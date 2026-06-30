"""Map a frontend manual-entry payload onto the full CVData schema."""

from backend.app.features.cv_confirmation.manual_schemas import ManualCVInput
from backend.app.features.cv_parsing.schemas import (
    Certification,
    CVData,
    Education,
    Experience,
    Language,
    Metadata,
    PersonalInfo,
    ProfileSummary,
    Project,
    SkillsExtracted,
    SourceDocument,
    TechnicalSkill,
)

MAX_LIST_ITEMS = 50


class ManualCVValidationError(ValueError):
    """Raised when a manual profile does not carry the minimum required signal."""


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _dedupe_strings(values: list[str]) -> list[str]:
    """Trim, drop blanks, and dedupe case-insensitively while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        trimmed = value.strip()
        if not trimmed:
            continue
        key = trimmed.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(trimmed)
    return result[:MAX_LIST_ITEMS]


def _dedupe_languages(values: list[Language]) -> list[Language]:
    seen: set[str] = set()
    result: list[Language] = []
    for lang in values:
        name = lang.language.strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(Language(language=name, level=_clean(lang.level)))
    return result[:MAX_LIST_ITEMS]


def build_cv_data_from_manual_input(request: ManualCVInput) -> CVData:
    """Convert a ManualCVInput DTO into a validated CVData object.

    Raises ManualCVValidationError when required manual profile signal is missing
    (mirrors the frontend minimum guard).
    """
    technical_skill_names = _dedupe_strings(request.technical_skills)
    current_role = _clean(request.current_role)
    seniority_level = _clean(request.seniority_level)
    interests = _dedupe_strings(request.interests)

    if not current_role:
        raise ManualCVValidationError("Provide your current role.")
    if not technical_skill_names:
        raise ManualCVValidationError("Provide at least one technical skill.")
    if not interests:
        raise ManualCVValidationError("Provide at least one interest.")

    education = [
        Education(
            entry_type="degree",
            degree_type=_clean(item.degree_type),
            institution=_clean(item.institution),
            field_of_study=_clean(item.field_of_study),
            start_date=_clean(item.start_date),
            end_date=_clean(item.end_date),
        )
        for item in request.education[:MAX_LIST_ITEMS]
        if _clean(item.degree_type)
    ]

    experience = [
        Experience(
            role=_clean(item.role),
            organization=_clean(item.organization),
            start_date=_clean(item.start_date),
            end_date=_clean(item.end_date),
        )
        for item in request.experience[:MAX_LIST_ITEMS]
        if _clean(item.role)
    ]

    projects = [
        Project(
            title=_clean(item.title),
            description=_clean(item.description),
            technologies=_dedupe_strings(item.technologies),
            start_date=_clean(item.start_date),
            end_date=_clean(item.end_date),
        )
        for item in request.projects[:MAX_LIST_ITEMS]
        if _clean(item.title)
    ]

    certifications = [
        Certification(
            name=_clean(item.name),
            issuing_organization=_clean(item.issuing_organization),
            issue_date=_clean(item.issue_date),
        )
        for item in request.certifications[:MAX_LIST_ITEMS]
        if _clean(item.name)
    ]

    skills_extracted = SkillsExtracted(
        technical_skills=[TechnicalSkill(name=name) for name in technical_skill_names],
        soft_skills=_dedupe_strings(request.soft_skills),
        languages=_dedupe_languages(request.languages),
    )

    return CVData(
        source=SourceDocument(filename="manual_entry"),
        metadata=Metadata(parsing_confidence=0.0),
        personal_info=PersonalInfo(current_role=current_role),
        profile_summary=ProfileSummary(
            summary=_clean(request.summary),
            current_seniority_level=seniority_level,
            years_of_experience=request.years_of_experience,
        ),
        experience=experience,
        education=education,
        projects=projects,
        certifications=certifications,
        skills_extracted=skills_extracted,
        interests=interests,
        unmapped_information=[],
    )
