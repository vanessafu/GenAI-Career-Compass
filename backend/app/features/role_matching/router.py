import logging

from fastapi import APIRouter, HTTPException

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.profile_preparation.cv_privacy_service import privacy_strip_cv_data
from backend.app.features.role_matching.career_path import generate_career_path
from backend.app.features.role_matching.schemas import (
    CareerPathReport,
    CareerResultsV1,
    RoleMatchRequest,
)
from backend.app.features.role_matching.service import match_roles_for_profile

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])
logger = logging.getLogger("CareerCompass.RoleMatching.Router")


def _privacy_safe(profile: ConfirmedCVData) -> ConfirmedCVData:
    return profile.model_copy(
        update={"confirmed_cv_data": privacy_strip_cv_data(profile.confirmed_cv_data)}
    )




@router.post("/match", response_model=CareerResultsV1)
async def match_roles(request: RoleMatchRequest) -> CareerResultsV1:
    logger.info("Role match request: top_k=%d", request.top_k)
    try:
        response = await match_roles_for_profile(
            profile=request.profile,
            top_k=request.top_k,
            include_debug=False,
        )
        return CareerResultsV1.from_bucketed_roles(response.buckets)
    except Exception as exc:
        logger.exception("Role matching failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Role matching is temporarily unavailable.",
        ) from exc




@router.post("/{role_id}/career-path", response_model=CareerPathReport)
async def create_career_path(role_id: int, confirmed_profile: ConfirmedCVData) -> CareerPathReport:
    try:
        return await generate_career_path(role_id, _privacy_safe(confirmed_profile))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Role not found.") from exc
    except Exception as exc:
        logger.exception("Career path generation failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Career path generation is temporarily unavailable.",
        ) from exc