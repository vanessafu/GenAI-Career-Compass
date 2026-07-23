"""
Run:
    python -m backend.scripts.role_embeddings                 # full rebuild: embeddings + sort_skills
    python -m backend.scripts.role_embeddings --dry-run        # print sample texts/skills, no API calls, no writes
    python -m backend.scripts.role_embeddings --limit 20       # first 20 roles only
    python -m backend.scripts.role_embeddings --test           # rerank one role's skills, print, no writes
    python -m backend.scripts.role_embeddings --rerank         # recompute title/skill enhancements only, embeddings untouched
    python -m backend.scripts.role_embeddings --rerank --limit 10
    python -m backend.scripts.role_embeddings --rerank --role-ids 12,45,78   # rerank only these role_ids
    python -m backend.scripts.role_embeddings --retry-failures  # rerank only the roles whose LLM call failed last run

Every run reports which role_ids the Gemini call failed for (network error, bad
JSON, etc.) and writes them to last_llm_failures.txt next to this script, so
--retry-failures can target just those roles on the next attempt.

Role texts are DOCUMENTS, so we use encode_documents() with no query prefix.
User profile texts remain per-request QUERIES in the matching service.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

if TYPE_CHECKING:
    from google import genai

from backend.app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.app.core.database import db_pool, get_db_connection
from backend.app.features.role_matching.embedder import EMBEDDING_DIM, get_embedder

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CareerCompass.DataPreprocessing")

MAX_DESC_CHARS = 1200
MAX_INTENT_DESC_CHARS = 700
DB_UPDATE_PAGE = 100

# Skill ranking: how much to trust the Gemini tier/score vs. embedding similarity
# to the job description. We trust the LLM more, so it dominates the blend.
SKILL_RANK_ALPHA = 0.85

# Gemini free tier: 10 requests/minute, 500 requests/day. One call per role, so
# pace at 6s/call (60s / 10) to stay under the per-minute cap. On a 429/503
# (rate limited / overloaded) we don't retry - just skip the role and record
# it for --retry-failures, so one rate-limited role doesn't stall the run.
GEMINI_RATE_LIMIT_DELAY_SECONDS = 6

_SKILL_ENHANCEMENT_SYSTEM_PROMPT = """
You are an expert technical recruiter building structured skill profiles for a career exploration and job matching system.You are given: job title, job description, raw skill list.Use all inputs as evidence and industry knowledge.
Task 1 — Processed Job Title
Standardize the job title.
- Keep it unchanged if already clear and standard.
- Otherwise remove noise or duplicates.
- Only refine if strongly supported by the description.
- Never change the role type.
Task 2 — Skill Hierarchy
Organize skills into IT industry-standard domains:
Frontend, Backend, DevOps, Cloud, Databases, Data Engineering, AI, Networking, Security, Software Engineering, Softskills.
Domain rules:
- Use only relevant domains (typically 3–7 per job).
- Do not invent custom or abstract domains.
- Each domain must be a real industry category.
- Soft Skills is allowed when relevant.
Skill rules:
- Keep relevant raw skills.
- Replace generic skills with concrete technologies:
  Databases → PostgreSQL / MySQL / MongoDB
  Cloud → AWS / Azure / GCP
  Backend → Node.js / Spring Boot / FastAPI
  Frontend → React / Vue / Angular
  AI → PyTorch / TensorFlow / Scikit-learn
  DevOps → CI/CD / Docker / Kubernetes / Terraform
