import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.features.cv_parsing.debug_output import save_parsed_cv
from backend.app.features.cv_parsing.schemas import CVData, SourceDocument
from backend.app.features.cv_parsing.service import (
    extract_text_from_pdf_bytes,
    parse_cv_to_pydantic,
)

router = APIRouter(prefix="/api/v1", tags=["CV Parsing"])
logger = logging.getLogger("CareerCompass.CVParsing.Router")


@router.post("/parse-cv", response_model=CVData)
async def upload_and_parse_cv(file: UploadFile = File(...)) -> CVData:
    """Upload a PDF CV and parse it into structured profile data."""
    if not file.filename.endswith(".pdf") and file.content_type != "application/pdf":
        logger.warning("Rejected unsupported file format: %s", file.filename)
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    try:
        file_bytes = await file.read()
        raw_text = extract_text_from_pdf_bytes(file_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text:
        raise HTTPException(
            status_code=400,
            detail="The PDF does not contain readable text.",
        )

    try:
        parsed = await parse_cv_to_pydantic(raw_text)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    parsed.source = SourceDocument(filename=file.filename, extracted_text=raw_text)
    save_parsed_cv(parsed, filename=file.filename)
    return parsed
