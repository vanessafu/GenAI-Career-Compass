"""
Role-matching orchestration.

The public endpoint accepts one clean user career profile. For each request we:
1. Build two privacy-sensitive query texts in memory.
2. Embed those texts without persisting user profile data.
3. Compare against the Supabase role catalog.
4. Re-rank with explainable database signals.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from collections import defaultdict
from typing import Any, Iterable

from backend.app.core import openai_client
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.normalization import (
    certification_match_keys,
    clean_alias_map,
    normalize_certification_name,
    normalize_skill_key,
    normalize_user_certifications,
    required_skills_from_sort_skills,
    seniority_gap,
    seniority_level_from_title,
    skill_weight_map,
)
from backend.app.features.role_matching.recommendation import Candidate, recommend
from backend.app.features.role_matching.schemas import (
    RoleMatch,
    RoleMatchDebug,
    RoleMatchResponse,
    RoleSummaryBatch,
    UserCareerProfile,
)
from backend.app.features.role_matching.prepared_skills import PreparedSkillProfile, prepare_user_skills
from backend.app.features.role_matching.skill_alignment import (
    align_skills,
    build_skill_evidence_from_user_profile,
)

logger = logging.getLogger("CareerCompass.RoleMatching.Service")

_MAX_TEXT = 700
_MAX_ROLE_CARD_SUMMARY = 180

DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "architecture": ("architect", "architecture", "system design", "distributed systems"),
    "backend": ("backend", "api", "rest", "service", "server", "microservice"),
    "cloud": ("cloud", "aws", "azure", "gcp", "infrastructure"),
    "frontend": ("frontend", "front end", "react", "vue", "angular", "web ui"),
    "fullstack": ("fullstack", "full stack"),
    "software_engineering": (
        "software engineering",
        "software engineer",
        "software developer",
        "software development",
        "tooling engineer",
        "developer tooling",
    ),
    "ai_ml": ("artificial intelligence", "machine learning", "deep learning", " ai ", " ml "),
    "automation_scripting": ("automation", "scripting", "process automation", "workflow"),
    "data_engineering": ("big data", "data scale", "data engineering", "data pipeline", "etl", "spark"),
    "data_analytics": ("analytics", "business intelligence", "dashboard", "reporting", "sql analysis"),
    "devops": (
        "devops",
        "ci cd",
        "continuous integration",
        "jenkins",
        "ansible",
        "build automation",
        "release cadence",
        "kubernetes",
        "docker",
        "terraform",
        "platform engineering",
    ),
    "qa_testing": (
        "qa",
        "quality assurance",
        "testing",
        "test automation",
        "automated testing",
        "selenium",
        "junit",
        "quality gates",
    ),
    "cybersecurity": ("security", "cybersecurity", "appsec", "iam", "threat"),
    "database": ("database", "postgres", "postgresql", "mysql", "sql", "nosql"),
    "ux_ui": ("ux", "ui", "user experience", "user interface", "design system"),
    "support": ("support", "customer success", "helpdesk", "service desk"),
    "project_management": ("project management", "program management", "scrum", "agile", "stakeholder"),
}

_DYNAMIC_DOMAIN_STOPWORDS = {
    "and",
    "the",
    "with",
    "for",
    "role",
    "engineer",
    "developer",
    "specialist",
    "analyst",
    "senior",
    "junior",
    "mid",
    "level",
    "builds",
    "building",
    "systems",
    "using",
}

DEFAULT_SKILL_ALIASES: dict[str, str] = {
    "api": "rest apis",
    "apis": "rest apis",
    "rest api": "rest apis",
    "restful api": "restful apis",
    "spring": "spring framework",
    "spring boot": "spring framework",
    "ux": "ui ux design",
    "ui": "ui ux design",
    "accessibility": "web accessibility guidelines",
    "a11y": "web accessibility guidelines",
    "analytics": "data analysis",
    "data analytics": "data analysis",
    "ci": "ci cd",
    "ci/cd": "ci cd",
    "continuous integration": "ci cd",
    "continuous integration ci": "ci cd",
    "automated testing": "test automation",
    "azure cloud": "azure",
    "linux services": "linux",
    "shell scripts": "scripting",
}



def as_cv_data(profile: ConfirmedCVData | CVData) -> CVData:
    """Return the raw CV payload used by gap analysis."""
    return profile.confirmed_cv_data if isinstance(profile, ConfirmedCVData) else profile

def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(str(value).split())
    return cleaned or None


def _truncate(value: str, max_chars: int = _MAX_TEXT) -> str:
    cleaned = " ".join(value.split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0] + " ..."


def _clean_role_card_summary(value: Any) -> str | None:
    cleaned = _clean_text(value)
    if not cleaned:
        return None
    sentence_ends = list(re.finditer(r"[.!?](?:\s|$)", cleaned))
    if len(sentence_ends) >= 2:
        cleaned = cleaned[: sentence_ends[1].end()].strip()
    if len(cleaned) <= _MAX_ROLE_CARD_SUMMARY:
        return cleaned
    shortened = cleaned[: _MAX_ROLE_CARD_SUMMARY - 3].rsplit(" ", 1)[0].rstrip(" ,;:-")
    return f"{shortened}..."


def _format_salary(monthly_gross_eur: Any) -> str:
    if monthly_gross_eur is None:
        return ""
    try:
        annual_thousands = int(round((float(monthly_gross_eur) * 12) / 1000))
    except (TypeError, ValueError):
        return ""
    return f"EUR {annual_thousands}k"


def _join_unique(values: Iterable[str | None], *, limit: int | None = None) -> str | None:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
        if limit is not None and len(out) >= limit:
            break
    return ", ".join(out) if out else None


def _dedupe(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = _clean_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


def normalize_user_skills(skills: Iterable[str], alias_map: dict[str, str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    merged_aliases = clean_alias_map(DEFAULT_SKILL_ALIASES)
    merged_aliases.update(clean_alias_map(alias_map))
    for skill in skills:
        key = normalize_skill_key(skill)
        if not key:
            continue
        canonical = merged_aliases.get(key, key)
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
    return normalized


def _listify(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe(str(item) for item in value if item is not None)
    if isinstance(value, tuple | set):
        return _dedupe(str(item) for item in value if item is not None)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return _dedupe(str(item) for item in parsed if item is not None)
            except json.JSONDecodeError:
                pass
        return _dedupe(re.split(r"[,;|/]+", stripped))
    return _dedupe([str(value)])


def _profile_skill_terms(profile: UserCareerProfile) -> list[str]:
    skills: list[str] = []
    skills.extend(profile.skills)
    for exp in profile.experience:
        skills.extend(exp.skills)
    for project in profile.projects:
        skills.extend(project.technologies)
    return _dedupe(skills)



def build_capability_text(profile: UserCareerProfile) -> str:
    parts: list[str] = []
    skill_text = _join_unique(profile.skills, limit=30)
    if skill_text:
        parts.append(f"Skills: {skill_text}")
    
    for index, exp in enumerate(profile.experience, start=1):
        line_parts = [
            exp.role,
            f"Summary: {_truncate(exp.summary)}" if _clean_text(exp.summary) else None,
            f"Skills: {_join_unique(exp.skills)}" if _join_unique(exp.skills) else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Experience {index}: {joined}")

    for index, project in enumerate(profile.projects, start=1):
        line_parts = [
            project.title,
            f"Summary: {_truncate(project.summary)}" if _clean_text(project.summary) else None,
            f"Technologies: {_join_unique(project.technologies)}" if _join_unique(project.technologies) else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Project {index}: {joined}")
    for index, cert in enumerate(profile.certifications, start=1):
        line_parts = [
            cert.name,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Certification {index}: {joined}")
    for index, edu in enumerate(profile.education, start=1):
        line_parts = [
            edu.degree,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Education {index}: {joined}")
    return "\n".join(parts).strip()


def build_intent_text(profile: UserCareerProfile) -> str:
    """Where this person could plausibly grow toward - potential_direction
    (inferred from experience/projects) + stated interests. Compared against
    each role's intent_embedding (its own career-direction framing)."""
    parts: list[str] = []
    interest_text = _join_unique(profile.interests, limit=20)
    if interest_text:
        parts.append(f"Interests: {interest_text}")

    if _clean_text(profile.potential_direction):
        parts.append(f"Potential direction: {_truncate(profile.potential_direction)}")
    return "\n".join(parts).strip()


