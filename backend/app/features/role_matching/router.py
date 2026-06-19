import logging

from fastapi import APIRouter, HTTPException

from backend.app.features.role_matching.schemas import CareerResultsV1, RoleMatchRequest
from backend.app.features.role_matching.service import match_roles_for_profile

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])
logger = logging.getLogger("CareerCompass.RoleMatching.Router")


@router.post("/match", response_model=CareerResultsV1)
async def match_roles(request: RoleMatchRequest) -> CareerResultsV1:
    """Match one clean career profile against the Supabase role catalog."""
    logger.info(
        "Role match request: top_k=%d mode=%s include_debug=%s",
        request.top_k,
        request.mode.value,
        request.include_debug,
    )
    try:
        response = await match_roles_for_profile(
            profile=request.profile,
            top_k=request.top_k,
            mode=request.mode,
            include_debug=request.include_debug,
        )
        return CareerResultsV1.from_bucketed_roles(response.buckets)
    except Exception as exc:
        logger.exception("Role matching failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
