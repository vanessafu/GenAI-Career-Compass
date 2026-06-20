import logging

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.schemas import CareerIdentityGeneration

logger = logging.getLogger("CareerCompass.PromptEngineering.IdentityGenerationService")

_SYSTEM_PROMPT = """
You are an expert tech recruiter specializing in IT and data careers.

Input:
You receive structured, privacy-stripped CV data as JSON. It contains only
career-relevant fields (role, seniority, experience, education, projects,
skills, interests) with personal identifiers already removed.

Task:
Return a structured career identity with:
1. label: a short 2-4 word Title Case career label.
2. summary: 2-3 concise, evidence-backed sentences in recruiter-style language.

Rules:
- The label must be career-oriented and specific to the evidence, e.g.
  "Robust Systems Architect" or "Applied Vision Engineer".
- The summary must focus on current career identity, realistic seniority,
  demonstrated strengths, and the most likely career direction.
- Base every claim strictly on evidence present in the input data.
- Do not invent information that is not in the input.
- Do not exaggerate technical depth, ownership, seniority, or impact.
- Do not include personal identifiers, employer names, organization names,
  locations, email addresses, phone numbers, links, or postal addresses.
- Avoid generic buzzwords and personality traits.
- Output only the requested structured fields.
""".strip()


async def generate_career_identity(cv_data: CVData) -> CareerIdentityGeneration:
    """Generate a structured career identity from privacy-stripped CV data."""
    try:
        logger.info("Generating career identity from privacy-stripped CV data...")
        generated = await openai_client.parse_structured(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": cv_data.model_dump_json()},
            ],
            response_format=CareerIdentityGeneration,
        )
        if generated is None:
            raise RuntimeError("LLM returned no parsed response for the career identity.")
        logger.info("Career identity generated successfully.")
        return generated
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Career identity generation error: %s", exc)
        raise RuntimeError("Error while generating the career identity.") from exc
