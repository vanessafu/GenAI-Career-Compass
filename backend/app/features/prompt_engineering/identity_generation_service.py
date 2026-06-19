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
Write a single career_identity_statement of 2-3 sentences in concise,
recruiter-style language suitable for ATS notes or a LinkedIn headline.

Rules:
- Focus on current career identity, realistic seniority, demonstrated strengths,
  and the most likely career direction.
- Base every claim strictly on evidence present in the input data.
- Do not invent information that is not in the input.
- Do not exaggerate technical depth, ownership, seniority, or impact.
- Avoid generic buzzwords and personality traits.
- Output only the career identity statement, nothing else.
""".strip()


async def generate_career_identity(cv_data: CVData) -> str:
    """Generate a career identity statement from privacy-stripped CV data."""
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
        return generated.career_identity_statement
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Career identity generation error: %s", exc)
        raise RuntimeError("Error while generating the career identity.") from exc