def build_identity_text(profile: UserCareerProfile) -> str:
    """Who this person currently identifies as professionally. The text is
    compared with each role's capability embedding and scored as the identity
    signal in all three recommendation lenses."""
    parts: list[str] = []
    if _clean_text(profile.career_identity.title):
        parts.append(f"Career identity: {profile.career_identity.title.strip()}")
    if _clean_text(profile.career_identity.summary):
        parts.append(f"Career summary: {_truncate(profile.career_identity.summary)}")
    return "\n".join(parts).strip()


def map_profile_domains(profile: UserCareerProfile) -> list[str]:
    terms = [
        profile.career_identity.title or "",
        profile.career_identity.summary or "",
        *profile.interests,
    ]
    normalized_text = " " + normalize_skill_key(" ".join(terms)) + " "
    domains: list[str] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = " " + normalize_skill_key(keyword) + " "
            if normalized_keyword in normalized_text:
                domains.append(domain)
                break
    return domains


def _dynamic_domain_terms(terms: Iterable[str | None]) -> set[str]:
    dynamic_terms: set[str] = set()
    for term in terms:
        normalized = normalize_skill_key(str(term or "").replace("_", " "))
        words = [
            word
            for word in normalized.split()
            if len(word) > 3 and word not in _DYNAMIC_DOMAIN_STOPWORDS
        ]
        dynamic_terms.update(words)
        dynamic_terms.update(f"{left} {right}" for left, right in zip(words, words[1:]))
    return dynamic_terms