- Remove vague or duplicate skills.
- Each domain contains 2–5 skills only.
- Add missing standard skills only if strongly implied.
- Add at most 10 new skills total.
No abstract skills:
Do not output Principles, Concepts, Fundamentals, Best Practices, or generic categories like Programming, Cloud Platforms, Databases.
Deduplication:
- A skill appears only once across all domains.
- Prefer most specific version.
Scoring: Each skill has:
- essential: 0.75–1.00
- important: 0.40–0.74
- nice_to_have: 0.00–0.39
Score reflects real job importance in industry.
Output JSON only:{"processed_job_title": "...","skill_domains": [{"domain": "...","skills": [{"skill": "...","tier": "...","score": 0.0}]}]}"""
_gemini_client: Optional["genai.Client"] = None

# Split career_roles.raw_skills on these only. '/' is intentionally excluded so
# CI/CD, TCP/IP, I/O survive as single tokens.
_RAW_SKILLS_SPLIT = re.compile(r"[;,|\n•]+")


def _split_raw_skills(text: Optional[str]) -> list[str]:
    """Comma/semicolon/pipe-separated skill string -> deduped list, order preserved."""
    if not text:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for part in _RAW_SKILLS_SPLIT.split(text):
        s = part.strip()
        key = s.lower()
        if s and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def _clean_text(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _truncate(value: Optional[str], max_chars: int) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0] + " ..."


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _get_gemini_client() -> "genai.Client":
    global _gemini_client
    if _gemini_client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in the environment variables.")
        from google import genai

        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client


def _skill_enhancement_prompt(title: Optional[str], description: Optional[str], raw_skills: list[str]) -> str:
    raw_skills_block = "\n".join(raw_skills) if raw_skills else "(none provided)"
    return (
        f"{_SKILL_ENHANCEMENT_SYSTEM_PROMPT}\n\n"
        f"ROLE TITLE: {_clean_text(title)}\n"
        f"ROLE DESCRIPTION: {_truncate(description, MAX_DESC_CHARS)}\n"
        f"RAW SKILLS:\n{raw_skills_block}"
    )


@dataclass
class LlmSkillEnhancement:
    processed_job_title: Optional[str]
    skill_scores: dict[str, float]
    skill_domains: dict[str, str] = field(default_factory=dict)


@dataclass
class RoleSkillEnhancement:
    processed_job_title: Optional[str] = None
    sort_skills: list[dict] = field(default_factory=list)
    processed_skills: list[str] = field(default_factory=list)
    llm_failed: bool = False


def _parse_llm_skill_enhancement(output_text: Optional[str]) -> Optional[LlmSkillEnhancement]:
    """Parse Gemini's hierarchical JSON reply - {"processed_job_title", "skill_domains":
    [{"domain", "skills": [{"skill","tier","score"}]}]} - into a flat (skill: score)
    map plus a (skill: domain) map; None if unusable."""
    text = (output_text or "").strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text[:4].lower() == "json":
            text = text[4:]
        text = text.strip()

    try:
        payload = json.loads(text)
        domain_groups = payload["skill_domains"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return None

    scores: dict[str, float] = {}
    skill_domains: dict[str, str] = {}
    for group in domain_groups:
        if not isinstance(group, dict):
            return None
        domain, items = group.get("domain"), group.get("skills")
        if not isinstance(domain, str) or not domain.strip() or not isinstance(items, list):
            return None
        domain = domain.strip()
        for item in items:
            if not isinstance(item, dict):
                return None
            skill, score = item.get("skill"), item.get("score")
            if not isinstance(skill, str) or not skill.strip() or not isinstance(score, (int, float)):
                return None
            skill = skill.strip()
            scores[skill] = _clamp01(float(score))
            skill_domains[skill] = domain

    if not scores:
        return None

    processed_title = payload.get("processed_job_title")
    processed_title = processed_title.strip() if isinstance(processed_title, str) else None
    return LlmSkillEnhancement(
        processed_job_title=processed_title or None,
        skill_scores=scores,
        skill_domains=skill_domains,
    )


def enhance_and_rank_skills_with_llm(
    title: Optional[str], description: Optional[str], raw_skills: list[str]
) -> Optional[LlmSkillEnhancement]:
    """Ask Gemini to clean up the job title and expand the raw/legacy skill list
    into a complete, specific set grounded in the role title/description, each
    scored for essentiality. None on any failure (including 429/503 rate
    limits) - no retry here, the caller skips the role outright so one
    rate-limited role doesn't stall the whole run; rerun with --retry-failures
    later instead.

    Paces one call every GEMINI_RATE_LIMIT_DELAY_SECONDS to stay under the free
    tier's requests-per-minute quota.
    """
    try:
        response = _get_gemini_client().models.generate_content(
            model=GEMINI_MODEL,
            contents=_skill_enhancement_prompt(title, description, raw_skills),
        )
        return _parse_llm_skill_enhancement(response.text)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini skill enhancement failed for %r: %s", title, exc)
        return None


def rank_role_skills(
    role_id: int,
    title: Optional[str],
    description: Optional[str],
    raw_skills: list[str],
) -> RoleSkillEnhancement:
    """Clean up a role's title and enhance its raw/legacy skill list with Gemini
    (grounded in title + description), blending the resulting essentiality
    scores with embedding similarity to the job description. If the Gemini
    call fails, skip the role entirely (no embedding fallback, no retry) and
    mark it for --retry-failures."""
    if not raw_skills:
        return RoleSkillEnhancement()

    enhancement = enhance_and_rank_skills_with_llm(title, description, raw_skills)
    if enhancement is None:
        logger.warning("role_id=%s: no usable Gemini skill enhancement, skipping.", role_id)
        return RoleSkillEnhancement(llm_failed=True)

    llm_scores = enhancement.skill_scores
    skills = list(llm_scores.keys())
    vectors = get_embedder().encode_documents([_clean_text(description), *skills])
    description_vector, skill_vectors = vectors[0], vectors[1:]
    emb_scores = {
        skill: _clamp01(_dot(description_vector, skill_vector))
        for skill, skill_vector in zip(skills, skill_vectors)
    }

    ranked = [
        {
            "skill": skill,
            "domain": enhancement.skill_domains.get(skill),
            "score": round(
                SKILL_RANK_ALPHA * llm_scores.get(skill, 0.0)
                + (1 - SKILL_RANK_ALPHA) * emb_scores.get(skill, 0.0),
                4,
            ),
        }
        for skill in skills
    ]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return RoleSkillEnhancement(
        processed_job_title=enhancement.processed_job_title,
        sort_skills=ranked,
        processed_skills=[item["skill"] for item in ranked],
        llm_failed=False,
    )


def _role_skill_fields(
    roles: list[tuple],
) -> tuple[list[int], list[Optional[str]], list[Optional[str]], list[list[str]]]:
    """Pull (role_id, title, description, raw skills) out of fetch_roles() rows.
    Seeded from career_roles.raw_skills only - the LLM enhancement step is what
    fills in gaps, not a preference for role_skills.normalized_skill_name."""
    ids: list[int] = []
    titles: list[Optional[str]] = []
    descriptions: list[Optional[str]] = []
    cleaned_skills: list[list[str]] = []
    for role_id, title, desc, _normalized_skills, raw_skills, *_rest in roles:
        ids.append(role_id)
        titles.append(title)
        descriptions.append(desc)
        cleaned_skills.append(_split_raw_skills(raw_skills))
    return ids, titles, descriptions, cleaned_skills


def compute_sort_skills(
    ids: list[int],
    titles: list[Optional[str]],
    descriptions: list[Optional[str]],
    cleaned_skills: list[list[str]],
) -> dict[int, RoleSkillEnhancement]:
    """Clean up the title and rank every role's skills one at a time (Gemini
    call + embedding call per role)."""
    ranked_role_count = sum(1 for skills in cleaned_skills if skills)
    logger.info("Enhancing title + skills with Gemini (%s) for %d roles ...", GEMINI_MODEL, ranked_role_count)

    enhancement_by_role: dict[int, RoleSkillEnhancement] = {}
    for role_id, title, description, skills in zip(ids, titles, descriptions, cleaned_skills):
        enhancement_by_role[role_id] = rank_role_skills(role_id, title, description, skills)
        time.sleep(GEMINI_RATE_LIMIT_DELAY_SECONDS)  # pace Gemini calls to stay under free tier limit

    return enhancement_by_role


LLM_FAILURES_FILE = Path(__file__).with_name("last_llm_failures.txt")


def report_llm_failures(enhancement_by_role: dict[int, RoleSkillEnhancement]) -> list[int]:
    """Collect role_ids whose LLM enhancement call failed (fell back to
    embedding-only scores), log them, and write them to LLM_FAILURES_FILE as a
    ready-to-paste --role-ids value for a targeted retry. Roles with no
    raw_skills at all are not "failures" - there was nothing to enhance."""
    failed_ids = sorted(rid for rid, enhancement in enhancement_by_role.items() if enhancement.llm_failed)

    if not failed_ids:
        LLM_FAILURES_FILE.unlink(missing_ok=True)
        logger.info("No LLM enhancement failures.")
        return failed_ids

    role_ids_arg = ",".join(str(rid) for rid in failed_ids)
    logger.warning(
        "LLM enhancement failed for %d role(s): %s\nRetry with:\n"
        "  python -m backend.scripts.role_embeddings --rerank --role-ids %s",
        len(failed_ids),
        failed_ids,
        role_ids_arg,
    )
    LLM_FAILURES_FILE.write_text(role_ids_arg + "\n", encoding="utf-8")
    logger.info("Failed role_ids written to %s for later reuse.", LLM_FAILURES_FILE)
    return failed_ids


def build_capability_embedding_text(
    *,
    title: Optional[str],
    description: Optional[str],
    skills_text: Optional[str],
    certifications: Optional[str],
    raw_certifications: Optional[str],
) -> str:
    """Role-side evidence comparable to a user's capability profile."""
    parts = [f"Job title: {_clean_text(title)}"]

    skills = _clean_text(skills_text)
    if skills:
        parts.append(f"Required skills: {skills}")

    certs = _first_non_empty(certifications, raw_certifications)
    if certs:
        parts.append(f"Certifications: {certs}")

    responsibilities = _truncate(description, MAX_DESC_CHARS)
    if responsibilities:
        parts.append(f"Responsibilities: {responsibilities}")

    return "\n".join(parts).strip()


