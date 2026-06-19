import logging

from fastapi import APIRouter, HTTPException

from backend.app.core.pipeline_debug import derive_profile_stem, save_pipeline_artifact
from backend.app.features.cv_confirmation.manual_schemas import ManualCVInput
from backend.app.features.cv_confirmation.manual_service import (
    ManualCVValidationError,
    build_cv_data_from_manual_input,
)
from backend.app.features.cv_parsing.debug_output import save_cv_debug_artifact
from backend.app.features.cv_parsing.schemas import CVData

router = APIRouter(prefix="/api/v1", tags=["CV Confirmation"])
logger = logging.getLogger("CareerCompass.CVConfirmation.Router")


@router.post("/manual-cv", response_model=CVData)
async def create_manual_cv(request: ManualCVInput) -> CVData:
    """Build structured CVData from a manually entered profile."""
    try:
        cv = build_cv_data_from_manual_input(request)
    except ManualCVValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    save_cv_debug_artifact(cv, name="manual_entry")
    save_pipeline_artifact(
        "02_confirmed_cv",
        cv,
        profile_stem=derive_profile_stem(cv, fallback="manual_entry"),
    )
    return cv
