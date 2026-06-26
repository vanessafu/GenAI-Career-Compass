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
from backend.app.features.role_matching.recommendation import Candidate, recommend
from backend.app.features.role_matching.schemas import (
    RecommendationMode,
    RoleMatch,
    RoleMatchDebug,
    RoleMatchResponse,
    RoleSummaryBatch,
    UserCareerProfile,
)

logger = logging.getLogger("CareerCompass.RoleMatching.Service")

_MAX_TEXT = 700
_MAX_ROLE_CARD_SUMMARY = 150

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

_SENIORITY_ORDER = ["intern", "junior", "mid", "senior", "lead", "staff", "principal", "director"]
_SENIORITY_ALIASES = {
    "entry": "junior",
    "entry level": "junior",
    "associate": "junior",
    "apprentice": "junior",
    "beginner": "junior",
    "graduate": "junior",
    "jr": "junior",
    "student": "junior",
    "trainee": "junior",
    "intermediate": "mid",
    "regular": "mid",
    "sr": "senior",
    "snr": "senior",
    "architect": "lead",
    "team lead": "lead",
    "tech lead": "lead",
    "head": "director",
    "vp": "director",
    "chief": "director",
}

DEFAULT_SKILL_ALIASES: dict[str, str] = {
    "api": "rest apis",
    "apis": "rest apis",
    "rest api": "rest apis",
    "restful api": "restful apis",
    "spring": "spring framework",
    "spring boot": "spring framework",
    "figma": "ui ux design",
    "ux": "ui ux design",
    "ui": "ui ux design",
    "accessibility": "web accessibility guidelines",
    "a11y": "web accessibility guidelines",
    "data": "data analysis",
    "analytics": "data analysis",
    "data analytics": "data analysis",
    "pandas": "python",
    "ci": "ci cd",
    "ci/cd": "ci cd",
    "continuous integration": "ci cd",
    "continuous integration ci": "ci cd",
    "automated testing": "test automation",
    "azure cloud": "azure",
    "linux services": "linux",
    "shell scripts": "scripting",
}

_CERTIFICATION_ALIAS_GROUPS_RAW: tuple[tuple[str, ...], ...] = (
    (
        "Google Data Analytics Certificate",
        "Google Data Analytics Professional Certificate",
    ),
    (
        "Oracle Certified Associate Java Programmer",
        "Oracle Certified Associate (OCA) - Java",
        "Oracle Java Programmer Certification",
        "OCA Java",
    ),
    (
        "CompTIA A+",
        "CompTIA A Plus",
        "CompTIA A+ Certification",
    ),
)


def as_cv_data(profile: ConfirmedCVData | CVData) -> CVData:
    """Return the raw CV parser payload for older gap-analysis helpers."""
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
    sentence_end = re.search(r"[.!?](?:\s|$)", cleaned)
    if sentence_end:
        cleaned = cleaned[: sentence_end.end()].strip()
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


