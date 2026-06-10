"""
Role-matching RAG pipeline.

Flow:
  1. build_cv_embedding_text   — compact CareerBERT-optimised query string
  2. Dense retrieval           — pgvector cosine similarity (top-N candidates)
  3. Sparse retrieval          — BM25 via rank_bm25 (top-N candidates)
  4. RRF fusion                — Reciprocal Rank Fusion, k=60
  5. FlashRank reranking       — ms-marco-MiniLM-L-12-v2 cross-encoder (CPU, 4 MB)
  6. Interest-weighted scoring — user interests are the dominant signal (40 %)
  7. Gap analysis              — framework-level skill gap computation
  8. LLM explanation           — overall match rationale + multi-dimensional gaps

Reranker choice: FlashRank with ms-marco-MiniLM-L-12-v2.
  Rationale: no PyTorch/Transformers dependency, ONNX runtime, ~4 MB model,
  excellent latency on CPU — ideal for a school project demo environment.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import psycopg
from pgvector.psycopg import register_vector
from rank_bm25 import BM25Okapi
from flashrank import Ranker, RerankRequest

from backend.app.core.config import DATABASE_URL, get_async_openai_client, OPENAI_MODEL, OPENAI_TEMPERATURE
from backend.app.core.config import DATABASE_URL
from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.embedder import get_embedder
from backend.app.features.role_matching.normalization_layer import (
    get_normalization_engine,
    normalize_skills,
)
from backend.app.features.role_matching.schemas import (
    GapAnalysis,
    RoleMatch,
    RoleMatchResponse,
    SkillGap,
)

logger = logging.getLogger("CareerCompass.RoleMatching.Service")

# Stop-words excluded from interest overlap computation
_STOP = frozenset(
    {"and", "or", "the", "a", "an", "in", "of", "to", "for", "with",
     "on", "at", "by", "from", "is", "are", "be", "as", "i", "my", "me"}
)

# Final scoring weights  (must sum to 1.0)
_W_EMBED = 0.35   # dense similarity (RRF normalised)
_W_INTEREST = 0.40  # interest alignment — dominant
_W_RERANK = 0.25  # cross-encoder rerank score


# ---------------------------------------------------------------------------
# 1.  CV → embedding text
# ---------------------------------------------------------------------------

def build_cv_embedding_text(cv_data: CVData) -> str:
    """
    Compact CareerBERT-optimised query text (~130–170 tokens).

    Format:
      [Title]: {current_role}
      [Skills]: {normalized skills, max 12}
      [Experience]: {role}: {resp1}; {resp2} | ... (up to 3 entries)
      [Interests]: {interests}
      [Profile]: {first sentence of summary}

    Experience slots are filled from work experience (newest-first).
    If fewer than 3 work entries exist, projects supplement the remainder
    (using description + technologies).
    """
    parts: list[str] = []
    engine = get_normalization_engine()

    # Title
    title = cv_data.personal_info.current_role or ""
    if title:
        parts.append(f"[Title]: {title}")

    # Skills (normalized, deduped, cap at 12)
    raw_skills = [s.name for s in cv_data.skills_extracted.technical_skills]
    norm_skills = engine.normalize_list(raw_skills)[:12]
    if norm_skills:
        parts.append(f"[Skills]: {', '.join(norm_skills)}")

    # Experience — up to 3 slots, newest-first
    exp_slots: list[str] = []

    for exp in cv_data.experience:
        if len(exp_slots) >= 3:
            break
        if not exp.role:
            continue
        resps = "; ".join(r for r in exp.core_responsibilities[:2] if r)
        slot = f"{exp.role}: {resps}" if resps else exp.role
        exp_slots.append(slot)

    # Supplement from projects if still < 3
    if len(exp_slots) < 3:
        for proj in cv_data.projects:
            if len(exp_slots) >= 3:
                break
            desc = (proj.description or "")[:80].strip()
            techs = ", ".join(proj.technologies[:4])
            if desc or techs:
                slot = f"{desc} [{techs}]" if techs else desc
                exp_slots.append(slot)

    if exp_slots:
        parts.append(f"[Experience]: {' | '.join(exp_slots)}")

    # Interests
    if cv_data.interests:
        parts.append(f"[Interests]: {', '.join(cv_data.interests)}")

    # Profile — first sentence of summary only (~20 tokens)
    summary = (cv_data.profile_summary.summary or "").strip()
    if summary:
        first_sentence = re.split(r"(?<=[.!?])\s", summary)[0][:150]
        parts.append(f"[Profile]: {first_sentence}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 2.  Dense retrieval  (pgvector)
# ---------------------------------------------------------------------------

def _dense_retrieve(query_embedding: list[float], n: int) -> list[tuple[str, float]]:
    """Return (job_id, cosine_similarity) for top-n jobs."""
    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        rows = conn.execute(
            """
            SELECT job_id,
                   1 - (embedding <=> %s::vector) AS score
            FROM job_postings
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, n),
        ).fetchall()
    return [(row[0], float(row[1])) for row in rows]


