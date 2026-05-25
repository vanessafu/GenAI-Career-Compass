from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData, UnmappedInformation
from backend.app.features.prompt_engineering.schemas import (
    EmbeddingInputResponse,
    EmbeddingMetadata,
)
from backend.app.features.prompt_engineering.service import (
    _fallback_current_role,
    _is_section_available,
)

CAREER_RELATED_UNMAPPED_KEYWORDS = {
    "achievement",
    "award",
    "career",
    "certification",
    "certificate",
    "course",
    "framework",
    "methodology",
    "project",
    "responsibility",
    "skill",
    "technology",
    "tool",
    "training",
}

PRIVACY_UNMAPPED_KEYWORDS = {
    "address",
    "birth",
    "contact",
    "email",
    "github",
    "linkedin",
    "location",
    "name",
    "phone",
    "portfolio",
    "website",
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _dedupe_preserve_order(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _join_inline(values: list[str | None]) -> str | None:
    cleaned_values = _dedupe_preserve_order(values)
    if not cleaned_values:
        return None
    return "; ".join(cleaned_values)


def _append_section(lines: list[str], title: str, content: list[str]) -> None:
    cleaned_content = [_clean_text(item) for item in content]
    visible_content = [item for item in cleaned_content if item is not None]
    if not visible_content:
        return

    if lines:
        lines.append("")
    lines.append(f"{title}:")
    lines.extend(visible_content)


def _unmapped_search_text(item: UnmappedInformation) -> str:
    parts = [
        item.label,
        item.source_section,
        item.reason_not_mapped,
        item.value,
    ]
    return " ".join(part for part in parts if part).casefold()


def _is_career_related_unmapped(item: UnmappedInformation) -> bool:
    search_text = _unmapped_search_text(item)
    if any(keyword in search_text for keyword in PRIVACY_UNMAPPED_KEYWORDS):
        return False
    return any(keyword in search_text for keyword in CAREER_RELATED_UNMAPPED_KEYWORDS)


def _format_experience(cv_data: CVData) -> list[str]:
    formatted_experience: list[str] = []
    for experience in cv_data.experience:
        parts = [
            f"Role: {experience.role}" if _clean_text(experience.role) else None,
            f"Industry: {experience.industry}" if _clean_text(experience.industry) else None,
            f"Duration months: {experience.duration_months}"
            if experience.duration_months is not None
            else None,
            f"Responsibilities: {_join_inline(experience.core_responsibilities)}"
            if _join_inline(experience.core_responsibilities)
            else None,
            f"Contextual skills: {_join_inline(experience.contextual_skills)}"
            if _join_inline(experience.contextual_skills)
            else None,
        ]
        visible_parts = [part for part in parts if part is not None]
        if visible_parts:
            formatted_experience.append(f"- {' | '.join(visible_parts)}")
    return formatted_experience


def _format_education(cv_data: CVData) -> list[str]:
    formatted_education: list[str] = []
    for education in cv_data.education:
        parts = [
            f"Degree: {education.degree_type}" if _clean_text(education.degree_type) else None,
            f"Field: {education.field_of_study}"
            if _clean_text(education.field_of_study)
            else None,
        ]
        visible_parts = [part for part in parts if part is not None]
        if visible_parts:
            formatted_education.append(f"- {' | '.join(visible_parts)}")
    return formatted_education


def _format_technical_skills(cv_data: CVData) -> list[str]:
    formatted_skills: list[str] = []
    for skill in cv_data.skills_extracted.technical_skills:
        if _clean_text(skill.proficiency_indication):
            formatted_skills.append(f"{skill.name} {skill.proficiency_indication}")
        else:
            formatted_skills.append(skill.name)
    return _dedupe_preserve_order(formatted_skills)


def _format_unmapped_information(cv_data: CVData) -> list[str]:
    formatted_items: list[str] = []
    for item in cv_data.unmapped_information:
        if _is_career_related_unmapped(item):
            formatted_items.append(item.value)
    return _dedupe_preserve_order(formatted_items)


def _build_embedding_metadata(
    cv_data: CVData,
    current_role: str | None,
    include_profile_summary: bool,
    include_experience: bool,
    include_technical_skills: bool,
    include_soft_skills: bool,
    include_interests: bool,
) -> EmbeddingMetadata:
    return EmbeddingMetadata(
        current_role=current_role,
        current_seniority_level=(
            cv_data.profile_summary.current_seniority_level if include_profile_summary else None
        ),
        years_of_experience=(
            cv_data.profile_summary.years_of_experience if include_profile_summary else None
        ),
        technical_skills=[
            skill.name for skill in cv_data.skills_extracted.technical_skills
        ]
        if include_technical_skills
        else [],
        soft_skills=_dedupe_preserve_order(cv_data.skills_extracted.soft_skills)
        if include_soft_skills
        else [],
        interests=_dedupe_preserve_order(cv_data.interests) if include_interests else [],
        industries=_dedupe_preserve_order(
            [experience.industry for experience in cv_data.experience]
        )
        if include_experience
        else [],
    )


def build_embedding_input(confirmed_profile: ConfirmedCVData) -> EmbeddingInputResponse:
    """Build deterministic embedding input text from confirmed, non-sensitive fields."""
    cv_data = confirmed_profile.confirmed_cv_data
    include_personal_info = _is_section_available(confirmed_profile, "personal_info")
    include_profile_summary = _is_section_available(confirmed_profile, "profile_summary")
    include_experience = _is_section_available(confirmed_profile, "experience")
    include_education = _is_section_available(confirmed_profile, "education")
    include_technical_skills = _is_section_available(confirmed_profile, "technical_skills")
    include_soft_skills = _is_section_available(confirmed_profile, "soft_skills")
    include_interests = _is_section_available(confirmed_profile, "interests")
    include_unmapped = _is_section_available(confirmed_profile, "unmapped_information")

    current_role = _fallback_current_role(
        cv_data,
        include_personal_info=include_personal_info,
        include_experience=include_experience,
    )

    lines: list[str] = []
    if _clean_text(current_role):
        lines.append(f"Current role: {current_role}")
    if include_profile_summary and _clean_text(cv_data.profile_summary.current_seniority_level):
        lines.append(f"Seniority: {cv_data.profile_summary.current_seniority_level}")
    if include_profile_summary and cv_data.profile_summary.years_of_experience is not None:
        lines.append(f"Years of experience: {cv_data.profile_summary.years_of_experience}")

    if include_profile_summary and _clean_text(cv_data.profile_summary.summary):
        _append_section(lines, "Profile summary", [cv_data.profile_summary.summary])
    if include_experience:
        _append_section(lines, "Experience", _format_experience(cv_data))
    if include_education:
        _append_section(lines, "Education", _format_education(cv_data))
    if include_technical_skills:
        _append_section(lines, "Technical skills", _format_technical_skills(cv_data))
    if include_soft_skills:
        _append_section(
            lines,
            "Soft skills",
            _dedupe_preserve_order(cv_data.skills_extracted.soft_skills),
        )
    if include_interests:
        _append_section(lines, "Interests", _dedupe_preserve_order(cv_data.interests))
    if include_unmapped:
        _append_section(
            lines,
            "Additional career-relevant information",
            _format_unmapped_information(cv_data),
        )

    return EmbeddingInputResponse(
        embedding_input_text="\n".join(lines).strip(),
        embedding_metadata=_build_embedding_metadata(
            cv_data=cv_data,
            current_role=current_role,
            include_profile_summary=include_profile_summary,
            include_experience=include_experience,
            include_technical_skills=include_technical_skills,
            include_soft_skills=include_soft_skills,
            include_interests=include_interests,
        ),
    )
