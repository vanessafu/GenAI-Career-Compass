import logging

from fastapi import APIRouter, HTTPException

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.career_path import generate_career_path
from backend.app.features.role_matching.gap_analysis import explain_role_gap
from backend.app.features.role_matching.schemas import CareerPathReport, CareerResultsV1, GapReport, RoleMatchRequest
from backend.app.features.role_matching.service import match_roles_for_profile

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])
logger = logging.getLogger("CareerCompass.RoleMatching.Router")


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
