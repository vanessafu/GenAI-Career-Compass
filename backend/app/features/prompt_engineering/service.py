import logging

from backend.app.core.config import (
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    get_async_openai_client,
)
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.schemas import (
    DraftCareerSignal,
    DraftEducation,
    DraftExperience,
    DraftLanguageSkill,
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


def _privacy_safe_career_signals(cv_data: CVData) -> list[DraftCareerSignal]:
    """Keep non-identifying CV signals that HR reviewers commonly use for IT screening."""
    useful_terms = (
        "award",
        "certificate",
        "certification",
        "patent",
        "project",
        "publication",
        "thesis",
    )
    excluded_terms = (
        "address",
        "birth",
        "contact",
        "date of birth",
        "email",
        "final grade",
        "gender",
        "grade",
        "nationality",
        "phone",
        "website",
    )
    career_signals: list[DraftCareerSignal] = []

    for item in cv_data.unmapped_information:
        label = item.label or item.source_section or None
        searchable_text = " ".join(
            part.lower()
            for part in (item.label, item.source_section, item.reason_not_mapped)
            if part
        )
        value = item.value.strip()
        value_lower = value.lower()

        if not value:
            continue
        if any(term in searchable_text for term in excluded_terms):
            continue
        if "http://" in value_lower or "https://" in value_lower or "@" in value:
            continue
        if not any(term in searchable_text for term in useful_terms):
            continue

        career_signals.append(DraftCareerSignal(label=label, value=value))

    return career_signals[:5]


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
    include_languages = _is_section_available(confirmed_profile, "languages")
    include_unmapped_information = _is_section_available(
        confirmed_profile, "unmapped_information"
    )
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
        language_skills=[
            DraftLanguageSkill(language=language.language, level=language.level)
            for language in cv_data.skills_extracted.languages
        ]
        if include_languages
        else [],
        career_signals=(
            _privacy_safe_career_signals(cv_data) if include_unmapped_information else []
        ),
        interests=cv_data.interests if include_interests else [],
    )


async def generate_starter_profile(
    confirmed_profile: ConfirmedCVData,
) -> StarterProfileResponse:
    draft = build_privacy_stripped_profile_draft(confirmed_profile)
    client = get_async_openai_client()

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
