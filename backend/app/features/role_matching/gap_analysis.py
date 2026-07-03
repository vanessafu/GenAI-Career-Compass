"""
Gap analysis (decoupled). The service calls analyze_role_gap() / explain_role_gap().

Dimensions:
  1. Skills         -> ontology coverage (exact + implied + transferable) [skill_ontology]
  2. Certifications -> exact normalized certification overlap
  3. Seniority      -> user level/years vs the role's inferred level
  4. Readiness      -> weighted aggregate of the above

"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from psycopg2.extras import RealDictCursor

from backend.app.core.database import get_db_connection
from backend.app.core.openai_client import parse_structured
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.normalization import (
    canon_seniority_label,
    certification_match_keys,
    normalize_certification_name,
    normalize_skill_key,
    normalize_user_certifications,
    required_skills_from_sort_skills,
    seniority_gap,
    seniority_level_from_title,
    skill_domain_map,
    skill_weight_map,
)
from backend.app.features.role_matching.schemas import (
    CertificationDimension,
    CertificationGap,
    DimensionStatus,
    GapActionItem,
    GapNarrative,
    GapReport,
    SeniorityDimension,
    SkillDimension,
    SkillGap,
)
from backend.app.features.role_matching.service import _listify, as_cv_data
from backend.app.features.role_matching.skill_alignment import (
    SkillEvidence,
    align_skills,
    build_skill_evidence_from_confirmed_profile,
)

logger = logging.getLogger("CareerCompass.GapAnalysis")

# --- tunables --------------------------------------------------------------
READINESS_W = {"skills": 0.60, "certifications": 0.25, "seniority": 0.15}
MAX_GROUNDING_SKILLS = 8   # cap missing skills sent to the LLM (prompt budget)


# ===========================================================================
# small helpers
# ===========================================================================
def _status(coverage: float) -> DimensionStatus:
    if coverage >= 0.70:
        return "strong"
    if coverage >= 0.35:
        return "partial"
    return "weak"


# Extract user-side facts from the confirmed profile
def _user_certs(profile: ConfirmedCVData) -> list[str]:
    cv_data = as_cv_data(profile)
    return [c.name for c in cv_data.certifications if c.name]


def _user_seniority(profile: ConfirmedCVData) -> tuple[Optional[str], Optional[int]]:
    ps = as_cv_data(profile).profile_summary
    level = canon_seniority_label(ps.current_seniority_level)
    years = ps.years_of_experience
    return level, years


def _fetch_role(role_id: int) -> Optional[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT role_id, COALESCE(NULLIF(processed_job_title, ''), job_title) AS job_title, "
                "job_description, raw_skills, domain_tags, sort_skills "
                "FROM career_roles WHERE role_id = %s",
                (role_id,),
            )
            return cur.fetchone()




def _fetch_role_certs(role_id: int) -> list[dict]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT c.certification_name, c.normalized_certification_name "
                "FROM certifications_mapping cm "
                "JOIN certifications c ON c.certification_id = cm.certification_id "
                "WHERE cm.role_id = %s "
                "ORDER BY c.certification_name",
                (role_id,),
            )
            return cur.fetchall()


def _fetch_skill_aliases() -> dict[str, str]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT alias_key, canonical_key FROM skill_aliases "
                "WHERE alias_key IS NOT NULL AND canonical_key IS NOT NULL"
            )
            return {
                normalize_skill_key(row["alias_key"]): normalize_skill_key(row["canonical_key"])
                for row in cur.fetchall()
                if normalize_skill_key(row["alias_key"]) and normalize_skill_key(row["canonical_key"])
            }


def _fetch_role_skills_from_table(role_id: int) -> list[str]:
    """Fallback required-skills source for roles never reprocessed into
    sort_skills - the older, structured role_skills relation."""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT normalized_skill_name FROM role_skills "
                "WHERE role_id = %s AND normalized_skill_name IS NOT NULL "
                "ORDER BY normalized_skill_name",
                (role_id,),
            )
            required = [
                normalized
                for row in cur.fetchall()
                if (normalized := normalize_skill_key(row["normalized_skill_name"]))
            ]
    return list(dict.fromkeys(required))


def _retrieve_esco_grounding(role_id: int, missing_skills: list[str]) -> tuple[Optional[str], dict[str, str]]:
    """RAG: official occupation title for the role + ESCO descriptions for the
    missing skills, so the LLM explains them accurately instead of guessing.
    Adjust esco_skills/esco_occupations column names to your schema."""
    descriptions: dict[str, str] = {}
    occupation_title: Optional[str] = None
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT COALESCE(em.esco_title, eo.name) AS occupation_title "
                "FROM esco_mappings em "
                "JOIN esco_occupations eo ON eo.esco_uri = em.esco_uri "
                "WHERE em.role_id = %s",
                (role_id,),
            )
            row = cur.fetchone()
            if row:
                occupation_title = row.get("occupation_title")

            for skill in missing_skills[:MAX_GROUNDING_SKILLS]:
                cur.execute(
                    "SELECT preferred_label, description FROM esco_skills "
                    "WHERE lower(preferred_label) = lower(%s) LIMIT 1",
                    (skill,),
                )
                hit = cur.fetchone()
                if not hit:  # fuzzy fallback
                    cur.execute(
                        "SELECT preferred_label, description FROM esco_skills "
                        "WHERE preferred_label ILIKE %s ORDER BY length(preferred_label) LIMIT 1",
                        (f"%{skill}%",),
                    )
                    hit = cur.fetchone()
                if hit and hit.get("description"):
                    descriptions[skill] = hit["description"]
    return occupation_title, descriptions


def _analyze_skills(
    required_skills: list[str],
    user_evidence: SkillEvidence,
    alias_map: dict[str, str],
    skill_weights: dict[str, float],
    skill_domains: dict[str, str],
) -> SkillDimension:
    alignment = align_skills(required_skills, user_evidence, alias_map, skill_weights, skill_domains)
    return SkillDimension(
        matched_skills=alignment.matched_skills,
        missing_skills=alignment.missing_skills,
        skill_gaps=[
            SkillGap(
                required_skill=g["required_skill"],
                user_closest_skill=g["user_closest_skill"],
                transferability=g["transferability"],
                severity=g["severity"],
                importance=g.get("importance", ""),
                domain=g.get("domain", ""),
                source="shared_alignment",
            )
            for g in alignment.skill_gaps
        ],
        domain_coverage=alignment.domain_scores,
        domain_skills=alignment.domain_skills,
        coverage=alignment.coverage,
        status=_status(alignment.coverage),
    )


def _analyze_certs(role_certs: list[dict], user_certs: list[str]) -> CertificationDimension:
    if not role_certs:  # role requires no certs -> not a gap
        return CertificationDimension(coverage=1.0, status="strong")

    user_norm = normalize_user_certifications(user_certs)
    held: list[str] = []
    missing: list[CertificationGap] = []

    for rc in role_certs:
        name = rc["certification_name"]
        norm = normalize_certification_name(rc.get("normalized_certification_name") or name)
        if certification_match_keys(norm) & user_norm:
            held.append(name)
            continue
        missing.append(
            CertificationGap(
                required_certification=name,
                normalized_name=norm,
                user_closest_certification=None,
                similarity=0.0,
                status="missing",
            )
        )

    total = len(role_certs)
    coverage = len(held) / total
    return CertificationDimension(held=held, related=[], missing=missing,
                                  coverage=coverage, status=_status(coverage))


def _analyze_seniority(
    role_title: str, user_level: Optional[str], user_years: Optional[int]
) -> tuple[SeniorityDimension, float]:
    role_level = seniority_level_from_title(role_title)
    gap, fit = seniority_gap(user_level, role_level)
    note = None
    if gap == "stretch":
        note = f"Role looks {role_level}; you are {user_level}. Expect a stretch in scope/leadership."
    elif gap == "overqualified":
        note = f"You ({user_level}) may be over-levelled for a {role_level} role."
    dimension = SeniorityDimension(
        user_level=user_level, role_level=role_level, user_years=user_years, gap=gap, note=note
    )
    return dimension, fit



# ===========================================================================
# RAG + LLM narrative layer
# ===========================================================================

_SYSTEM_PROMPT = (
    "You are an explainable career-gap advisor. You receive a PRE-COMPUTED gap "
    "analysis and official ESCO skill context. Do NOT invent gaps, skills, or "
    "certifications: only explain and prioritise what is given. Ground every "
    "explanation in the provided context."
)


def _build_user_prompt(report: GapReport, occupation_title: Optional[str],
                       descriptions: dict[str, str]) -> str:
    facts = {
        "target_role": report.job_title,
        "official_esco_occupation": occupation_title,
        "overall_readiness": round(report.overall_readiness, 3),
        "skill_coverage": round(report.skills.coverage, 3),
        "matched_skills": report.skills.matched_skills,
        "missing_or_partial_skills": [
            {"skill": g.required_skill, "closest_user_skill": g.user_closest_skill,
             "transferability": g.transferability, "severity": g.severity}
            for g in report.skills.skill_gaps
        ],
        "certifications": {
            "held": report.certifications.held,
            "related": [c.required_certification for c in report.certifications.related],
            "missing": [c.required_certification for c in report.certifications.missing],
        },
        "seniority": report.seniority.model_dump(),
        "esco_skill_context": descriptions,
        "role_description": (report.job_description or "")[:1200],
    }
    return (
        "Here is the pre-computed gap analysis. Produce a prioritised, grounded "
        "action plan that closes the gaps, hardest/most-important first.\n\n"
        + json.dumps(facts, ensure_ascii=False, indent=2)
    )


async def _generate_narrative(
    report: GapReport, occupation_title: Optional[str], descriptions: dict[str, str]
) -> Optional[GapNarrative]:
    try:
        return await parse_structured(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(report, occupation_title, descriptions)},
            ],
            response_format=GapNarrative,
        )
    except Exception as exc:
        logger.warning("Gap narrative generation failed: %s", exc)
        return None


# ===========================================================================
# Public API
# ===========================================================================

def analyze_role_gap(
    role_id: int,
    confirmed_profile: ConfirmedCVData,
) -> GapReport:
    """Deterministic multi-dimensional gap report (no LLM). Call explain_role_gap
    for the async version that also generates the narrative."""
    role = _fetch_role(role_id)
    if role is None:
        raise ValueError(f"role_id {role_id} not found")

    user_evidence = build_skill_evidence_from_confirmed_profile(confirmed_profile)
    user_certs = _user_certs(confirmed_profile)
    user_level, user_years = _user_seniority(confirmed_profile)

    sort_skills = role.get("sort_skills")
    alias_map = _fetch_skill_aliases()
    required_skills = required_skills_from_sort_skills(sort_skills)
    if not required_skills:
        required_skills = _fetch_role_skills_from_table(role_id)
    if not required_skills:
        required_skills = _listify(role.get("raw_skills"))
    skill_weights = skill_weight_map(sort_skills)
    skill_domains = skill_domain_map(sort_skills)

    skills = _analyze_skills(required_skills, user_evidence, alias_map, skill_weights, skill_domains)
    certs = _analyze_certs(_fetch_role_certs(role_id), user_certs)
    seniority, seniority_fit = _analyze_seniority(role["job_title"], user_level, user_years)

    readiness = (
        READINESS_W["skills"] * skills.coverage
        + READINESS_W["certifications"] * certs.coverage
        + READINESS_W["seniority"] * seniority_fit
    )

    return GapReport(
        role_id=role_id,
        job_title=role["job_title"],
        job_description=role.get("job_description"),
        domain_tags=_listify(role.get("domain_tags")),
        overall_readiness=readiness,
        skills=skills,
        certifications=certs,
        seniority=seniority,
    )


async def explain_role_gap(
    role_id: int,
    confirmed_profile: ConfirmedCVData,
    *,
    with_narrative: bool = True,
) -> GapReport:
    """Full async gap report: deterministic dimensions (in thread) + OpenAI narrative."""
    report = await asyncio.to_thread(analyze_role_gap, role_id, confirmed_profile)

    if with_narrative:
        missing = [g.required_skill for g in report.skills.skill_gaps if g.severity in ("medium", "high")]
        occupation_title, descriptions = await asyncio.to_thread(
            _retrieve_esco_grounding, role_id, missing
        )
        report.grounding_used = list(descriptions.keys())
        report.narrative = await _generate_narrative(report, occupation_title, descriptions)

    return report