# ---------------------------------------------------------------------------
# 3.  Sparse retrieval  (BM25)
# ---------------------------------------------------------------------------

# Lazy corpus cache: (job_ids, raw_texts, BM25Okapi index)
_bm25_cache: Optional[tuple[list[str], list[str], BM25Okapi]] = None


def _get_bm25_index() -> tuple[list[str], list[str], BM25Okapi]:
    global _bm25_cache
    if _bm25_cache is None:
        with psycopg.connect(DATABASE_URL) as conn:
            rows = conn.execute(
                "SELECT job_id, raw_text FROM job_postings ORDER BY job_id"
            ).fetchall()
        job_ids = [r[0] for r in rows]
        texts = [r[1] for r in rows]
        tokenized = [t.lower().split() for t in texts]
        _bm25_cache = (job_ids, texts, BM25Okapi(tokenized))
        logger.info("BM25 index built over %d job postings.", len(job_ids))
    return _bm25_cache


def _bm25_retrieve(query_text: str, n: int) -> list[tuple[str, float]]:
    """Return (job_id, bm25_score) for top-n jobs."""
    job_ids, _texts, index = _get_bm25_index()
    tokens = query_text.lower().split()
    scores = index.get_scores(tokens)
    # Pair and sort
    ranked = sorted(zip(job_ids, scores), key=lambda x: x[1], reverse=True)
    return [(jid, float(sc)) for jid, sc in ranked[:n]]


def invalidate_bm25_cache() -> None:
    """Call after re-loading the job_postings table."""
    global _bm25_cache
    _bm25_cache = None


# ---------------------------------------------------------------------------
# 4.  RRF fusion
# ---------------------------------------------------------------------------

