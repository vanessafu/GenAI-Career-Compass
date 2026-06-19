"""
Role-matching orchestration.
two query embeddings (v_cv, v_interest)
-> pgvector dual-similarity scan -> ontology skill coverage -> recommend().

The heavy work (embedding on CPU/MPS + sync DB) runs in a worker thread so the
async endpoint never blocks the event loop.
"""
from __future__ import annotations

import asyncio
import logging

import numpy as np
from psycopg2.extras import RealDictCursor

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.embedder import get_embedder
from backend.app.features.role_matching.recommendation import Candidate, recommend
from backend.app.features.role_matching.schemas import (
    GapAnalysis,
    RecommendationMode,
    RoleMatchResponse,
    SkillGap,
    UserIdentity,
)
from backend.app.features.role_matching.skill_ontology import get_ontology, parse_raw_skills

# Same pooled, pgvector-registered context manager used by the rebuild script.
# Move it to a shared db module and import it from there.
from backend.app.core.database import get_db_connection

logger = logging.getLogger("CareerCompass.RoleMatching.Service")

# How many top text characters from various fields to keep query texts within the
# embedder's 512-token window.
_MAX_RESP = 400


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


# ---------------------------------------------------------------------------
# Build the two query texts + the user's skill set.
# NOTE: these assume ConfirmedCVData mirrors CVData (the parsed-CV schema) in a compressed form.
# Adjust the field paths to actual ConfirmedCVData shape.
# ---------------------------------------------------------------------------
def build_cv_query_text(profile: ConfirmedCVData) -> str:
    """Current capabilities -> v_cv (a 'query' for bge, so the embedder prefixes it)."""
    # ps = getattr(profile, "profile_summary", None)
    parts: list[str] = []
    skills = extract_user_skills(profile)
    if skills:
        parts.append("Skills: " + ", ".join(skills[:10]))

    for exp in (getattr(profile, "experience", None) or [])[:2]:
        role = getattr(exp, "role", None)
        resp = getattr(exp, "core_responsibilities", None) or []
        if role:
            line = f"Worked as {role}"
            if resp:
                line += ": " + "; ".join(resp)[:_MAX_RESP]
            parts.append(line)
    return "\n".join(parts).strip()


def build_interest_query_text(identity: UserIdentity) -> str:
    """Direction / interest -> v_interest."""
    parts = [identity.career_identity_statement.strip()]
    if identity.career_directions:
        parts.append("Target directions: " + ", ".join(identity.career_directions))
    if identity.interests:
        parts.append("Interests: " + ", ".join(identity.interests))
    return "\n".join(p for p in parts if p).strip()


def extract_user_skills(profile: ConfirmedCVData) -> list[str]:
    """Union of skills across technical_skills, project tech, and contextual skills."""
    out: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        n = (name or "").strip()
        if n and n.lower() not in seen:
            seen.add(n.lower())
            out.append(n)

    se = getattr(profile, "skills_extracted", None)
    for ts in (getattr(se, "technical_skills", None) or []) if se else []:
        add(getattr(ts, "name", "") or "")
    for proj in getattr(profile, "projects", None) or []:
        for tech in getattr(proj, "technologies", None) or []:
            add(tech)
    for exp in getattr(profile, "experience", None) or []:
        for sk in getattr(exp, "contextual_skills", None) or []:
            add(sk)
    return out


def _fetch_scored_roles(v_cv: list[float], v_interest: list[float]) -> list[dict]:
    sql = """
        SELECT role_id, job_title, job_description, raw_skills, domain_tags, embedding,
               1 - (embedding <=> %(v_cv)s::vector)       AS sim_cv,
               1 - (embedding <=> %(v_interest)s::vector) AS sim_interest
        FROM career_roles
        WHERE embedding IS NOT NULL
    """
    params = {"v_cv": _vec_literal(v_cv), "v_interest": _vec_literal(v_interest)}
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def _match_roles_sync(
    confirmed_profile: ConfirmedCVData,
    identity: UserIdentity,
    top_k: int,
    mode: RecommendationMode,
) -> RoleMatchResponse:
    cv_text = build_cv_query_text(confirmed_profile)
    interest_text = build_interest_query_text(identity)
    user_skills = extract_user_skills(confirmed_profile)

    # Both are queries -> encode_queries applies the bge query prefix.
    v_cv, v_interest = get_embedder().encode_queries([cv_text, interest_text])

    rows = _fetch_scored_roles(v_cv, v_interest)
    onto = get_ontology()

    candidates: list[Candidate] = []
    for row in rows:
        coverage, matched, gaps = onto.compute_coverage(row["raw_skills"], user_skills)
        candidates.append(
            Candidate(
                role_id=row["role_id"],
                job_title=row["job_title"],
                description=row["job_description"],
                essential_skills=parse_raw_skills(row["raw_skills"]),
                domain_tags=row["domain_tags"],
                embedding=np.asarray(row["embedding"], dtype=np.float32),
                sim_cv=float(row["sim_cv"]),
                sim_interest=float(row["sim_interest"]),
                skill_coverage=coverage,
                gap_analysis=_build_gap_analysis(coverage, matched, gaps),
            )
        )

    buckets = recommend(candidates, mode=mode, per_bucket=top_k)
    logger.info(
        "Matched %d roles -> ready=%d next=%d aspirational=%d",
        len(candidates),
        len(buckets.ready_now),
        len(buckets.next_step),
        len(buckets.aspirational),
    )
    return RoleMatchResponse(
        mode=mode,
        cv_query_text=cv_text,
        interest_query_text=interest_text,
        career_directions=identity.career_directions,
        buckets=buckets,
    )


async def match_roles_for_cv(
    confirmed_profile: ConfirmedCVData,
    identity: UserIdentity,
    top_k: int = 2,
    mode: RecommendationMode = RecommendationMode.balanced,
) -> RoleMatchResponse:
    """Async wrapper: offload the blocking embed + DB work to a worker thread."""
    return await asyncio.to_thread(
        _match_roles_sync, confirmed_profile, identity, top_k, mode
    )
    
    
def _build_gap_analysis(coverage: float, matched: list[str], gaps: list[dict]) -> GapAnalysis:
    return GapAnalysis(
        matched_skills=matched,
        skill_gaps=[
            SkillGap(
                required_skill=g["required_skill"],
                user_closest_skill=g["user_closest_skill"],
                transferability=g["transferability"],
                severity=g["severity"],
                source="MIND",
            )
            for g in gaps
        ],
        required_count=len(matched) + len(gaps),
        coverage=coverage,
    )
