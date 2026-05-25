from fastapi import APIRouter, HTTPException

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.prompt_engineering.embedding_preparation_service import (
    build_embedding_input,
)
from backend.app.features.prompt_engineering.schemas import (
    EmbeddingInputResponse,
    StarterProfileResponse,
)
from backend.app.features.prompt_engineering.service import generate_starter_profile

router = APIRouter(prefix="/api/v1/prompt-engineering", tags=["Prompt Engineering"])


@router.post("/starter-profile", response_model=StarterProfileResponse)
async def create_starter_profile(confirmed_profile: ConfirmedCVData) -> StarterProfileResponse:
    """Generate the initial editable identity and follow-up questions from confirmed CV JSON."""
    try:
        return await generate_starter_profile(confirmed_profile)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/embedding-input", response_model=EmbeddingInputResponse)
async def create_embedding_input(confirmed_profile: ConfirmedCVData) -> EmbeddingInputResponse:
    """Build deterministic embedding input text from confirmed CV JSON."""
    return build_embedding_input(confirmed_profile)
