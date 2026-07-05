import logging

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.profile_preparation.schemas import CareerIdentityGeneration

logger = logging.getLogger("CareerCompass.PromptEngineering.IdentityGenerationService")

_IDENTITY_GENERATION_PROMPT = """  
Role: Senior technical recruiter.

Task: Generate a recruiter-style market-facing career identity from privacy-stripped CV data.  

Output:  
- label: 2-4 words, Title Case, market-recognized role. 
- summary: 3-5 concise sentences. Do not start with or repeat the label.  

Build the summary in this order:  
1. Primary expertise, max 3 domains.
2. Career progression, if evidenced.
3. Recurring business value.
4. One realistic next direction.

Rules:
- Objective, subject-free style.
- Capabilities, not responsibilities.
- Professional domains over tool lists.
- Evidence weight: recent experience > progression > projects > education > interests.
- Infer only from evidence.
- No organizations, locations, personal information, links, or pronouns.
- Do not exaggerate seniority or impact.
""".strip()


async def generate_career_identity(cv_data: CVData) -> CareerIdentityGeneration:
    """Generate a structured career identity from privacy-stripped CV data."""
    try:
        logger.info("Generating career identity from privacy-stripped CV data...")
        generated = await openai_client.parse_structured(
            messages=[
                {"role": "system", "content": _IDENTITY_GENERATION_PROMPT},
                {"role": "user", "content": cv_data.model_dump_json()},
            ],
            response_format=CareerIdentityGeneration,
            model_purpose="identity",
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
