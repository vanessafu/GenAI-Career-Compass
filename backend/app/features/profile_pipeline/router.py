import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.features.cv_confirmation.manual_schemas import ManualCVInput
from backend.app.features.cv_confirmation.manual_service import (
    ManualCVValidationError,
    build_cv_data_from_manual_input,
)
from backend.app.features.cv_parsing.schemas import SourceDocument
from backend.app.features.cv_parsing.service import (
    extract_text_from_pdf_bytes,
    parse_cv_to_pydantic,
)
from backend.app.features.profile_pipeline.schemas import ProfilePipelineResponse
from backend.app.features.profile_pipeline.service import run_profile_pipeline

router = APIRouter(prefix="/api/v1/profile-pipeline", tags=["Profile Pipeline"])
logger = logging.getLogger("CareerCompass.ProfilePipeline.Router")


@router.post("/parse-cv", response_model=ProfilePipelineResponse)
async def upload_parse_and_prepare_profile(
    file: UploadFile = File(...),
) -> ProfilePipelineResponse:
    """Upload a PDF, parse the CV, privacy-strip it, and build embedding profile data."""
    if not file.filename.endswith(".pdf") and file.content_type != "application/pdf":
        logger.warning("Rejected unsupported file format: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        file_bytes = await file.read()
        raw_text = extract_text_from_pdf_bytes(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text:
        raise HTTPException(status_code=400, detail="The PDF does not contain readable text.")

    try:
        parsed = await parse_cv_to_pydantic(raw_text)
        parsed.source = SourceDocument(filename=file.filename, extracted_text=raw_text)
        return await run_profile_pipeline(parsed, artifact_name=file.filename)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/manual-cv", response_model=ProfilePipelineResponse)
async def create_manual_profile_pipeline(request: ManualCVInput) -> ProfilePipelineResponse:
    """Build CVData from manual input, privacy-strip it, and build embedding profile data."""
    try:
        cv_data = build_cv_data_from_manual_input(request)
        return await run_profile_pipeline(cv_data, artifact_name="manual_entry")
    except ManualCVValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