def _rrf_fuse(
    dense: list[tuple[str, float]],
    sparse: list[tuple[str, float]],
    k: int = 60,
) -> list[tuple[str, float]]:
    """
    Reciprocal Rank Fusion.
    score(d) = Σ 1 / (k + rank_i(d))   over each ranked list.
    """
    scores: dict[str, float] = {}
    for rank, (job_id, _) in enumerate(dense):
        scores[job_id] = scores.get(job_id, 0.0) + 1.0 / (k + rank + 1)
    for rank, (job_id, _) in enumerate(sparse):
        scores[job_id] = scores.get(job_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ---------------------------------------------------------------------------
# 5.  FlashRank cross-encoder reranking
# ---------------------------------------------------------------------------

_ranker: Optional[Ranker] = None


def _get_ranker() -> Ranker:
    global _ranker
    if _ranker is None:
        _ranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank")
    return _ranker


def _rerank(
    query: str,
    candidates: list[tuple[str, str]],  # [(job_id, raw_text), ...]
) -> list[tuple[str, float]]:
    """Return (job_id, rerank_score) sorted descending."""
    passages = [{"id": jid, "text": text} for jid, text in candidates]
    request = RerankRequest(query=query, passages=passages)
    results = _get_ranker().rerank(request)
    return [(r["id"], float(r["score"])) for r in results]


# ---------------------------------------------------------------------------
# 6.  Interest-weighted scoring
# ---------------------------------------------------------------------------

def _interest_score(
    user_interests: list[str],
    jobtitle: str,
    essential_skills: list[str],
) -> float:
    """
    Soft keyword overlap between user interests and job (title + skills).
    Returns a value in [0, 1].  0.5 when the user has no interests (neutral).
    """
    if not user_interests:
        return 0.5

    def tokenize(text: str) -> set[str]:
        tokens = set(re.sub(r"[^a-z\s]", "", text.lower()).split())
        return tokens - _STOP

    interest_tokens: set[str] = set()
    for interest in user_interests:
        interest_tokens |= tokenize(interest)

    job_tokens: set[str] = tokenize(jobtitle)
    for skill in essential_skills:
        job_tokens |= tokenize(skill)

    if not interest_tokens:
        return 0.5
    overlap = len(interest_tokens & job_tokens)
    # Recall-biased: how much of the user's intent is reflected in the job
    return min(1.0, overlap / len(interest_tokens))


# ---------------------------------------------------------------------------
# 7.  Gap analysis
# ---------------------------------------------------------------------------

def compute_gap_analysis(
    user_skills: list[str],
    job_skills: list[str],
) -> GapAnalysis:
    """
    Framework-level gap analysis (Step 3 dimensionality reduction).

    Maps both skill sets to ~50 framework domains, then computes:
      - matched_skills: frameworks covered by the user
      - skill_gaps: frameworks required by the job but missing or weak
      - match_coverage: fraction of job frameworks the user covers
    """
    engine = get_normalization_engine()

    # Cluster to framework level
    user_fw: dict[str, str] = {}   # framework → best user canonical skill
    for s in user_skills:
        fw = engine.get_framework(s)
        user_fw.setdefault(fw, engine.normalize(s))

    job_fw: dict[str, str] = {}    # framework → required canonical skill
    for s in job_skills:
        fw = engine.get_framework(s)
        job_fw.setdefault(fw, engine.normalize(s))

    matched: list[str] = []
    gaps: list[SkillGap] = []

    for fw, req_skill in job_fw.items():
        if fw in user_fw:
            matched.append(req_skill)
        else:
            # Find best transferability from any user skill
            best_transfer = 0.0
            best_source: Optional[str] = None
            for user_skill in user_skills:
                t = engine.get_transferability(user_skill, req_skill)
                if t > best_transfer:
                    best_transfer = t
                    best_source = engine.normalize(user_skill)

            if best_transfer >= 0.65:
                severity = "low"
            elif best_transfer >= 0.35:
                severity = "medium"
            else:
                severity = "high"

            gaps.append(SkillGap(
                framework=fw,
                required_skill=req_skill,
                user_closest_skill=best_source,
                transferability=round(best_transfer, 2),
                severity=severity,
            ))

    total = len(job_fw)
    coverage = len(matched) / total if total else 0.0

    return GapAnalysis(
        matched_skills=matched,
        skill_gaps=gaps,
        match_coverage=round(coverage, 2),
    )


# ---------------------------------------------------------------------------
# 8.  Fetch full job records for a set of job_ids
# ---------------------------------------------------------------------------

def _fetch_jobs(job_ids: list[str]) -> dict[str, dict]:
    """Return {job_id: {jobtitle, description, essential_skills, raw_text}}."""
    if not job_ids:
        return {}
    with psycopg.connect(DATABASE_URL) as conn:
        placeholders = ",".join(["%s"] * len(job_ids))
        rows = conn.execute(
            f"SELECT job_id, jobtitle, description, essential_skills, raw_text "
            f"FROM job_postings WHERE job_id IN ({placeholders})",
            job_ids,
        ).fetchall()
    return {
        r[0]: {
            "jobtitle": r[1],
            "description": r[2],
            "essential_skills": list(r[3] or []),
            "raw_text": r[4],
        }
        for r in rows
    }


# ---------------------------------------------------------------------------
# 9.  LLM explanation + gap narrative
# ---------------------------------------------------------------------------

async def _generate_analysis(
    cv_data: CVData,
    matches: list[RoleMatch],
) -> str:
    client = get_async_openai_client()

    user_skills = [s.name for s in cv_data.skills_extracted.technical_skills[:12]]
    interests_str = ", ".join(cv_data.interests) or "not specified"

    roles_block_parts: list[str] = []
    for i, m in enumerate(matches):
        gap_summary = ""
        if m.gap_analysis:
            high_gaps = [
                g.required_skill for g in m.gap_analysis.skill_gaps
                if g.severity == "high"
            ]
            low_gaps = [
                g.required_skill for g in m.gap_analysis.skill_gaps
                if g.severity in ("low", "medium")
            ]
            matched = m.gap_analysis.matched_skills
            gap_summary = (
                f"\n   Skills matched: {', '.join(matched[:5]) or 'none'}"
                f"\n   High-priority gaps: {', '.join(high_gaps[:3]) or 'none'}"
                f"\n   Bridgeable gaps (transferable): {', '.join(low_gaps[:3]) or 'none'}"
                f"\n   Coverage: {m.gap_analysis.match_coverage:.0%}"
            )
        roles_block_parts.append(
            f"{i + 1}. {m.jobtitle}  (match score: {m.final_score:.0%})"
            + (f"\n   {(m.description or '')[:200]}" if m.description else "")
            + gap_summary
        )
    roles_block = "\n".join(roles_block_parts)

    system_prompt = (
        "You are a concise career advisor. "
        "Give specific, actionable insights grounded in the user's actual profile. "
        "Focus on fit and growth opportunities, not generic advice."
    )

    user_prompt = (
        f"User profile:\n"
        f"  Current role: {cv_data.personal_info.current_role or 'not specified'}\n"
        f"  Key skills: {', '.join(user_skills) or 'not specified'}\n"
        f"  Interests: {interests_str}\n\n"
        f"Top matched job roles:\n{roles_block}\n\n"
        "Structure your response:\n"
        "1. OVERALL FIT (2 sentences): Why these roles match this user's background.\n"
        "2. SKILL GAPS by domain (bullet points): For each high-priority gap, "
        "briefly note whether the user can bridge it from their existing skills.\n"
        "3. RECOMMENDATION (1 sentence): Which role to target first and why."
    )

    return await openai_client.complete(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=OPENAI_TEMPERATURE,
        max_tokens=450,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

RETRIEVAL_N = 50    # candidates per retrieval leg
RERANK_N = 20       # candidates fed to cross-encoder


async def match_roles_for_cv(cv_data: CVData, top_k: int = 5) -> RoleMatchResponse:
    """
    Full hybrid RAG pipeline:
      Dense → Sparse (BM25) → RRF → FlashRank → interest scoring → LLM
    """
    query_text = build_cv_embedding_text(cv_data)
    logger.info("CV query text:\n%s", query_text)

    # Embed CV
    embedder = get_embedder()
    query_vec = embedder.encode(query_text)

    # Retrieve
    dense_hits = _dense_retrieve(query_vec, RETRIEVAL_N)
    sparse_hits = _bm25_retrieve(query_text, RETRIEVAL_N)
    logger.info("Dense hits: %d  BM25 hits: %d", len(dense_hits), len(sparse_hits))

    # RRF fusion
    fused = _rrf_fuse(dense_hits, sparse_hits)[:RERANK_N]
    fused_ids = [jid for jid, _ in fused]
    rrf_score_map = {jid: sc for jid, sc in fused}

    # Fetch job texts for reranking
    job_map = _fetch_jobs(fused_ids)

    # Rerank
    candidates = [(jid, job_map[jid]["raw_text"]) for jid in fused_ids if jid in job_map]
    reranked = _rerank(query_text, candidates)
    logger.info("Reranked %d candidates.", len(reranked))

    # Build RoleMatch objects with all scores
    user_skills = normalize_skills([s.name for s in cv_data.skills_extracted.technical_skills])

    # Normalise rerank scores to [0,1] (FlashRank returns logits)
    if reranked:
        max_rr = max(sc for _, sc in reranked)
        min_rr = min(sc for _, sc in reranked)
        rr_range = max_rr - min_rr if max_rr != min_rr else 1.0
    else:
        max_rr = min_rr = rr_range = 1.0

    # Also normalise RRF scores to [0,1]
    rrf_values = list(rrf_score_map.values())
    max_rrf = max(rrf_values) if rrf_values else 1.0

    results: list[RoleMatch] = []
    for job_id, raw_rr in reranked:
        if job_id not in job_map:
            continue
        job = job_map[job_id]

        # Scores
        sim_score = dict(dense_hits).get(job_id, 0.0)
        norm_rrf = rrf_score_map.get(job_id, 0.0) / max_rrf
        norm_rr = (raw_rr - min_rr) / rr_range
        i_score = _interest_score(
            cv_data.interests,
            job["jobtitle"],
            job["essential_skills"],
        )
        final = _W_EMBED * norm_rrf + _W_INTEREST * i_score + _W_RERANK * norm_rr

        # Gap analysis
        gap = compute_gap_analysis(user_skills, job["essential_skills"])

        results.append(RoleMatch(
            job_id=job_id,
            jobtitle=job["jobtitle"],
            description=job["description"],
            essential_skills=job["essential_skills"],
            similarity_score=round(sim_score, 4),
            interest_score=round(i_score, 4),
            rerank_score=round(norm_rr, 4),
            final_score=round(final, 4),
            gap_analysis=gap,
        ))

    # Sort by final score, keep top_k
    results.sort(key=lambda r: r.final_score, reverse=True)
    top_results = results[:top_k]

    analysis = await _generate_analysis(cv_data, top_results)

    return RoleMatchResponse(
        query_text=query_text,
        matched_roles=top_results,
        analysis=analysis,
    )
