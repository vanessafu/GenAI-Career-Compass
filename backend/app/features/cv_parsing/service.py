import logging

import fitz

from backend.app.core.config import (
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    get_async_openai_client,
)
from backend.app.features.cv_parsing.schemas import CVData

logger = logging.getLogger("CareerCompass.CVParsing.Service")


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from a PDF byte stream in memory."""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            pages_text = [page.get_text() for page in doc]
            return "\n".join(pages_text).strip()
    except Exception as exc:
        logger.error("PDF extraction error: %s", exc)
        raise ValueError("The PDF document could not be read.") from exc


async def parse_cv_to_pydantic(raw_text: str) -> CVData:
    """Send CV text to the LLM and validate the result against the schema."""
    client = get_async_openai_client()

    system_prompt = (
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

    try:
        logger.info("Sending request to OpenAI API (model=%s)...", OPENAI_MODEL)
        response = await client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": raw_text},
            ],
            response_format=CVData,
            temperature=OPENAI_TEMPERATURE,
        )
        logger.info("Response received and validated successfully.")
        return response.choices[0].message.parsed
    except Exception as exc:
        logger.exception("LLM communication error (%s): %s", type(exc).__name__, exc)
        raise RuntimeError(f"Error while processing with the LLM: {type(exc).__name__}: {exc}") from exc