def _profile_domain_context_terms(profile: UserCareerProfile) -> set[str]:
    terms: list[str | None] = [
        profile.career_identity.title,
        profile.career_identity.summary,
        *profile.interests,
    ]
    terms.extend(exp.role for exp in profile.experience)
    terms.extend(exp.summary for exp in profile.experience)
    terms.extend(project.title for project in profile.projects)
    terms.extend(project.summary for project in profile.projects)
    return _dynamic_domain_terms(terms)


def infer_seniority_gap(user_title: str | None, role_title: str | None) -> tuple[str, float]:
    return seniority_gap(seniority_level_from_title(user_title), seniority_level_from_title(role_title))


def _latest_experience_title(profile: UserCareerProfile) -> str | None:
    for exp in profile.experience:
        if _clean_text(exp.role):
            return exp.role
    return profile.career_identity.title


def _fetch_catalog(
    v_capability: list[float],
    v_intent: list[float],
    v_identity: list[float],
) -> tuple[
    list[dict],
    dict[str, str],
    dict[str, list[str]],
    dict[str, list[tuple[str, str]]],
]:
    from psycopg2.extras import RealDictCursor

    from backend.app.core.database import get_db_connection

    roles_sql = """
        SELECT
            cr.role_id,
            COALESCE(NULLIF(cr.processed_job_title, ''), cr.job_title) AS job_title,
            cr.job_description,
            cr.raw_skills,
            cr.sort_skills,
            cr.domain_tags,
            rs.salary_median_monthly_gross_eur,
            esco.esco_title,
            esco.esco_uri,
            1 - (cr.capability_embedding <=> %(v_capability)s::vector) AS capability_vector_similarity,
            1 - (cr.intent_embedding <=> %(v_intent)s::vector) AS intent_vector_similarity,
            1 - (cr.capability_embedding <=> %(v_identity)s::vector) AS identity_vector_similarity
        FROM career_roles cr
        LEFT JOIN role_salaries rs
          ON rs.role_id = cr.role_id
         AND rs.region = 'Deutschland'
        LEFT JOIN LATERAL (
            SELECT COALESCE(em.esco_title, eo.name) AS esco_title, em.esco_uri
            FROM esco_mappings em
            JOIN esco_occupations eo ON eo.esco_uri = em.esco_uri
            WHERE em.role_id = cr.role_id
            ORDER BY COALESCE(em.esco_title, eo.name), em.esco_uri
            LIMIT 1
        ) esco ON TRUE
        WHERE cr.capability_embedding IS NOT NULL
          AND cr.intent_embedding IS NOT NULL
    """
    # There is no dedicated role-side identity_embedding column (and no plan
    # to add one - see career_path/service.py history): the identity guardrail
    # compares the user's title+summary query vector against each role's
    # existing capability_embedding, the closest available "what is this role"
    # anchor, at zero extra schema/infra cost.
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                roles_sql,
                {
                    "v_capability": _vec_literal(v_capability),
                    "v_intent": _vec_literal(v_intent),
                    "v_identity": _vec_literal(v_identity),
                },
            )
            roles = cur.fetchall()

            cur.execute(
                "SELECT alias_key, canonical_key FROM skill_aliases "
                "WHERE alias_key IS NOT NULL AND canonical_key IS NOT NULL"
            )
            alias_map = {
                normalize_skill_key(row["alias_key"]): normalize_skill_key(row["canonical_key"])
                for row in cur.fetchall()
            }

            cur.execute(
                "SELECT role_id, normalized_skill_name FROM role_skills "
                "WHERE normalized_skill_name IS NOT NULL"
            )
            role_skills: dict[str, list[str]] = defaultdict(list)
            for row in cur.fetchall():
                role_id = str(row["role_id"])
                normalized = normalize_skill_key(row["normalized_skill_name"])
                if normalized and normalized not in role_skills[role_id]:
                    role_skills[role_id].append(normalized)

            cur.execute(
                """
                SELECT cm.role_id, c.certification_name, c.normalized_certification_name
                FROM certifications_mapping cm
                JOIN certifications c ON c.certification_id = cm.certification_id
                WHERE c.certification_name IS NOT NULL
                """
            )
            role_certs: dict[str, list[tuple[str, str]]] = defaultdict(list)
            for row in cur.fetchall():
                display = _clean_text(row["certification_name"])
                normalized = normalize_certification_name(
                    row.get("normalized_certification_name") or display
                )
                role_id = str(row["role_id"])
                if display and normalized and (display, normalized) not in role_certs[role_id]:
                    role_certs[role_id].append((display, normalized))

    return roles, alias_map, role_skills, role_certs


