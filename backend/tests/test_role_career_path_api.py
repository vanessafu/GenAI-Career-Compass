import asyncio

from fastapi.testclient import TestClient

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.schemas import (
    CertificationDimension,
    CertificationGap,
    GapReport,
    SkillDimension,
    SkillGap,
)
from backend.app.main import app


def minimal_confirmed_profile():
    return {
        "confirmed_cv_data": {
            "personal_info": {"current_role": "Backend Developer"},
            "profile_summary": {
                "summary": "Builds APIs.",
                "current_seniority_level": "mid",
                "years_of_experience": 4,
            },
            "skills_extracted": {
                "technical_skills": [{"name": "Python"}],
                "soft_skills": [],
                "languages": [],
            },
        },
        "confirmation_metadata": {
            "confirmed_at": "2026-06-26T00:00:00",
            "confirmed_sections": [],
            "skipped_sections": [],
            "edited_fields": [],
        },
    }


def test_career_path_endpoint_returns_report(monkeypatch):
    async def fake_generate_career_path(role_id, confirmed_profile):
        return {
            "role_id": role_id,
            "current_profile_summary": "Backend Developer: Builds APIs.",
            "target_role": "Backend Engineer",
            "readiness_score": 0.75,
            "top_gaps": ["Cloud architecture"],
            "milestones": [
                {
                    "order": 1,
                    "kind": "project",
                    "title": "Build cloud evidence",
                    "timeline": "1 month",
                    "rationale": "Closes the largest visible skill gap.",
                    "skills": ["Cloud architecture"],
                    "projects": ["Deploy an API to a cloud runtime"],
                }
            ],
            "recommended_projects": ["Deploy an API to a cloud runtime"],
            "skills_to_learn": ["Cloud architecture"],
            "certifications": ["AWS Certified Developer - Associate"],
            "estimated_timeline": "3 months",
            "requirement_breakdown": GapReport(
                role_id=role_id,
                job_title="Backend Engineer",
                overall_readiness=0.75,
            ).model_dump(mode="json"),
        }

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "generate_career_path", fake_generate_career_path, raising=False)
    client = TestClient(app)

    response = client.post("/api/v1/roles/42/career-path", json=minimal_confirmed_profile())

    assert response.status_code == 200
    body = response.json()
    assert body["role_id"] == 42
    assert body["target_role"] == "Backend Engineer"
    assert body["milestones"][0]["kind"] == "project"
    assert body["requirement_breakdown"]["job_title"] == "Backend Engineer"


def test_career_path_endpoint_returns_404_for_missing_role(monkeypatch):
    async def fake_generate_career_path(role_id, confirmed_profile):
        raise ValueError(f"role_id {role_id} not found")

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "generate_career_path", fake_generate_career_path, raising=False)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/roles/404/career-path", json=minimal_confirmed_profile())

    assert response.status_code == 404
    assert response.json()["detail"] == "role_id 404 not found"


def test_career_path_endpoint_returns_503_for_service_failure(monkeypatch):
    async def fake_generate_career_path(role_id, confirmed_profile):
        raise RuntimeError("path service unavailable")

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "generate_career_path", fake_generate_career_path, raising=False)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/roles/42/career-path", json=minimal_confirmed_profile())

    assert response.status_code == 503
    assert response.json()["detail"] == "path service unavailable"


def test_career_path_filters_llm_certifications_to_gap_report(monkeypatch):
    from backend.app.features.role_matching import career_path

    async def fake_explain_role_gap(role_id, confirmed_profile, *, with_narrative):
        return GapReport(
            role_id=role_id,
            job_title="Backend Engineer",
            overall_readiness=0.5,
            skills=SkillDimension(
                skill_gaps=[
                    SkillGap(required_skill="Cloud architecture", severity="high"),
                    SkillGap(required_skill="Observability", severity="medium"),
                ],
            ),
            certifications=CertificationDimension(
                missing=[
                    CertificationGap(
                        required_certification="AWS Certified Developer - Associate",
                        normalized_name="aws certified developer associate",
                    )
                ]
            ),
        )

    async def fake_parse_structured(messages, response_format, **kwargs):
        return career_path.CareerPathDraft(
            milestones=[
                career_path.CareerPathMilestone(
                    order=1,
                    title="Build cloud evidence",
                    timeline="1 month",
                    rationale="Targets the largest gap.",
                    skills=["Cloud architecture"],
                    projects=["Deploy an API to a cloud runtime"],
                )
            ],
            recommended_projects=["Deploy an API to a cloud runtime"],
            estimated_timeline="",
            certifications=[
                "AWS Certified Developer - Associate",
                "Made Up Platform Certificate",
            ],
        )

    monkeypatch.setattr(career_path, "explain_role_gap", fake_explain_role_gap)
    monkeypatch.setattr(career_path, "parse_structured", fake_parse_structured)

    report = asyncio.run(
        career_path.generate_career_path(
            42,
            ConfirmedCVData.model_validate(
                {
                    **minimal_confirmed_profile(),
                    "career_identity_statement": "Edited identity: wants backend platform work.",
                }
            ),
        )
    )

    assert report.current_profile_summary == "Edited identity: wants backend platform work."
    assert report.skills_to_learn == ["Cloud architecture", "Observability"]
    assert report.certifications == ["AWS Certified Developer - Associate"]
    assert 3 <= len(report.milestones) <= 5
    assert report.estimated_timeline
    assert report.requirement_breakdown.job_title == "Backend Engineer"


def test_career_path_milestone_kind_defaults_to_skill():
    from backend.app.features.role_matching.schemas import CareerPathMilestone

    milestone = CareerPathMilestone.model_validate(
        {
            "order": 1,
            "title": "Build cloud evidence",
            "timeline": "1 month",
            "rationale": "Targets the largest gap.",
        }
    )

    assert milestone.kind == "skill"


def test_fallback_career_path_uses_meaningful_milestone_kinds():
    from backend.app.features.role_matching import career_path

    draft = career_path._fallback_draft(
        ["Cloud architecture", "AWS Certified Developer - Associate"],
        ["AWS Certified Developer - Associate"],
    )

    assert [milestone.kind for milestone in draft.milestones[:3]] == [
        "skill",
        "certification",
        "project",
    ]
