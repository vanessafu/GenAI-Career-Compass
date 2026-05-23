from fastapi import APIRouter, HTTPException

from backend.app.features.role_matching.schemas import RoleMatchRequest, RoleMatchResponse
from backend.app.features.role_matching.service import match_roles_for_cv

router = APIRouter(prefix="/api/v1/roles", tags=["Role Matching"])


@router.post("/match", response_model=RoleMatchResponse)
async def match_roles(request: RoleMatchRequest):
    """
    Match a parsed CV against ESCO occupations via pgvector similarity search.
    Requires the database to be populated first — run the three scripts in order:
        python -m backend.scripts.data_loader
        python -m backend.scripts.data_preprocessing
        python -m backend.scripts.build_embeddings
    """
    try:
        return await match_roles_for_cv(request.cv_data, top_k=request.top_k)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))