def _role_required_skills(row: dict, role_skills: dict[str, list[str]], alias_map: dict[str, str]) -> list[str]:
    required = required_skills_from_sort_skills(row.get("sort_skills"))
    if required:
        return required
    role_id = str(row["role_id"])
    if role_skills.get(role_id):
        return role_skills[role_id]
    return normalize_user_skills(_listify(row.get("raw_skills")), alias_map)


def _domain_overlap(
    role_domains: list[str],
    profile_domains: list[str],
    *,
    profile_context_terms: set[str] | None = None,
    role_title: str | None = None,
    esco_title: str | None = None,
) -> tuple[float, list[str]]:
    role_domain_set = {normalize_skill_key(domain).replace(" ", "_") for domain in role_domains}
    profile_domain_set = set(profile_domains)
    matched = [domain for domain in role_domains if normalize_skill_key(domain).replace(" ", "_") in profile_domain_set]
    if not role_domain_set:
        base_overlap = 0.0
    else:
        base_overlap = len({normalize_skill_key(domain).replace(" ", "_") for domain in matched}) / len(
            role_domain_set
        )

    if profile_context_terms:
        role_context_terms = _dynamic_domain_terms([role_title, esco_title, *role_domains])
        dynamic_matches = role_context_terms & profile_context_terms
        if dynamic_matches:
            dynamic_overlap = min(0.85, len(dynamic_matches) / max(len(role_context_terms), 1))
            return max(base_overlap, dynamic_overlap), matched

    return base_overlap, matched


