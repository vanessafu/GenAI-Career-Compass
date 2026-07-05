import asyncio

from fastapi.testclient import TestClient
import pytest

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.role_matching.schemas import (
    ActionableSkillGap,
    ActionableSkillGapPolish,
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
            "plan_summary": "This plan turns the largest gaps into direct proof for the target role.",
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
    assert body["plan_summary"]
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
            plan_summary=(
                "Focus the roadmap on cloud architecture and observability evidence. "
                "Use the project milestone to make the strongest gap easy to verify."
            ),
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
    assert "cloud architecture" in report.plan_summary.lower()
    assert report.skills_to_learn == ["Cloud architecture", "Observability"]
    assert report.certifications == ["AWS Certified Developer - Associate"]
    assert 3 <= len(report.milestones) <= 5
    assert report.estimated_timeline
    assert report.requirement_breakdown.job_title == "Backend Engineer"


def test_career_path_estimated_timeline_is_the_readiness_tiers_range(monkeypatch):
    from backend.app.features.role_matching import career_path

    async def fake_explain_role_gap(role_id, confirmed_profile, *, with_narrative):
        return GapReport(
            role_id=role_id,
            job_title="Backend Engineer",
            overall_readiness=0.6,
            skills=SkillDimension(
                skill_gaps=[
                    SkillGap(required_skill="Cloud architecture", severity="high"),
                    SkillGap(required_skill="Observability", severity="medium"),
                    SkillGap(required_skill="Release automation", severity="medium"),
                ],
            ),
        )

    async def fake_parse_structured(messages, response_format, **kwargs):
        return career_path.CareerPathDraft(
            plan_summary="Build cloud, observability, and release evidence for the target role.",
            milestones=[
                career_path.CareerPathMilestone(
                    order=1,
                    title="First",
                    timeline="2 months",
                    rationale="",
                    skills=["Cloud architecture"],
                ),
                career_path.CareerPathMilestone(
                    order=2,
                    title="Second",
                    timeline="3 weeks",
                    rationale="",
                    skills=["Observability"],
                ),
                career_path.CareerPathMilestone(
                    order=3,
                    title="Third",
                    timeline="8 weeks",
                    rationale="",
                    skills=["Release automation"],
                ),
            ],
        )

    monkeypatch.setattr(career_path, "explain_role_gap", fake_explain_role_gap)
    monkeypatch.setattr(career_path, "parse_structured", fake_parse_structured)

    report = asyncio.run(
        career_path.generate_career_path(
            42,
            ConfirmedCVData.model_validate(minimal_confirmed_profile()),
        )
    )

    assert [milestone.timeline for milestone in report.milestones] == [
        "2 months",
        "3 weeks",
        "2 months",
    ]
    # estimated_timeline is now the readiness tier's fixed range, not a sum of
    # milestone durations - 0.6 readiness falls in the next_step tier (0.35-0.70).
    assert report.estimated_timeline == "3-5 months"


def test_career_path_applies_llm_top_skill_gap_suggestion_polish(monkeypatch):
    from backend.app.features.role_matching import career_path

    async def fake_explain_role_gap(role_id, confirmed_profile, *, with_narrative):
        return GapReport(
            role_id=role_id,
            job_title="Release Manager",
            overall_readiness=0.48,
            skills=SkillDimension(
                skill_gaps=[
                    SkillGap(
                        required_skill="software development life cycle",
                        display="Software Development Life Cycle (SDLC)",
                        severity="high",
                        suggestion="Rule-based SDLC action.",
                    )
                ],
            ),
            top_actionable_skill_gaps=[
                ActionableSkillGap(
                    skill="software development life cycle",
                    display="Software Development Life Cycle (SDLC)",
                    domain="Software Engineering",
                    priority_label="critical",
                    estimated_effort="substantial",
                    why_it_matters="Rule-based why.",
                    suggested_action="Rule-based action.",
                    proof_to_build="Rule-based proof.",
                    resume_hint="Rule-based resume hint.",
                )
            ],
        )

    async def fake_parse_structured(messages, response_format, **kwargs):
        return career_path.CareerPathLLMDraft(
            plan_summary="Build release ownership proof around the SDLC gap.",
            milestones=[],
            top_skill_gap_suggestions=[
                ActionableSkillGapPolish(
                    skill="software development life cycle",
                    why_it_matters="SDLC matters because release managers need to own the path from scope to post-release review.",
                    suggested_action="Create a release lifecycle case study with QA gates, approval owners, rollback criteria, and release notes.",
                    proof_to_build="Build a release checklist and go/no-go summary that a hiring manager can inspect.",
                    resume_hint="Add a bullet showing release lifecycle coordination across engineering, QA, and operations.",
                ),
                ActionableSkillGapPolish(
                    skill="not a supplied skill",
                    suggested_action="This must be ignored.",
                ),
            ],
        )

    monkeypatch.setattr(career_path, "explain_role_gap", fake_explain_role_gap)
    monkeypatch.setattr(career_path, "parse_structured", fake_parse_structured)

    report = asyncio.run(
        career_path.generate_career_path(
            42,
            ConfirmedCVData.model_validate(minimal_confirmed_profile()),
        )
    )

    polished = report.requirement_breakdown.top_actionable_skill_gaps[0]
    assert polished.suggested_action.startswith("Create a release lifecycle case study")
    assert "release managers" in polished.why_it_matters
    assert report.requirement_breakdown.skills.skill_gaps[0].suggestion == polished.suggested_action


def test_career_path_replaces_profile_like_plan_summary(monkeypatch):
    from backend.app.features.role_matching import career_path

    async def fake_explain_role_gap(role_id, confirmed_profile, *, with_narrative):
        return GapReport(
            role_id=role_id,
            job_title="Backend Engineer",
            overall_readiness=0.75,
            skills=SkillDimension(
                skill_gaps=[SkillGap(required_skill="Cloud architecture", severity="high")],
            ),
        )

    async def fake_parse_structured(messages, response_format, **kwargs):
        return career_path.CareerPathDraft(
            plan_summary="Backend Developer: Builds APIs.",
            milestones=[
                career_path.CareerPathMilestone(
                    order=1,
                    title="Build cloud evidence",
                    timeline="1 month",
                    rationale="",
                    skills=["Cloud architecture"],
                ),
            ],
        )

    monkeypatch.setattr(career_path, "explain_role_gap", fake_explain_role_gap)
    monkeypatch.setattr(career_path, "parse_structured", fake_parse_structured)

    report = asyncio.run(
        career_path.generate_career_path(
            42,
            ConfirmedCVData.model_validate(minimal_confirmed_profile()),
        )
    )

    assert report.plan_summary != report.current_profile_summary
    assert "cloud architecture" in report.plan_summary.lower()


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


def test_career_path_milestone_rejects_timeline_ranges():
    from backend.app.features.role_matching.schemas import CareerPathMilestone

    with pytest.raises(ValueError):
        CareerPathMilestone.model_validate(
            {
                "order": 1,
                "title": "Build cloud evidence",
                "timeline": "1-2 months",
                "rationale": "Targets the largest gap.",
            }
        )


def test_fallback_career_path_uses_meaningful_milestone_kinds():
    from backend.app.features.role_matching import career_path

    draft = career_path._fallback_draft(
        ["Cloud architecture", "AWS Certified Developer - Associate"],
        ["AWS Certified Developer - Associate"],
    )

    assert draft.plan_summary
    assert [milestone.kind for milestone in draft.milestones[:3]] == [
        "skill",
        "certification",
        "project",
    ]
    assert all("-" not in milestone.timeline for milestone in draft.milestones)


def test_fallback_career_path_summary_is_user_focused():
    from backend.app.features.role_matching import career_path

    summary = career_path._fallback_plan_summary(["Cloud architecture", "Observability"], [])

    assert "you're" in summary.lower()
    assert "already" in summary.lower()
    assert "Cloud architecture" in summary
    assert "roadmap starts" not in summary.lower()
    assert "certification work" not in summary.lower()


def test_career_path_prompt_requests_exact_milestone_durations():
    from backend.app.features.role_matching import career_path

    assert "timeline as a single duration" in career_path._CAREER_PATH_SYSTEM_PROMPT
    assert "Do not output ranges" in career_path._CAREER_PATH_SYSTEM_PROMPT


def test_top_skill_gaps_groups_by_domain_and_ranks_by_worst_gap():
    from backend.app.features.role_matching import career_path

    report = GapReport(
        role_id=1,
        job_title="Backend Engineer",
        skills=SkillDimension(
            skill_gaps=[
                SkillGap(
                    required_skill="Docker",
                    domain="DevOps",
                    importance="important",
                    severity="medium",
                    transferability=0.4,
                ),
                SkillGap(
                    required_skill="Kubernetes",
                    domain="DevOps",
                    importance="essential",
                    severity="high",
                    transferability=0.0,
                ),
                SkillGap(
                    required_skill="PostgreSQL",
                    domain="Databases",
                    importance="important",
                    severity="medium",
                    transferability=0.5,
                ),
            ]
        ),
    )

    top_gaps = career_path._top_skill_gaps(report)

    # DevOps contains the single worst gap (essential/high/0.0) so it ranks
    # ahead of Databases even though DevOps also has a milder gap (Docker).
    assert top_gaps == ["DevOps", "Databases"]


def test_top_skill_gaps_falls_back_to_skill_name_when_domain_is_missing():
    from backend.app.features.role_matching import career_path

    report = GapReport(
        role_id=1,
        job_title="Backend Engineer",
        skills=SkillDimension(
            skill_gaps=[
                SkillGap(
                    required_skill="GraphQL",
                    domain="",
                    importance="important",
                    severity="medium",
                    transferability=0.3,
                ),
            ]
        ),
    )

    # Role never reprocessed with the domain hierarchy -> each ungrouped skill
    # is its own pseudo-domain, so career path still has something to show.
    assert career_path._top_skill_gaps(report) == ["GraphQL"]


def test_top_skill_gaps_prefers_display_casing_over_normalized_required_skill():
    from backend.app.features.role_matching import career_path

    report = GapReport(
        role_id=1,
        job_title="Web Designer",
        skills=SkillDimension(
            skill_gaps=[
                SkillGap(
                    required_skill="ui ux design",
                    display="UI/UX Design",
                    domain="",
                    importance="important",
                    severity="medium",
                    transferability=0.3,
                ),
            ]
        ),
    )

    assert career_path._top_skill_gaps(report) == ["UI/UX Design"]
