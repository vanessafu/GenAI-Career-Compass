import logging
from typing import Any

from backend.app.core.validation import MAX_ITEMS
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.profile_preparation.cv_privacy_service import privacy_strip_cv_data
from backend.app.features.profile_preparation.identity_generation_service import (
    generate_career_identity,
)
from backend.app.features.profile_preparation.schemas import (
    CareerIdentitySummary,
    EmbeddingProfile,
)
from backend.app.features.profile_pipeline.schemas import ProfilePipelineResponse

logger = logging.getLogger("CareerCompass.ProfilePipeline.Service")


def _clean_dict(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value not in (None, "", [], {})
    }


def _section_dicts(items: list[Any], *fields: str) -> list[dict[str, Any]]:
    return [
        cleaned
        for item in items
        if (cleaned := _clean_dict({field: getattr(item, field, None) for field in fields}))
    ]


def _skill_keywords(cv_data: CVData) -> list[str]:
    seen: set[str] = set()
    skills: list[str] = []
    for skill in cv_data.skills_extracted.technical_skills:
        key = skill.name.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            skills.append(skill.name.strip())
    for skill in cv_data.skills_extracted.soft_skills:
        key = skill.name.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            skills.append(skill.name.strip())
    return skills[:MAX_ITEMS]


def build_fallback_career_identity(cv_data: CVData) -> CareerIdentitySummary:
    role = (
        cv_data.personal_info.current_role
        or next((experience.role for experience in cv_data.experience if experience.role), None)
        or "Career Explorer"
    )
    summary = cv_data.profile_summary.summary
    if not summary:
        signals = [
            *_skill_keywords(cv_data)[:4],
            *[item for item in cv_data.interests if item.strip()][:3],
        ]
        summary = (
            "Profile combines career signals across " + ", ".join(signals) + "."
            if signals
            else "Profile contains enough career signal to begin role matching."
        )
    return CareerIdentitySummary(label=role, summary=summary)


def build_embedding_profile(
    privacy_stripped_cv_data: CVData,
    career_identity_summary: CareerIdentitySummary,
) -> EmbeddingProfile:
    return EmbeddingProfile(
        career_identity_summary=career_identity_summary,
        education=_section_dicts(
            privacy_stripped_cv_data.education,
            "entry_type",
            "degree_type",
            "field_of_study",
            "start_date",
            "end_date",
            "courses",
        ),
        experience=_section_dicts(
            privacy_stripped_cv_data.experience,
            "role",
            "industry",
            "start_date",
            "end_date",
            "duration_months",
            "core_responsibilities",
            "contextual_skills",
        ),
        skills=_skill_keywords(privacy_stripped_cv_data),
        interests=list(
            dict.fromkeys(
                item.strip()
                for item in privacy_stripped_cv_data.interests
                if item.strip()
            )
        ),
        certifications=_section_dicts(
            privacy_stripped_cv_data.certifications,
            "name",
            "issue_date",
            "expiration_date",
        ),
        projects=_section_dicts(
            privacy_stripped_cv_data.projects,
            "title",
            "description",
            "technologies",
            "outcomes",
            "start_date",
            "end_date",
        ),
        potential_direction=privacy_stripped_cv_data.potential_direction or "",
    )


async def run_profile_pipeline(cv_data: CVData) -> ProfilePipelineResponse:
    privacy_stripped_cv_data = privacy_strip_cv_data(cv_data)
    try:
        career_identity_summary = await generate_career_identity(privacy_stripped_cv_data)
    except RuntimeError as exc:
        logger.warning("Career identity generation failed; using fallback: %s", exc)
        career_identity_summary = build_fallback_career_identity(privacy_stripped_cv_data)

    return ProfilePipelineResponse(
        cv_data=cv_data,
        privacy_stripped_cv_data=privacy_stripped_cv_data,
        embedding_profile=build_embedding_profile(
            privacy_stripped_cv_data,
            career_identity_summary,
        ),
    )