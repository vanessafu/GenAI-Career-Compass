from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.schemas import (
    DraftCareerSignal,
    DraftEducation,
    DraftExperience,
    DraftLanguageSkill,
    DraftProject,
    DraftTechnicalSkill,
    PrivacyStrippedProfileDraft,
)


def is_section_available(confirmed_profile: ConfirmedCVData, section_id: str) -> bool:
    metadata = confirmed_profile.confirmation_metadata
    if section_id in metadata.skipped_sections:
        return False
    if metadata.confirmed_sections and section_id not in metadata.confirmed_sections:
        return False
    return True


def is_section_available_or_untracked(
    confirmed_profile: ConfirmedCVData,
    section_id: str,
) -> bool:
    """Allow backward-compatible use of sections not tracked by older confirmations."""
    metadata = confirmed_profile.confirmation_metadata
    return section_id not in metadata.skipped_sections


def fallback_current_role(
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


def _has_project_signal(title: str | None, description: str | None, technologies: list[str]) -> bool:
    return bool(title or description or technologies)


def _has_education_signal(degree_type: str | None, field_of_study: str | None) -> bool:
    return bool(degree_type or field_of_study)


def _has_experience_signal(
    role: str | None,
    industry: str | None,
    duration_months: int | None,
    core_responsibilities: list[str],
    contextual_skills: list[str],
) -> bool:
    return bool(
        role
        or industry
        or duration_months is not None
        or core_responsibilities
        or contextual_skills
    )


def build_privacy_stripped_profile_draft(
    confirmed_profile: ConfirmedCVData,
) -> PrivacyStrippedProfileDraft:
    """Project confirmed CV JSON into only fields needed by prompt engineering.

    Personal identifiers, source text, organization names, institutions, contacts,
    links, and locations are intentionally excluded here.
    """
    cv_data = confirmed_profile.confirmed_cv_data
    include_personal_info = is_section_available(confirmed_profile, "personal_info")
    include_profile_summary = is_section_available(confirmed_profile, "profile_summary")
    include_experience = is_section_available(confirmed_profile, "experience")
    include_education = is_section_available(confirmed_profile, "education")
    include_projects = is_section_available_or_untracked(confirmed_profile, "projects")
    include_technical_skills = is_section_available(confirmed_profile, "technical_skills")
    include_soft_skills = is_section_available(confirmed_profile, "soft_skills")
    include_languages = is_section_available(confirmed_profile, "languages")
    include_unmapped_information = is_section_available(
        confirmed_profile, "unmapped_information"
    )
    include_interests = is_section_available(confirmed_profile, "interests")

    current_role = fallback_current_role(
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
            if _has_experience_signal(
                role=experience.role,
                industry=experience.industry,
                duration_months=experience.duration_months,
                core_responsibilities=experience.core_responsibilities,
                contextual_skills=experience.contextual_skills,
            )
        ]
        if include_experience
        else [],
        education=[
            DraftEducation(
                degree_type=education.degree_type,
                field_of_study=education.field_of_study,
            )
            for education in cv_data.education
            if _has_education_signal(
                degree_type=education.degree_type,
                field_of_study=education.field_of_study,
            )
        ]
        if include_education
        else [],
        projects=[
            DraftProject(
                title=project.title,
                description=project.description,
                technologies=project.technologies,
            )
            for project in cv_data.projects
            if _has_project_signal(
                title=project.title,
                description=project.description,
                technologies=project.technologies,
            )
        ]
        if include_projects
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
