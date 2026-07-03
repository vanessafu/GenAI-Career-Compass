from typing import Any

from backend.app.core.pipeline_debug import derive_profile_stem, save_pipeline_artifact
from backend.app.features.cv_confirmation.schemas import (
    ConfirmationMetadata,
    ConfirmedCVData,
)
from backend.app.features.cv_parsing.debug_output import save_cv_debug_artifact
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.prompt_engineering.identity_generation_service import (
    generate_career_identity,
)
from backend.app.features.prompt_engineering.cv_privacy_service import privacy_strip_cv_data
from backend.app.features.prompt_engineering.schemas import (
    CareerIdentitySummary,
    EmbeddingProfile,
)
from backend.app.features.profile_pipeline.schemas import ProfilePipelineResponse


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
        key = skill.strip().casefold()
        if key and key not in seen:
            seen.add(key)
            skills.append(skill.strip())
    return skills


def build_fallback_career_identity(cv_data: CVData) -> CareerIdentitySummary:
    role = (
        cv_data.personal_info.current_role
        or next((experience.role for experience in cv_data.experience if experience.role), None)
        or "Career Explorer"
    )
    summary = cv_data.profile_summary.summary
    if not summary:
        skills = _skill_keywords(cv_data)[:4]
        interests = [item for item in cv_data.interests if item.strip()][:3]
        signals = [*skills, *interests]
        if signals:
            summary = "Profile combines career signals across " + ", ".join(signals) + "."
        else:
            summary = "Profile contains enough career signal to begin role matching."
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
        interests=list(dict.fromkeys(item.strip() for item in privacy_stripped_cv_data.interests if item.strip())),
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
    )


async def run_profile_pipeline(cv_data: CVData, *, artifact_name: str | None = None) -> ProfilePipelineResponse:
    save_cv_debug_artifact(cv_data, name=artifact_name)
    profile_stem = derive_profile_stem(cv_data, fallback=artifact_name or "profile")

    privacy_stripped_cv_data = privacy_strip_cv_data(cv_data)
    save_pipeline_artifact(
        "02_privacy_stripped",
        privacy_stripped_cv_data,
        profile_stem=profile_stem,
    )

    try:
        career_identity_summary = await generate_career_identity(privacy_stripped_cv_data)
    except RuntimeError as exc:
        career_identity_summary = build_fallback_career_identity(privacy_stripped_cv_data)
        save_pipeline_artifact(
            "03_identity_summary_error",
            {"error": str(exc), "fallback_used": True},
            profile_stem=profile_stem,
        )
    save_pipeline_artifact(
        "03_identity_summary",
        {"career_identity_summary": career_identity_summary.model_dump(mode="json")},
        profile_stem=profile_stem,
    )

    embedding_profile = build_embedding_profile(
        privacy_stripped_cv_data,
        career_identity_summary,
    )
    save_pipeline_artifact(
        "04_embedding_profile",
        embedding_profile,
        profile_stem=profile_stem,
    )

    save_pipeline_artifact(
        "05_confirmed_with_identity",
        ConfirmedCVData(
            confirmed_cv_data=privacy_stripped_cv_data,
            confirmation_metadata=ConfirmationMetadata(
                confirmed_sections=[
                    "personal_info",
                    "profile_summary",
                    "experience",
                    "education",
                    "projects",
                    "certifications",
                    "thesis",
                    "skills_extracted",
                    "interests",
                    "unmapped_information",
                ],
            ),
            career_identity_statement=(
                f"{career_identity_summary.label}: {career_identity_summary.summary}"
            ),
            career_identity_summary=career_identity_summary,
        ),
        profile_stem=profile_stem,
    )

    return ProfilePipelineResponse(
        cv_data=cv_data,
        privacy_stripped_cv_data=privacy_stripped_cv_data,
        embedding_profile=embedding_profile,
    )
