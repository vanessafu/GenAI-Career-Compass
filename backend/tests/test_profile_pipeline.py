import asyncio

from backend.app.features.cv_parsing.schemas import (
    Certification,
    CVData,
    Education,
    Experience,
    PersonalInfo,
    ProfileSummary,
    Project,
    SkillsExtracted,
    SourceDocument,
    TechnicalSkill,
    Thesis,
    UnmappedInformation,
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


def test_profile_pipeline_uses_privacy_stripped_data_for_identity(monkeypatch):
    captured = {}

    async def capture_identity_generation(cv_data):
        captured["cv_data"] = cv_data
        return service.CareerIdentitySummary(
            label="Backend Developer",
            summary="Builds APIs without personal identifiers.",
        )

    monkeypatch.setattr(service, "generate_career_identity", capture_identity_generation)
    monkeypatch.setattr(service, "save_cv_debug_artifact", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "save_pipeline_artifact", lambda *args, **kwargs: None)

    cv_data = CVData(
        source=SourceDocument(filename="jane.pdf", extracted_text="Jane Doe jane@example.com"),
        personal_info=PersonalInfo(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="+49 123",
            location="Berlin",
            current_role="Backend Developer",
            links=["https://example.com/jane"],
        ),
        profile_summary=ProfileSummary(summary="Builds APIs and data services."),
        experience=[
            Experience(
                role="Backend Engineer",
                organization="Acme GmbH",
                industry="Fintech",
                location="Berlin",
                core_responsibilities=["Built APIs"],
                contextual_skills=["Python"],
            ),
        ],
        education=[
            Education(
                degree_type="MSc",
                field_of_study="Computer Science",
                institution="TU Berlin",
                grade="1.3",
            ),
        ],
        projects=[
            Project(
                title="API Migration",
                organization="Acme GmbH",
                role="Lead Developer",
                technologies=["Python"],
                links=["https://example.com/project"],
            ),
        ],
        certifications=[
            Certification(
                name="AWS Certified Developer",
                issuing_organization="Amazon",
                credential_id="ABC-123",
                credential_url="https://example.com/cert",
            ),
        ],
        thesis=[
            Thesis(
                title="Distributed APIs",
                institution="TU Berlin",
                supervisor="Prof. Smith",
                grade="1.0",
            ),
        ],
        skills_extracted=SkillsExtracted(
            technical_skills=[TechnicalSkill(name="Python")],
        ),
        unmapped_information=[
            UnmappedInformation(label="email", value="jane@example.com"),
            UnmappedInformation(label="award", value="Best API Migration"),
        ],
    )

    response = asyncio.run(service.run_profile_pipeline(cv_data, artifact_name="test_profile"))

    stripped = captured["cv_data"]
    assert stripped == response.privacy_stripped_cv_data
    assert stripped.source is None
    assert stripped.personal_info.full_name is None
    assert stripped.personal_info.email is None
    assert stripped.personal_info.phone is None
    assert stripped.personal_info.location is None
    assert stripped.personal_info.links == []
    assert stripped.personal_info.current_role == "Backend Developer"
    assert stripped.experience[0].organization is None
    assert stripped.experience[0].location is None
    assert stripped.experience[0].role == "Backend Engineer"
    assert stripped.education[0].institution is None
    assert stripped.education[0].grade is None
    assert stripped.education[0].field_of_study == "Computer Science"
    assert stripped.projects[0].organization is None
    assert stripped.projects[0].links == []
    assert stripped.projects[0].title == "API Migration"
    assert stripped.certifications[0].issuing_organization is None
    assert stripped.certifications[0].credential_id is None
    assert stripped.certifications[0].name == "AWS Certified Developer"
    assert stripped.thesis[0].institution is None
    assert stripped.thesis[0].supervisor is None
    assert [item.value for item in stripped.unmapped_information] == ["Best API Migration"]
