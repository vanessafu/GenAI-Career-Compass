import logging

from backend.app.core import openai_client
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.prompt_engineering.profile_projector import build_privacy_stripped_profile_draft
from backend.app.features.prompt_engineering.schemas import (
    StarterIdentityGeneration,
    StarterProfileResponse,
)

logger = logging.getLogger("CareerCompass.PromptEngineering.IdentityGenerationService")


async def generate_starter_profile(
    confirmed_profile: ConfirmedCVData,
) -> StarterProfileResponse:
    draft = build_privacy_stripped_profile_draft(confirmed_profile)

    system_prompt = """
You are an experienced tech recruiter specializing in IT and data careers.

Input:
Use only the structured, privacy-stripped resume JSON provided by the backend.

Task:
1. Generate a 2-3 sentence Career Identity Statement.
2. Generate 1-2 follow-up questions:
   - one capability-focused question
   - one career-orientation-focused question

Career Identity Statement:
- Write in concise recruiter-style language suitable for ATS, LinkedIn, or recruiter notes.
- Focus on current career identity, realistic seniority, demonstrated strengths, stakeholder or business exposure, and likely career direction.
- Prioritize evidence-backed positioning over aspirational language.
- Do not exaggerate technical depth, ownership, seniority, or impact.
- Avoid generic buzzwords or personality traits.

Follow-up Questions:
- Ask only about unclear or missing career signals.
- Capability questions should clarify technical depth, work complexity, or analytical focus.
- Orientation questions should clarify preferred work style, problem domain, or career direction.
- Avoid generic preference questions such as desired job title or preferred industry.
- Each question should include 3-5 concise option labels.
""".strip()

    try:
        logger.info("Generating starter identity from privacy-stripped profile draft...")
        generated = await openai_client.parse_structured(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": draft.model_dump_json()},
            ],
            response_format=StarterIdentityGeneration,
        )
        if generated is None:
            raise RuntimeError("LLM returned no parsed response for starter identity.")
        logger.info("Starter identity generated successfully.")
        return StarterProfileResponse(
            privacy_stripped_profile_draft=draft,
            starter_identity=generated.starter_identity,
            suggested_questions=generated.suggested_questions,
        )
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("Starter profile generation error: %s", exc)
        raise RuntimeError("Error while generating the starter profile.") from exc
