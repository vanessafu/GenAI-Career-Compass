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

MAX_PDF_BYTES = 5 * 1024 * 1024
MAX_FILENAME_CHARS = 200


async def _read_pdf(file: UploadFile) -> bytes:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    if len(filename) > MAX_FILENAME_CHARS:
        raise HTTPException(
            status_code=400,
            detail="PDF filenames must be 200 characters or fewer.",
        )

    file_bytes = await file.read(MAX_PDF_BYTES + 1)
    if len(file_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF files must be 5 MB or smaller.")
    if not file_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")
    return file_bytes


@router.post("/parse-cv", response_model=ProfilePipelineResponse)
async def upload_parse_and_prepare_profile(
    file: UploadFile = File(...),
) -> ProfilePipelineResponse:
    """Parse a bounded PDF upload and build privacy-safe matching data."""
    try:
        raw_text = extract_text_from_pdf_bytes(await _read_pdf(file))
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text:
        raise HTTPException(status_code=400, detail="The PDF does not contain readable text.")

    try:
        parsed = await parse_cv_to_pydantic(raw_text)
        parsed.source = SourceDocument(filename=file.filename)
        return await run_profile_pipeline(parsed)
    except Exception as exc:
        logger.exception("CV profile pipeline failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="CV processing is temporarily unavailable.",
        ) from exc


@router.post("/manual-cv", response_model=ProfilePipelineResponse)
async def create_manual_profile_pipeline(request: ManualCVInput) -> ProfilePipelineResponse:
    """Build privacy-safe matching data from bounded manual input."""
    try:
        return await run_profile_pipeline(build_cv_data_from_manual_input(request))
    except ManualCVValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Manual profile pipeline failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Profile processing is temporarily unavailable.",
        ) from exc