def _cert_overlap(role_certs: list[tuple[str, str]], user_cert_norms: set[str]) -> tuple[float, list[str]]:
    if not role_certs:
        return 0.0, []
    matched = [
        display
        for display, normalized in role_certs
        if certification_match_keys(normalized or display) & user_cert_norms
    ]
    return len(matched) / len(role_certs), matched


def _candidate_from_row(
    row: dict,
    *,
    alias_map: dict[str, str],
    role_skills: dict[str, list[str]],
    role_certs: dict[str, list[tuple[str, str]]],
    prepared_skills: PreparedSkillProfile,
    profile_domains: list[str],
    profile_context_terms: set[str],
    user_cert_norms: set[str],
    user_title: str | None,
) -> Candidate:
    role_id = str(row["role_id"])
    required_skills = _role_required_skills(row, role_skills, alias_map)
    skill_weights = skill_weight_map(row.get("sort_skills"))
    # prepared_skills is computed once per /match request (see _match_roles_sync)
    # and reused across every candidate role here, instead of re-walking the
    # user's ontology closure hundreds of times (once per role) as the
    # evidence+enable_ontology_tiers path would.
    alignment = align_skills(required_skills, alias_map=alias_map, skill_weights=skill_weights, prepared=prepared_skills)

    role_domains = [normalize_skill_key(domain).replace(" ", "_") for domain in _listify(row.get("domain_tags"))]
    domain_overlap, matched_domains = _domain_overlap(
        role_domains,
        profile_domains,
        profile_context_terms=profile_context_terms,
        role_title=row.get("job_title"),
        esco_title=row.get("esco_title"),
    )

    cert_overlap, matched_certs = _cert_overlap(role_certs.get(role_id, []), user_cert_norms)
    role_seniority_gap, role_seniority_fit = infer_seniority_gap(user_title, row.get("job_title"))

    return Candidate(
        role_id=role_id,
        job_title=row.get("job_title") or "",
        description=_clean_role_card_summary(row.get("job_description")) or "",
        salary=_format_salary(row.get("salary_median_monthly_gross_eur")),
        esco_title=row.get("esco_title") or "",
        esco_uri=row.get("esco_uri") or "",
        required_skills=required_skills,
        domain_tags=role_domains,
        capability_vector_similarity=float(row.get("capability_vector_similarity") or 0.0),
        intent_vector_similarity=float(row.get("intent_vector_similarity") or 0.0),
        identity_vector_similarity=float(row.get("identity_vector_similarity") or 0.0),
        normalized_skill_overlap=alignment.coverage,
        interest_domain_overlap=domain_overlap,
        certification_overlap=cert_overlap,
        seniority_fit=role_seniority_fit,
        seniority_gap=role_seniority_gap,
        matched_skills=alignment.matched_skills,
        missing_skills=alignment.missing_skills,
        matched_domains=matched_domains,
        matched_certifications=matched_certs,
    )


