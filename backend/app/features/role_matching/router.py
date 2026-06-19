import logging

from fastapi import APIRouter, HTTPException

from backend.app.features.role_matching.schemas import RoleMatchRequest, RoleMatchResponse
from backend.app.features.role_matching.service import match_roles_for_cv

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])
logger = logging.getLogger("CareerCompass.RoleMatching.Router")


@router.post("/match", response_model=RoleMatchResponse)
async def match_roles(request: RoleMatchRequest) -> RoleMatchResponse:
    """

    """
    logger.info(
        "Role match request: top_k=%d mode=%s",
        request.top_k,
        request.mode.value,
    )
    try:
        return await match_roles_for_cv(
            confirmed_profile=request.confirmed_profile,
            identity=request.identity,
            top_k=request.top_k,
            mode=request.mode,
        )
    except Exception as exc:
        logger.exception("Role matching failed: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc))
