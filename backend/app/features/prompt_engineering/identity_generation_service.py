import logging

from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.schemas import CareerIdentityGeneration

logger = logging.getLogger("CareerCompass.PromptEngineering.IdentityGenerationService")

_SYSTEM_PROMPT = """  
You are a senior IT recruiter specializing in technical career assessment.  

Generate a recruiter-style career identity from privacy-stripped CV data.  

Produce a professional profile, not a resume summary.  

Output  
- label: 2-4 words, Title Case, using the most representative market-recognized role supported by recurring experience.  
- summary: 3-5 concise sentences.  

Build the summary in this order:  
1. Begin with the role identity.  
2. Primary Expertise (max 3 capability domains)  
3. Career Progression (if evidenced)  
4. Business Impact  
5. One realistic next career direction  

Rules  
- Write in an objective, subject-free style.  
- Describe capabilities, not responsibilities.  
- Express expertise as professional domains and capabilities rather than technologies.  
- Choose the most representative professional role supported by recurring experience.  
- Describe progression through increasing technical ownership, scope or specialization.  
- Summarize recurring business value rather than project outcomes.  
- Weight evidence: recent experience > career progression > projects > education > interests.  
- Infer only from evidence; recommend only the next logical role or specialization beyond the current position.  
- Never include organizations, locations, personal information, links or any personal pronouns.  
- Never exaggerate seniority or impact.  
- Optimize for recruiter readability and rapid market positioning.  
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