def _match_roles_sync(
    profile: UserCareerProfile,
    top_k: int,
    include_debug: bool,
) -> RoleMatchResponse:
    from backend.app.features.role_matching.embedder import get_embedder

    capability_text = build_capability_text(profile)
    intent_text = build_intent_text(profile)
    identity_text = build_identity_text(profile)

    v_capability, v_intent, v_identity = get_embedder().encode_queries(
        [capability_text, intent_text, identity_text]
    )
    roles, alias_map, role_skills, role_certs = _fetch_catalog(v_capability, v_intent, v_identity)

    normalized_user_skills = normalize_user_skills(_profile_skill_terms(profile), alias_map)
    skill_evidence = build_skill_evidence_from_user_profile(profile)
    prepared_skills = prepare_user_skills(skill_evidence, alias_map)
    profile_domains = map_profile_domains(profile)
    profile_context_terms = _profile_domain_context_terms(profile)
    user_cert_norms = normalize_user_certifications(
        cert.name for cert in profile.certifications if _clean_text(cert.name)
    )
    user_title = _latest_experience_title(profile)

    candidates = [
        _candidate_from_row(
            row,
            alias_map=alias_map,
            role_skills=role_skills,
            role_certs=role_certs,
            prepared_skills=prepared_skills,
            profile_domains=profile_domains,
            profile_context_terms=profile_context_terms,
            user_cert_norms=user_cert_norms,
            user_title=user_title,
        )
        for row in roles
    ]

    buckets = recommend(candidates, top_k=top_k)

    logger.info(
        "Matched %d roles -> ready=%d next=%d aspirational=%d",
        len(candidates),
        len(buckets.ready_now),
        len(buckets.next_step),
        len(buckets.aspirational),
    )
    logger.info(
        "Recommended role_ids: ready_now=%s next_step=%s aspirational=%s",
        [role.role_id for role in buckets.ready_now],
        [role.role_id for role in buckets.next_step],
        [role.role_id for role in buckets.aspirational],
    )

    return RoleMatchResponse(
        buckets=buckets,
        debug=RoleMatchDebug(
            capability_text=capability_text,
            intent_text=intent_text,
            normalized_user_skills=normalized_user_skills,
            mapped_domains=profile_domains,
        )
        if include_debug
        else None,
    )


def _selected_roles(response: RoleMatchResponse) -> list[RoleMatch]:
    return [
        *response.buckets.ready_now,
        *response.buckets.next_step,
        *response.buckets.aspirational,
    ]


def _summary_payload(roles: list[RoleMatch]) -> dict[str, Any]:
    return {
        "roles": [
            {
                "role_id": str(role.role_id),
                "title": role.job_title,
                "esco_title": role.esco_title,
                "description": _clean_role_card_summary(role.description) or "",
            }
            for role in roles
        ],
    }


async def _apply_role_summaries(_profile: UserCareerProfile, response: RoleMatchResponse) -> None:
    roles = _selected_roles(response)
    if not roles:
        return

    try:
        generated = await openai_client.parse_structured(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Write one role-card description per role. "
                        "Each summary must be one or two present-tense sentences under 35 words and 180 characters. "
                        "Describe concrete day-to-day work plus the outcome the role creates. "
                        "Avoid repetitive generic openers like 'Provides' or 'Develops' when a more specific verb fits. "
                        "Do not mention the user, candidate, profile, fit, readiness, matched skills, "
                        "missing skills, salary, certifications, or recommendations. "
                        "Do not list skills. "
                        "Use only supplied role title, ESCO title, and catalog description."
                    ),
                },
                {"role": "user", "content": json.dumps(_summary_payload(roles))},
            ],
            response_format=RoleSummaryBatch,
            model_purpose="role_description",
        )
    except Exception as exc:
        logger.warning("Role summary generation failed; using catalog descriptions: %s", exc)
        return

    if generated is None:
        return

    summaries = {
        item.role_id: cleaned
        for item in generated.summaries
        if (cleaned := _clean_role_card_summary(item.summary))
    }
    for role in roles:
        summary = summaries.get(str(role.role_id))
        if summary:
            role.description = summary


async def match_roles_for_profile(
    profile: UserCareerProfile,
    top_k: int = 9,
    include_debug: bool = False,
) -> RoleMatchResponse:
    """Offload blocking embedding + DB work to a worker thread."""
    response = await asyncio.to_thread(_match_roles_sync, profile, top_k, include_debug)
    await _apply_role_summaries(profile, response)
    return response
