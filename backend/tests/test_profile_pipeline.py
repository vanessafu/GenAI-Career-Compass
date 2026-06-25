import asyncio

from backend.app.features.cv_parsing.schemas import (
    CVData,
    Experience,
    PersonalInfo,
    ProfileSummary,
    SkillsExtracted,
    TechnicalSkill,
)
from backend.app.features.profile_pipeline import service


def test_profile_pipeline_falls_back_when_identity_generation_fails(monkeypatch):
    async def fail_identity_generation(_cv_data):
        raise RuntimeError("identity service unavailable")

    monkeypatch.setattr(service, "generate_career_identity", fail_identity_generation)
    monkeypatch.setattr(service, "save_cv_debug_artifact", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "save_pipeline_artifact", lambda *args, **kwargs: None)

    cv_data = CVData(
        personal_info=PersonalInfo(current_role="Backend Developer"),
        profile_summary=ProfileSummary(summary="Builds APIs and data services."),
        experience=[Experience(role="Backend Engineer")],
        skills_extracted=SkillsExtracted(
            technical_skills=[
                TechnicalSkill(name="Python"),
                TechnicalSkill(name="PostgreSQL"),
            ],
        ),
        interests=["Cloud platforms"],
    )

    response = asyncio.run(service.run_profile_pipeline(cv_data, artifact_name="test_profile"))

    assert response.embedding_profile.career_identity_summary.label == "Backend Developer"
    assert "Builds APIs and data services." in response.embedding_profile.career_identity_summary.summary