def _normalize_key(value: str | None) -> str:
    value = (value or "").casefold()
    value = re.sub(r"[^a-z0-9+#]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_certification_name(name: str | None) -> str:
    value = (name or "").casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


_CERTIFICATION_ALIAS_GROUPS = tuple(
    frozenset(
        normalized
        for normalized in (normalize_certification_name(name) for name in group)
        if normalized
    )
    for group in _CERTIFICATION_ALIAS_GROUPS_RAW
)
_CERTIFICATION_ALIAS_MAP = {
    alias: group for group in _CERTIFICATION_ALIAS_GROUPS for alias in group
}


def certification_match_keys(name: str | None) -> set[str]:
    normalized = normalize_certification_name(name)
    if not normalized:
        return set()
    return set(_CERTIFICATION_ALIAS_MAP.get(normalized, {normalized}))


def normalize_user_certifications(certification_names: Iterable[str | None]) -> set[str]:
    normalized: set[str] = set()
    for name in certification_names:
        normalized.update(certification_match_keys(name))
    return normalized


def normalize_user_skills(skills: Iterable[str], alias_map: dict[str, str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    clean_alias_map = {
        _normalize_key(alias): _normalize_key(canonical)
        for alias, canonical in DEFAULT_SKILL_ALIASES.items()
    }
    clean_alias_map.update(
        {_normalize_key(alias): _normalize_key(canonical) for alias, canonical in alias_map.items()}
    )
    for skill in skills:
        key = _normalize_key(skill)
        if not key:
            continue
        canonical = clean_alias_map.get(key, key)
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


def extract_user_skills(profile: ConfirmedCVData | CVData | UserCareerProfile) -> list[str]:
    """Union of user skills for both the new profile schema and legacy gap helpers."""
    if isinstance(profile, UserCareerProfile):
        return _profile_skill_terms(profile)

    cv_data = as_cv_data(profile)
    skills: list[str] = []

    extracted = getattr(cv_data, "skills_extracted", None)
    for technical_skill in (getattr(extracted, "technical_skills", None) or []) if extracted else []:
        skills.append(getattr(technical_skill, "name", "") or "")
    for project in getattr(cv_data, "projects", None) or []:
        skills.extend(getattr(project, "technologies", None) or [])
    for thesis in getattr(cv_data, "thesis", None) or []:
        skills.extend(getattr(thesis, "technologies", None) or [])
    for exp in getattr(cv_data, "experience", None) or []:
        skills.extend(getattr(exp, "contextual_skills", None) or [])
    return _dedupe(skills)


def build_capability_text(profile: UserCareerProfile) -> str:
    parts: list[str] = []

    for index, exp in enumerate(profile.experience, start=1):
        line_parts = [
            exp.role,
            f"Organization: {exp.organization}" if _clean_text(exp.organization) else None,
            f"Dates: {exp.start_date}-{exp.end_date}" if exp.start_date or exp.end_date else None,
            f"Summary: {_truncate(exp.summary)}" if _clean_text(exp.summary) else None,
            f"Skills: {_join_unique(exp.skills)}" if _join_unique(exp.skills) else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Experience {index}: {joined}")

    for index, edu in enumerate(profile.education, start=1):
        line_parts = [
            edu.degree,
            f"Institution: {edu.institution}" if _clean_text(edu.institution) else None,
            f"Years: {edu.start_year}-{edu.end_year}" if edu.start_year or edu.end_year else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Education {index}: {joined}")

    skill_text = _join_unique(profile.skills, limit=30)
    if skill_text:
        parts.append(f"Skills: {skill_text}")

    for index, cert in enumerate(profile.certifications, start=1):
        line_parts = [
            cert.name,
            f"Issuer: {cert.issuer}" if _clean_text(cert.issuer) else None,
            f"Year: {cert.year}" if _clean_text(cert.year) else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Certification {index}: {joined}")

    for index, project in enumerate(profile.projects, start=1):
        line_parts = [
            project.title,
            f"Summary: {_truncate(project.summary)}" if _clean_text(project.summary) else None,
            f"Technologies: {_join_unique(project.technologies)}" if _join_unique(project.technologies) else None,
            f"Year: {project.year}" if _clean_text(project.year) else None,
        ]
        joined = _join_unique(line_parts)
        if joined:
            parts.append(f"Project {index}: {joined}")

    return "\n".join(parts).strip()


def build_intent_text(profile: UserCareerProfile) -> str:
    parts: list[str] = []
    if _clean_text(profile.career_identity.title):
        parts.append(f"Career identity: {profile.career_identity.title.strip()}")
    if _clean_text(profile.career_identity.summary):
        parts.append(f"Career summary: {_truncate(profile.career_identity.summary)}")
    interest_text = _join_unique(profile.interests, limit=20)
    if interest_text:
        parts.append(f"Interests: {interest_text}")
    return "\n".join(parts).strip()


def map_profile_domains(profile: UserCareerProfile) -> list[str]:
    terms = [
        profile.career_identity.title or "",
        profile.career_identity.summary or "",
        *profile.interests,
    ]
    normalized_text = " " + _normalize_key(" ".join(terms)) + " "
    domains: list[str] = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            normalized_keyword = " " + _normalize_key(keyword) + " "
            if normalized_keyword in normalized_text:
                domains.append(domain)
                break
    return domains


def _seniority_level(title: str | None) -> str | None:
    text = " " + _normalize_key(title) + " "
    for level in reversed(_SENIORITY_ORDER):
        if f" {level} " in text:
            return level
    for alias, level in _SENIORITY_ALIASES.items():
        if f" {alias} " in text:
            return level
    return None


def infer_seniority_gap(user_title: str | None, role_title: str | None) -> tuple[str, float]:
    user_level = _seniority_level(user_title)
    role_level = _seniority_level(role_title)
    if not user_level or not role_level:
        return "unknown", 0.70

    distance = _SENIORITY_ORDER.index(role_level) - _SENIORITY_ORDER.index(user_level)
    if distance == 0:
        return "match", 1.0
    if distance > 0:
        return "stretch", max(0.25, 0.65 - (0.20 * (distance - 1)))
    return "overqualified", max(0.75, 0.90 - (0.05 * (abs(distance) - 1)))


def _latest_experience_title(profile: UserCareerProfile) -> str | None:
    for exp in profile.experience:
        if _clean_text(exp.role):
            return exp.role
    return profile.career_identity.title


def _fetch_catalog(
    v_capability: list[float],
    v_intent: list[float],
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
            cr.job_title,
            cr.job_description,
            cr.raw_skills,
            cr.domain_tags,
            rs.salary_median_monthly_gross_eur,
            esco.esco_title,
            esco.esco_uri,
            1 - (cr.capability_embedding <=> %(v_capability)s::vector) AS capability_vector_similarity,
            1 - (cr.intent_embedding <=> %(v_intent)s::vector) AS intent_vector_similarity
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
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                roles_sql,
                {
                    "v_capability": _vec_literal(v_capability),
                    "v_intent": _vec_literal(v_intent),
                },
            )
            roles = cur.fetchall()

            cur.execute(
                "SELECT alias_key, canonical_key FROM skill_aliases "
                "WHERE alias_key IS NOT NULL AND canonical_key IS NOT NULL"
            )
            alias_map = {
                _normalize_key(row["alias_key"]): _normalize_key(row["canonical_key"])
                for row in cur.fetchall()
            }

            cur.execute(
                "SELECT role_id, normalized_skill_name FROM role_skills "
                "WHERE normalized_skill_name IS NOT NULL"
            )
            role_skills: dict[str, list[str]] = defaultdict(list)
            for row in cur.fetchall():
                role_id = str(row["role_id"])
                normalized = _normalize_key(row["normalized_skill_name"])
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
    role_id = str(row["role_id"])
    if role_skills.get(role_id):
        return role_skills[role_id]
    return normalize_user_skills(_listify(row.get("raw_skills")), alias_map)


def _overlap(required: list[str], available: set[str]) -> tuple[float, list[str], list[str]]:
    if not required:
        return 0.0, [], []
    matched = [skill for skill in required if skill in available]
    missing = [skill for skill in required if skill not in available]
    return len(matched) / len(required), matched, missing


def _domain_overlap(role_domains: list[str], profile_domains: list[str]) -> tuple[float, list[str]]:
    role_domain_set = {_normalize_key(domain).replace(" ", "_") for domain in role_domains}
    profile_domain_set = set(profile_domains)
    matched = [domain for domain in role_domains if _normalize_key(domain).replace(" ", "_") in profile_domain_set]
    if not role_domain_set:
        return 0.0, []
    return len({ _normalize_key(domain).replace(" ", "_") for domain in matched }) / len(role_domain_set), matched


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
    user_skills: list[str],
    profile_domains: list[str],
    user_cert_norms: set[str],
    user_title: str | None,
) -> Candidate:
    role_id = str(row["role_id"])
    required_skills = _role_required_skills(row, role_skills, alias_map)
    skill_overlap, matched_skills, missing_skills = _overlap(required_skills, set(user_skills))

    role_domains = [_normalize_key(domain).replace(" ", "_") for domain in _listify(row.get("domain_tags"))]
    domain_overlap, matched_domains = _domain_overlap(role_domains, profile_domains)

    cert_overlap, matched_certs = _cert_overlap(role_certs.get(role_id, []), user_cert_norms)
    seniority_gap, seniority_fit = infer_seniority_gap(user_title, row.get("job_title"))

    return Candidate(
        role_id=role_id,
        job_title=row.get("job_title") or "",
        description=_clean_role_card_summary(row.get("job_description")) or "",
        salary=_format_salary(row.get("salary_median_monthly_gross_eur")),
        esco_title=row.get("esco_title") or "",
        esco_uri=row.get("esco_uri") or "",
        capability_vector_similarity=float(row.get("capability_vector_similarity") or 0.0),
        intent_vector_similarity=float(row.get("intent_vector_similarity") or 0.0),
        normalized_skill_overlap=skill_overlap,
        interest_domain_overlap=domain_overlap,
        certification_overlap=cert_overlap,
        seniority_fit=seniority_fit,
        seniority_gap=seniority_gap,
        matched_skills=matched_skills,
        missing_skills=missing_skills,
        matched_domains=matched_domains,
        matched_certifications=matched_certs,
    )


def _match_roles_sync(
    profile: UserCareerProfile,
    top_k: int,
    mode: RecommendationMode,
    include_debug: bool,
) -> RoleMatchResponse:
    from backend.app.features.role_matching.embedder import get_embedder

    capability_text = build_capability_text(profile)
    intent_text = build_intent_text(profile)

    v_capability, v_intent = get_embedder().encode_queries([capability_text, intent_text])
    roles, alias_map, role_skills, role_certs = _fetch_catalog(v_capability, v_intent)

    normalized_user_skills = normalize_user_skills(_profile_skill_terms(profile), alias_map)
    profile_domains = map_profile_domains(profile)
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
            user_skills=normalized_user_skills,
            profile_domains=profile_domains,
            user_cert_norms=user_cert_norms,
            user_title=user_title,
        )
        for row in roles
    ]

    buckets = recommend(
        candidates,
        top_k=None if top_k == 9 and mode == RecommendationMode.BALANCED else top_k,
        mode=mode,
        per_bucket=3 if top_k == 9 and mode == RecommendationMode.BALANCED else None,
    )
    logger.info(
        "Matched %d roles -> ready=%d next=%d aspirational=%d",
        len(candidates),
        len(buckets.ready_now),
        len(buckets.next_step),
        len(buckets.aspirational),
    )

    return RoleMatchResponse(
        mode=mode,
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
                        "Each summary must be one present-tense sentence under 18 words and 150 characters. "
                        "Describe what the role does. "
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
    mode: RecommendationMode = RecommendationMode.BALANCED,
    include_debug: bool = False,
) -> RoleMatchResponse:
    """Offload blocking embedding + DB work to a worker thread."""
    response = await asyncio.to_thread(_match_roles_sync, profile, top_k, mode, include_debug)
    await _apply_role_summaries(profile, response)
    return response
