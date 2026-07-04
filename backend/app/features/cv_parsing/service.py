import logging

import fitz

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData

logger = logging.getLogger("CareerCompass.CVParsing.Service")

# One LLM step for CV parsing plus career signal extraction:
# structured CV data, inferred interests, and inferred soft skills.
_CV_PARSING_AND_EXTRACTING_PROMPT = """
Role
Resume parser and career signal extractor.

Task
Extract structured CV data into the provided schema.
Also normalize interests and infer soft skills when supported by CV evidence.

Priority

P1 Completeness
Extract every explicitly stated entry.
Never skip, merge, summarize, or deduplicate.

P2 Faithfulness
Use only CV evidence.
Never invent, guess, rewrite, or complete missing facts.
Do not infer industry, seniority, or impact unless clearly supported.

P3 Missing Values
Unsupported scalar → null.
Unsupported list → [].

P4 Structure
Keep each item in its corresponding schema section.
Do not move entries across sections.

P5 Formatting
Preserve original wording unless a field-specific rule says to normalize.
Keep dates exactly as written.

P6 Education
Use `entry_type`: degree, semester_abroad, high_school, certification, other.
Classify exchange/study abroad as `semester_abroad`; Abitur/A-levels/secondary school as `high_school`; work & travel as `other`.
For degrees, split fields strictly:
`degree_type` = level only; `field_of_study` = field only; `institution` = school only.

P7 Personal Data
Extract personal data only when explicitly stated.
Do not use personal identifiers in generated interests or soft skills.

P8 Interests
Return 3–5 short noun phrases in `interests`; no duplicates/sentences.
Priority: target role/career goal > recurring CV evidence > listed generic interests.

P9 Soft Skills
Return 3–5 soft skills in `skills_extracted.soft_skills`.
Infer only from repeated responsibilities, achievements, leadership, collaboration, communication, ownership, problem-solving, or stakeholder evidence.
Use concise noun phrases.
Exclude technical skills, tools, languages, job titles, and unsupported personality traits.

P10 Fallback
Store relevant unmapped information in `unmapped_information`.

Schema Rules
Use schema enums exactly.
""".strip()


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
                {"role": "system", "content": _CV_PARSING_AND_EXTRACTING_PROMPT},
                {"role": "user", "content": raw_text},
            ],
            response_format=CVData,
            model_purpose="cv_parsing",
            model=model,
        )
        if result is None:
            raise RuntimeError("CV parser returned no structured output")
        logger.info("CV parsed successfully.")
        return result
    except Exception as exc:
        logger.exception("LLM communication error (%s): %s", type(exc).__name__, exc)
        raise RuntimeError(f"Error while processing with the LLM: {type(exc).__name__}: {exc}") from exc