def build_intent_embedding_text(
    *,
    title: Optional[str],
    description: Optional[str],
    domain_tags: Optional[str],
) -> str:
    """Role-side evidence comparable to a user's potential-direction/interests
    profile (the growth direction a person could plausibly move toward)."""
    parts = [f"Career direction: {_clean_text(title)}"]

    domains = _clean_text(domain_tags)
    if domains:
        parts.append(f"Domain tags: {domains}")

    context = _truncate(description, MAX_INTENT_DESC_CHARS)
    if context:
        parts.append(f"Role context: {context}")

    return "\n".join(parts).strip()


def _ensure_skill_enhancement_columns(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS sort_skills jsonb;")
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS processed_job_title text;")
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS processed_skills jsonb;")
    conn.commit()


def ensure_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS capability_embedding vector({EMBEDDING_DIM});"
        )
        cur.execute(
            f"ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS intent_embedding vector({EMBEDDING_DIM});"
        )
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS capability_embedding_text text;")
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS intent_embedding_text text;")
        cur.execute("ALTER TABLE career_roles DROP COLUMN IF EXISTS embedding;")
        cur.execute("ALTER TABLE career_roles DROP COLUMN IF EXISTS embedding_text;")
        cur.execute("ALTER TABLE certifications DROP COLUMN IF EXISTS embedding;")
    conn.commit()
    _ensure_skill_enhancement_columns(conn)
    _assert_vector_dims(conn)


