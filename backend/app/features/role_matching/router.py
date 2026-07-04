import asyncio
import logging

from fastapi import APIRouter, HTTPException

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.career_path import generate_career_path
from backend.app.features.role_matching.gap_analysis import explain_role_gap, fetch_skill_aliases
from backend.app.features.role_matching.prepared_skills import PreparedSkillProfile
from backend.app.features.role_matching.schemas import CareerPathReport, CareerResultsV1, GapReport, RoleMatchRequest
from backend.app.features.role_matching.service import match_roles_for_profile
from backend.app.features.role_matching.skill_alignment import prepare_confirmed_profile_skills

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])
logger = logging.getLogger("CareerCompass.RoleMatching.Router")


@router.post("/prepare-skills", response_model=PreparedSkillProfile)
async def prepare_skills(cv_data: CVData) -> PreparedSkillProfile:
    """One-time, role-agnostic skill preparation (normalize + alias-resolve +
    ontology-canonicalize + hop-decayed closure) run right after CV
    confirmation, so /gap-analysis and /career-path don't redo it per call.
    Call once, attach the result as ConfirmedCVData.prepared_skills, reuse for
    every role the user inspects in the session."""
    try:
        alias_map = await asyncio.to_thread(fetch_skill_aliases)
        return await asyncio.to_thread(prepare_confirmed_profile_skills, cv_data, alias_map)
    except Exception as exc:
        logger.exception("Skill preparation failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/match", response_model=CareerResultsV1)
async def match_roles(request: RoleMatchRequest) -> CareerResultsV1:
    """Match one clean career profile against the Supabase role catalog."""
    logger.info(
        "Role match request: top_k=%d include_debug=%s",
        request.top_k,
        request.include_debug,
    )
    try:
        response = await match_roles_for_profile(
            profile=request.profile,
            top_k=request.top_k,
            include_debug=request.include_debug,
        )
        return CareerResultsV1.from_bucketed_roles(response.buckets)
    except Exception as exc:
        logger.exception("Role matching failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{role_id}/gap-analysis", response_model=GapReport)
async def analyze_role_gap(role_id: int, confirmed_profile: ConfirmedCVData) -> GapReport:
    try:
        return await explain_role_gap(role_id, confirmed_profile)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Gap analysis failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))


@router.post("/{role_id}/career-path", response_model=CareerPathReport)
async def create_career_path(role_id: int, confirmed_profile: ConfirmedCVData) -> CareerPathReport:
    try:
        return await generate_career_path(role_id, confirmed_profile)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.exception("Career path generation failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
