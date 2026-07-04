import logging

import fitz

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData

logger = logging.getLogger("CareerCompass.CVParsing.Service")

# One LLM step for CV parsing plus career signal extraction: structured CV
# data, inferred interests, inferred soft skills (each with a confidence
# score), inferred technical skills - tools/knowledge implied by the work
# described, not just stated skill combinations, kept separate from stated
# ones - and a potential-direction narrative.
_CV_PARSING_AND_EXTRACTING_PROMPT = """
Role
Resume parser and career signal extractor.

Task
Populate the provided schema from a CV.

The schema contains two types of outputs:

1. Explicit Extraction (facts explicitly stated in the CV)
Populate only:
- personal_info
- profile_summary
- experience
- education
- projects
- certifications
- thesis
- skills_extracted.technical_skills
- skills_extracted.languages

2. Inference (evidence-based reasoning)
Populate only:
- skills_extracted.inferred_skills
- skills_extracted.soft_skills
- interests
- potential_direction

Never place inferred information into explicit extraction fields, and never replace explicit information with inferred content.

Global Rules
1. Completeness is critical. Extract every explicit CV entry exactly once. Never skip, merge, summarize, rewrite, or deduplicate.
2. Use only CV evidence. Never invent, guess, or complete missing information. Infer only in the dedicated inference fields.
3. Unsupported scalar -> null. Unsupported list -> [].
4. Preserve original wording and dates unless normalization is explicitly requested.
5. Keep every entry in its own schema section. Projects, certifications and thesis must remain in their own sections unless the CV explicitly presents them as employment.
6. Do not infer industry, seniority, impact, or career goals.
7. Use schema enums exactly.

Education (only include entries above the high school level)
- entry_type:
  degree | semester_abroad 
- Exchange/study abroad -> semester_abroad
- Work & Travel -> other
- Degree entries:
  degree_type = degree level only
  field_of_study = subject only
  institution = school only

Technical Skills
Populate only with explicitly stated reusable skills:
programming languages, frameworks, libraries, databases, cloud platforms,
developer tools, software, methodologies and well-established technical concepts.

Do not include:
- inferred skills
- project names
- thesis titles
- course names
- responsibilities
- achievements
- company names (e.g. Github,Gitlab,etc.)
- URLs and other contact info

Each skill should be concise (1-4 words).

Interests
Return 3-5 concise noun phrases.
Priority:
1. Explicit interests
2. Target role / career objective
3. Recurring CV evidence
No duplicates or sentences.

Soft Skills
Populate only `skills_extracted.soft_skills`.

Infer workplace soft skills from repeated evidence across experience and projects.

Each item contains:
- name
- confidence (0-100)

Confidence reflects both strength and frequency of supporting evidence.
Exclude technical skills, tools, languages, job titles and unsupported personality traits.

Inferred Technical Skills
Populate only `skills_extracted.inferred_skills`.

Infer at most 8 technical skills that are NOT explicitly stated but are strongly supported by the CV through either:
- prerequisite/composition relationships among stated skills or coursework
- responsibilities, technologies or project descriptions that clearly require the inferred skill

Examples:
Python + Statistics + Linear Algebra -> Machine Learning Foundations
Designed REST APIs -> API Design
Managed PostgreSQL schema migrations -> Database Migrations
Built CI/CD pipelines -> CI/CD Tooling

Do not infer from isolated or vague evidence.

Each inferred skill must contain:
- name
- inferred_from
- rationale

Never infer soft skills, seniority, industry or career goals.

Potential Direction
Write 2-3 sentences describing plausible future technical directions suggested by recurring technologies, projects and responsibilities.

Ground every statement in explicit CV evidence.
Do not describe the current role, repeat interests or invent ambitions.
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