def _assert_vector_dims(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname, a.atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = 'career_roles'
              AND a.attname IN ('capability_embedding', 'intent_embedding')
              AND NOT a.attisdropped;
            """
        )
        dims = dict(cur.fetchall())

    for column in ("capability_embedding", "intent_embedding"):
        if column not in dims:
            raise RuntimeError(f"career_roles.{column} missing after ensure_schema().")
        dim = dims[column]
        if dim not in (EMBEDDING_DIM, -1):
            raise RuntimeError(
                f"career_roles.{column} is vector({dim}) but the model outputs {EMBEDDING_DIM}. "
                f"Fix it first: ALTER TABLE career_roles ALTER COLUMN {column} TYPE vector({EMBEDDING_DIM});"
            )


def fetch_roles(
    conn: psycopg2.extensions.connection,
    limit: Optional[int] = None,
    role_ids: Optional[list[int]] = None,
) -> list[tuple]:
    sql = """
        WITH normalized_role_skills AS (
            SELECT
                role_id,
                string_agg(DISTINCT normalized_skill_name, ', ' ORDER BY normalized_skill_name) AS normalized_skills
            FROM role_skills
            WHERE normalized_skill_name IS NOT NULL
              AND btrim(normalized_skill_name) <> ''
            GROUP BY role_id
        ),
        mapped_certifications AS (
            SELECT
                cm.role_id,
                string_agg(
                    DISTINCT COALESCE(c.certification_name, c.normalized_certification_name),
                    ', '
                    ORDER BY COALESCE(c.certification_name, c.normalized_certification_name)
                ) AS certifications
            FROM certifications_mapping cm
            JOIN certifications c ON c.certification_id = cm.certification_id
            WHERE COALESCE(c.certification_name, c.normalized_certification_name) IS NOT NULL
              AND btrim(COALESCE(c.certification_name, c.normalized_certification_name)) <> ''
            GROUP BY cm.role_id
        )
        SELECT
            c.role_id,
            c.job_title,
            c.job_description,
            nrs.normalized_skills,
            c.raw_skills,
            mc.certifications,
            c.raw_certifications,
            c.domain_tags
        FROM career_roles c
        LEFT JOIN normalized_role_skills nrs ON nrs.role_id = c.role_id
        LEFT JOIN mapped_certifications mc ON mc.role_id = c.role_id
    """
    params: list = []
    if role_ids:
        sql += " WHERE c.role_id = ANY(%s)"
        params.append(list(role_ids))
    sql += " ORDER BY c.role_id"
    if limit:
        sql += " LIMIT %s"
        params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return cur.fetchall()


def store_role_embeddings(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    if not rows:
        return
    sql = """
        UPDATE career_roles AS c
        SET capability_embedding = v.capability_embedding::vector,
            intent_embedding = v.intent_embedding::vector,
            capability_embedding_text = v.capability_embedding_text,
            intent_embedding_text = v.intent_embedding_text,
            sort_skills = v.sort_skills::jsonb,
            processed_job_title = v.processed_job_title,
            processed_skills = v.processed_skills::jsonb
        FROM (VALUES %s) AS v(
            role_id,
            capability_embedding,
            intent_embedding,
            capability_embedding_text,
            intent_embedding_text,
            sort_skills,
            processed_job_title,
            processed_skills
        )
        WHERE c.role_id = v.role_id::bigint
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template="(%s, %s, %s, %s, %s, %s, %s, %s)", page_size=DB_UPDATE_PAGE)
    conn.commit()


