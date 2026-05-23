import logging

from backend.app.core.config import (
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    get_async_openai_client,
)
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.schemas import (
    DraftEducation,
    DraftExperience,
    DraftTechnicalSkill,
    PrivacyStrippedProfileDraft,
    StarterIdentityGeneration,
    StarterProfileResponse,
)

logger = logging.getLogger("CareerCompass.PromptEngineering.Service")


def _is_section_available(confirmed_profile: ConfirmedCVData, section_id: str) -> bool:
    metadata = confirmed_profile.confirmation_metadata
    if section_id in metadata.skipped_sections:
        return False
    if metadata.confirmed_sections and section_id not in metadata.confirmed_sections:
        return False
    return True


def _fallback_current_role(
    cv_data: CVData,
    include_personal_info: bool,
    include_experience: bool,
) -> str | None:
    if include_personal_info and cv_data.personal_info.current_role:
        return cv_data.personal_info.current_role

    if include_experience:
        for experience in cv_data.experience:
            if experience.role:
                return experience.role

    return None


def build_privacy_stripped_profile_draft(
    confirmed_profile: ConfirmedCVData,
) -> PrivacyStrippedProfileDraft:
    """Project confirmed CV JSON into only the fields needed for prompt engineering.

    Personal identifiers, source text, organization names, institutions, contacts,
    links, and locations are intentionally excluded here.
    """
    cv_data = confirmed_profile.confirmed_cv_data
    include_personal_info = _is_section_available(confirmed_profile, "personal_info")
    include_profile_summary = _is_section_available(confirmed_profile, "profile_summary")
    include_experience = _is_section_available(confirmed_profile, "experience")
    include_education = _is_section_available(confirmed_profile, "education")
    include_technical_skills = _is_section_available(confirmed_profile, "technical_skills")
    include_soft_skills = _is_section_available(confirmed_profile, "soft_skills")
    include_interests = _is_section_available(confirmed_profile, "interests")

    current_role = _fallback_current_role(
        cv_data,
        include_personal_info=include_personal_info,
        include_experience=include_experience,
    )

    return PrivacyStrippedProfileDraft(
        current_role=current_role,
        current_seniority_level=(
            cv_data.profile_summary.current_seniority_level if include_profile_summary else None
        ),
        years_of_experience=(
            cv_data.profile_summary.years_of_experience if include_profile_summary else None
        ),
        summary=cv_data.profile_summary.summary if include_profile_summary else None,
        experience=[
            DraftExperience(
                role=experience.role,
                industry=experience.industry,
                duration_months=experience.duration_months,
                core_responsibilities=experience.core_responsibilities,
                contextual_skills=experience.contextual_skills,
            )
            for experience in cv_data.experience
        ]
        if include_experience
        else [],
        education=[
            DraftEducation(
                degree_type=education.degree_type,
                field_of_study=education.field_of_study,
            )
            for education in cv_data.education
        ]
        if include_education
        else [],
        technical_skills=[
            DraftTechnicalSkill(
                name=skill.name,
                proficiency_indication=skill.proficiency_indication,
            )
            for skill in cv_data.skills_extracted.technical_skills
        ]
        if include_technical_skills
        else [],
        soft_skills=cv_data.skills_extracted.soft_skills if include_soft_skills else [],
        interests=cv_data.interests if include_interests else [],
    )


async def generate_starter_profile(
    confirmed_profile: ConfirmedCVData,
) -> StarterProfileResponse:
    draft = build_privacy_stripped_profile_draft(confirmed_profile)
    client = get_async_openai_client()

    system_prompt = (
        "You are a career path prompt-engineering assistant. "
        "Use only the privacy-stripped profile draft provided by the backend. "
        "Do not infer personal identifiers, employer names, locations, age, "
        "gender, or contact details. "
        "Generate a first-person starter identity that is polished but still editable by the user. "
        "The identity should be 2 or 3 concise sentences and should describe current role, experience, "
        "skills, working style, and the kind of career direction the profile suggests. "
        "Also generate 1 or 2 high-level follow-up questions with short option labels. "
        "Questions should help clarify broad career direction, not ask for sensitive personal data."
    )

    try:
        logger.info("Generating starter identity from privacy-stripped profile draft...")
        response = await client.beta.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": draft.model_dump_json()},
            ],
            response_format=StarterIdentityGeneration,
            temperature=OPENAI_TEMPERATURE,
        )
        generated = response.choices[0].message.parsed
        logger.info("Starter identity generated successfully.")
        return StarterProfileResponse(
            privacy_stripped_profile_draft=draft,
            starter_identity=generated.starter_identity,
            suggested_questions=generated.suggested_questions,
        )
    except Exception as exc:
        logger.error("Starter profile generation error: %s", exc)
        raise RuntimeError("Error while generating the starter profile.") from exc
