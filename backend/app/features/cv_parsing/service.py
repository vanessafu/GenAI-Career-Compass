import logging

import fitz
from pydantic import BaseModel, Field

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData

logger = logging.getLogger("CareerCompass.CVParsing.Service")

_SYSTEM_PROMPT = (
    "You are a precise assistant for parsing resumes. "
    "Extract the data from the text and fill in the provided schema. "
    "IMPORTANT RULES: "
    "1. COMPLETENESS IS CRITICAL: Extract EVERY SINGLE entry from each section. "
    "Do not skip, merge, or summarise any work experience, education entry, project, certification, or thesis. "
    "If there are four work experience entries in the CV, the experience list must contain four items. "
    "2. Do not invent or guess any information under any circumstances. "
    "3. If a specific piece of information is not explicitly and clearly present in the resume text, "
    "leave the corresponding field empty (set the value to null or return an empty list). "
    "4. Do not infer an industry from company names if it is not stated in the text. "
    "5. Extract personal information such as name, email, phone, location, current role, and links "
    "only when explicitly present. "
    "6. For education entries, use entry_type to classify each entry: "
    "'degree' for university degrees, 'semester_abroad' for exchange semesters and study abroad programmes, "
    "'high_school' for Abitur/A-levels/secondary school, 'certification' for professional certificates, "
    "'other' for anything else (e.g. work & travel). "
    "7. Extract projects, certifications, and thesis or final dissertation work into their dedicated "
    "schema sections when they are explicitly present. Do not merge them into work experience unless "
    "the resume clearly presents them as employment. "
    "8. For date fields (start_date, end_date, issue_date, expiration_date) use the format found in the text "
    "(e.g. '01/2023' or '2023'). "
    "9. If the resume contains relevant information that does not fit any schema field, preserve it "
    "in unmapped_information instead of discarding it."
)

_INTEREST_GENERATION_PROMPT = (
    "Infer 3 to 5 concise career interests from the CV text. "
    "Use only evidence in the text, avoid personal identifiers, and return short noun phrases. "
    "Do not include duplicates or full sentences."
)


class _GeneratedInterests(BaseModel):
    interests: list[str] = Field(default_factory=list)


def _clean_interests(values: list[str]) -> list[str]:
    seen: set[str] = set()
    interests: list[str] = []
    for value in values:
        cleaned = value.strip()
        key = cleaned.casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        interests.append(cleaned)
    return interests[:5]


async def _fill_blank_interests(cv_data: CVData, raw_text: str, *, model: str | None = None) -> CVData:
    if any(item.strip() for item in cv_data.interests):
        cv_data.interests = _clean_interests(cv_data.interests)
        return cv_data

    try:
        generated = await openai_client.parse_structured(
            messages=[
                {"role": "system", "content": _INTEREST_GENERATION_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format=_GeneratedInterests,
            model_purpose="identity",
            model=model,
        )
    except Exception as exc:
        logger.warning("Interest generation failed; keeping blank interests: %s", exc)
        return cv_data

    if generated is not None:
        cv_data.interests = _clean_interests(generated.interests)
    return cv_data


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from a PDF byte stream in memory."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pages_text = [page.get_text() for page in doc]
            return "\n".join(pages_text).strip()
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        raise ValueError("The PDF document could not be read.") from exc


async def parse_cv_to_pydantic(raw_text: str, *, model: str | None = None) -> CVData:
    """Send CV text to the LLM and validate the result against the CVData schema."""
    logger.info("Sending CV text to LLM for structured parsing...")
    try:
        result = await openai_client.parse_structured(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format=CVData,
            model_purpose="cv_parsing",
            model=model,
        )
        if result is None:
            raise RuntimeError("CV parser returned no structured output")
        logger.info("CV parsed successfully.")
        return await _fill_blank_interests(result, raw_text, model=model)
    except Exception as exc:
        logger.exception("LLM communication error (%s): %s", type(exc).__name__, exc)
        raise RuntimeError(f"Error while processing with the LLM: {type(exc).__name__}: {exc}") from exc