def store_skill_enhancements(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    """Write sort_skills/processed_job_title/processed_skills only, leaving
    capability/intent embeddings untouched."""
    if not rows:
        return
    sql = """
        UPDATE career_roles AS c
        SET sort_skills = v.sort_skills::jsonb,
            processed_job_title = v.processed_job_title,
            processed_skills = v.processed_skills::jsonb
        FROM (VALUES %s) AS v(role_id, sort_skills, processed_job_title, processed_skills)
        WHERE c.role_id = v.role_id::bigint
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template="(%s, %s, %s, %s)", page_size=DB_UPDATE_PAGE)
    conn.commit()


def rebuild(
    limit: Optional[int] = None,
    dry_run: bool = False,
    role_ids: Optional[list[int]] = None,
) -> None:
    with get_db_connection() as conn:
        if not dry_run:
            ensure_schema(conn)

        roles = fetch_roles(conn, limit, role_ids)
        logger.info("Fetched %d roles.", len(roles))

        ids: list[int] = []
        titles: list[Optional[str]] = []
        descriptions: list[Optional[str]] = []
        capability_texts: list[str] = []
        intent_texts: list[str] = []
        cleaned_skills: list[list[str]] = []
        for (
            role_id,
            title,
            desc,
            normalized_skills,
            raw_skills,
            certifications,
            raw_certifications,
            domain_tags,
        ) in roles:
            ids.append(role_id)
            titles.append(title)
            descriptions.append(desc)
            skills_text = _first_non_empty(normalized_skills, raw_skills)
            cleaned_skills.append(_split_raw_skills(raw_skills))
            capability_texts.append(
                build_capability_embedding_text(
                    title=title,
                    description=desc,
                    skills_text=skills_text,
                    certifications=certifications,
                    raw_certifications=raw_certifications,
                )
            )
            intent_texts.append(
                build_intent_embedding_text(
                    title=title,
                    description=desc,
                    domain_tags=domain_tags,
                )
            )

        if dry_run:
            for i in range(min(3, len(ids))):
                logger.info(
                    "role_id=%s\n[Capability]\n%s\n\n[Intent]\n%s\n\n[Skills to rank]\n%s\n----------",
                    ids[i],
                    capability_texts[i],
                    intent_texts[i],
                    ", ".join(cleaned_skills[i]) or "(none)",
                )
            logger.info(
                "Dry run: %d roles would be embedded and skill-ranked. No writes or Gemini calls performed.",
                len(ids),
            )
            return

        logger.info("Encoding %d capability role documents (no query prefix) ...", len(capability_texts))
        capability_vectors = get_embedder().encode_documents(capability_texts)
        logger.info("Encoding %d intent role documents (no query prefix) ...", len(intent_texts))
        intent_vectors = get_embedder().encode_documents(intent_texts)

        enhancement_by_role = compute_sort_skills(ids, titles, descriptions, cleaned_skills)
        report_llm_failures(enhancement_by_role)

        rows = [
            (
                rid,
                _vec_literal(cap_vec),
                _vec_literal(intent_vec),
                cap_text,
                intent_text,
                json.dumps(enhancement_by_role.get(rid, RoleSkillEnhancement()).sort_skills),
                enhancement_by_role.get(rid, RoleSkillEnhancement()).processed_job_title,
                json.dumps(enhancement_by_role.get(rid, RoleSkillEnhancement()).processed_skills),
            )
            for rid, cap_vec, intent_vec, cap_text, intent_text in zip(
                ids,
                capability_vectors,
                intent_vectors,
                capability_texts,
                intent_texts,
            )
        ]
        store_role_embeddings(conn, rows)
        logger.info("Done. Wrote split embeddings + title/skill enhancements for %d roles.", len(rows))


def rerank_only(
    limit: Optional[int] = None,
    test: bool = False,
    role_ids: Optional[list[int]] = None,
) -> None:
    """Recompute title/skill enhancements only (Gemini + embedding blend);
    capability/intent embeddings are left untouched. --test forces a single
    role and never writes. If role_ids is given, only those roles are
    reranked (limit still applies on top)."""
    with get_db_connection() as conn:
        if not test:
            _ensure_skill_enhancement_columns(conn)

        roles = fetch_roles(conn, limit=1 if test else limit, role_ids=role_ids)
        logger.info("Fetched %d role(s) for title/skill enhancement.", len(roles))

        ids, titles, descriptions, cleaned_skills = _role_skill_fields(roles)
        enhancement_by_role = compute_sort_skills(ids, titles, descriptions, cleaned_skills)
        report_llm_failures(enhancement_by_role)

        if test:
            for role_id, title in zip(ids, titles):
                enhancement = enhancement_by_role.get(role_id, RoleSkillEnhancement())
                logger.info(
                    "role_id=%s title=%r\n[Processed title] %s\n[Ranked skills]\n%s\n----------",
                    role_id,
                    title,
                    enhancement.processed_job_title,
                    json.dumps(enhancement.sort_skills, indent=2),
                )
            logger.info("Test run: title/skill enhancement computed for %d role(s). No writes performed.", len(ids))
            return

        rows = [
            (
                rid,
                json.dumps(enhancement_by_role.get(rid, RoleSkillEnhancement()).sort_skills),
                enhancement_by_role.get(rid, RoleSkillEnhancement()).processed_job_title,
                json.dumps(enhancement_by_role.get(rid, RoleSkillEnhancement()).processed_skills),
            )
            for rid in ids
        ]
        store_skill_enhancements(conn, rows)
        logger.info("Done. Wrote title/skill enhancements for %d role(s); embeddings untouched.", len(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild split career_roles embeddings with bge-base-en-v1.5.")
    parser.add_argument("--dry-run", action="store_true", help="Print sample split embedding texts and exit; no writes.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N roles.")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run the skill reranker (Gemini + embeddings) on a single role and print the result; no writes.",
    )
    parser.add_argument(
        "--rerank",
        action="store_true",
        help="Only recompute title/skill enhancements (Gemini + embedding blend); skip capability/intent embeddings entirely.",
    )
    parser.add_argument(
        "--role-ids",
        type=str,
        default=None,
        help="Comma-separated role_id list to restrict processing to, e.g. --role-ids 12,45,78. "
        "Useful for re-ranking only the roles that never got an LLM ranking.",
    )
    parser.add_argument(
        "--retry-failures",
        action="store_true",
        help=f"Rerank only the role_ids from the previous run's LLM failures ({LLM_FAILURES_FILE.name}). "
        "Implies --rerank.",
    )
    args = parser.parse_args()
    if args.retry_failures:
        if not LLM_FAILURES_FILE.exists():
            logger.info("%s does not exist - nothing to retry.", LLM_FAILURES_FILE)
            return
        role_ids = [
            int(part.strip())
            for part in LLM_FAILURES_FILE.read_text(encoding="utf-8").split(",")
            if part.strip()
        ]
        logger.info("Retrying %d role(s) from %s.", len(role_ids), LLM_FAILURES_FILE)
        args.rerank = True
    else:
        role_ids = (
            [int(part.strip()) for part in args.role_ids.split(",") if part.strip()]
            if args.role_ids
            else None
        )
    try:
        if args.test:
            rerank_only(test=True)
        elif args.rerank:
            rerank_only(limit=args.limit, role_ids=role_ids)
        else:
            rebuild(limit=args.limit, dry_run=args.dry_run, role_ids=role_ids)
    finally:
        if db_pool is not None:
            db_pool.closeall()


if __name__ == "__main__":
    main()
