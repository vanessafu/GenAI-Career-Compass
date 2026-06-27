from __future__ import annotations

from backend.app.features.role_matching.skill_alignment import (
    build_skill_evidence_from_confirmed_profile,
    align_skills,
)
from backend.app.features.role_matching import gap_analysis
from backend.app.features.role_matching.career_path import timeline_from_readiness
from backend.app.features.role_matching.schemas import (
    CareerIdentity,
    RecommendationMode,
    UserCareerProfile,
    UserExperience,
    UserProject,
)
from backend.app.features.role_matching.service import _match_roles_sync
from backend.app.features.cv_confirmation.schemas import ConfirmationMetadata, ConfirmedCVData
from backend.app.features.cv_parsing.schemas import (
    CVData,
    Education,
    Experience,
    PersonalInfo,
    ProfileSummary,
    Project,
    SkillsExtracted,
    TechnicalSkill,
)


def robotics_profile() -> ConfirmedCVData:
    cv_data = CVData(
        personal_info=PersonalInfo(current_role="Robotics Perception Engineer"),
        profile_summary=ProfileSummary(
            summary=(
                "Builds real-time perception stacks for autonomous mobile robots, "
                "combining LiDAR SLAM, sensor fusion, and embedded GPU deployment."
            ),
            current_seniority_level="mid",
            years_of_experience=5,
        ),
        education=[
            Education(
                degree_type="MEng",
                field_of_study="Robotics and Autonomous Systems",
                institution="KIT",
            )
        ],
        experience=[
            Experience(
                role="Robotics Perception Engineer",
                core_responsibilities=["Built ROS2 perception nodes for AMRs."],
                contextual_skills=["LiDAR perception", "Sensor fusion"],
            )
        ],
        projects=[
            Project(
                title="Warehouse AMR perception stack",
                description="Improved localization stability on NVIDIA Jetson.",
                technologies=["ROS2", "C++", "CUDA", "OpenCV", "NVIDIA Jetson"],
            )
        ],
        skills_extracted=SkillsExtracted(
            technical_skills=[
                TechnicalSkill(name="ROS2"),
                TechnicalSkill(name="LiDAR perception"),
                TechnicalSkill(name="NVIDIA Jetson"),
                TechnicalSkill(name="Real-time Linux"),
            ]
        ),
        interests=["Autonomous mobile robots", "Edge AI"],
    )
    return ConfirmedCVData(
        confirmed_cv_data=cv_data,
        confirmation_metadata=ConfirmationMetadata(),
    )


def test_skill_alignment_matches_versions_compact_forms_and_token_variants() -> None:
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(
        ["ROS", "LiDAR", "Embedded Systems", "Sensors"],
        evidence,
        alias_map={"ros2": "ros", "nvidia jetson": "embedded systems"},
    )

    assert result.coverage >= 0.75
    assert "ros" in result.matched_skills
    assert "lidar" in result.matched_skills
    assert "embedded systems" in result.matched_skills
    assert "sensors" in result.matched_skills
    assert "ros" not in result.missing_skills


def test_context_only_role_family_credit_is_partial_not_full() -> None:
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(["Robotics"], evidence, alias_map={})

    assert result.coverage > 0
    assert result.coverage < 1
    assert result.skill_gaps[0]["required_skill"] == "robotics"
    assert result.skill_gaps[0]["transferability"] == result.coverage


def test_matching_ranks_niche_aligned_role_above_generic_ai(monkeypatch) -> None:
    profile = UserCareerProfile(
        career_identity=CareerIdentity(
            title="Robotics Perception Engineer",
            summary="Builds real-time perception stacks for autonomous mobile robots.",
        ),
        experience=[
            UserExperience(
                role="Robotics Perception Engineer",
                summary="LiDAR SLAM and sensor fusion on embedded GPUs.",
                skills=["ROS2", "LiDAR perception", "C++", "Python"],
            )
        ],
        skills=["ROS2", "LiDAR perception", "C++", "Python"],
        interests=["Autonomous mobile robots", "Edge AI"],
        projects=[
            UserProject(
                title="Warehouse AMR perception stack",
                summary="Improved localization stability.",
                technologies=["ROS2", "NVIDIA Jetson"],
            )
        ],
    )

    class FakeEmbedder:
        def encode_queries(self, texts: list[str]) -> tuple[list[float], list[float]]:
            return [0.1], [0.2]

    rows = [
        {
            "role_id": "robotics",
            "job_title": "Robotics Engineer",
            "job_description": "Designs robotic systems that operate autonomously.",
            "raw_skills": "",
            "domain_tags": "robotics,embedded_iot",
            "salary_median_monthly_gross_eur": None,
            "capability_vector_similarity": 0.62,
            "intent_vector_similarity": 0.58,
            "esco_title": "Robotics Engineer",
            "esco_uri": "robotics",
        },
        {
            "role_id": "generic-ai",
            "job_title": "Artificial Intelligence Engineer",
            "job_description": "Develops AI models and applications.",
            "raw_skills": "",
            "domain_tags": "ai_ml",
            "salary_median_monthly_gross_eur": None,
            "capability_vector_similarity": 0.68,
            "intent_vector_similarity": 0.68,
            "esco_title": "Artificial Intelligence Engineer",
            "esco_uri": "ai",
        },
    ]

    monkeypatch.setattr(
        "backend.app.features.role_matching.embedder.get_embedder",
        lambda: FakeEmbedder(),
    )
    monkeypatch.setattr(
        "backend.app.features.role_matching.service._fetch_catalog",
        lambda *_: (
            rows,
            {"ros2": "ros", "nvidia jetson": "embedded systems"},
            {
                "robotics": ["robotics", "ros", "embedded systems", "c++", "python"],
                "generic-ai": ["python", "machine learning"],
            },
            {},
        ),
    )

    response = _match_roles_sync(profile, top_k=2, mode=RecommendationMode.balanced, include_debug=True)
    roles = [
        *response.buckets.ready_now,
        *response.buckets.next_step,
        *response.buckets.aspirational,
    ]

    assert [role.role_id for role in roles][:2] == ["robotics", "generic-ai"]


def test_gap_analysis_uses_shared_alignment_for_niche_variants(monkeypatch) -> None:
    profile = robotics_profile()

    monkeypatch.setattr(
        gap_analysis,
        "_fetch_role",
        lambda role_id: {
            "role_id": role_id,
            "job_title": "Robotics Engineer",
            "job_description": "Designs robotic systems.",
            "raw_skills": "Robotics, ROS, Embedded Systems",
            "domain_tags": "robotics,embedded_iot",
        },
    )
    monkeypatch.setattr(gap_analysis, "_fetch_role_certs", lambda role_id: [])
    monkeypatch.setattr(
        gap_analysis,
        "_fetch_role_skill_data",
        lambda role_id: (
            ["Robotics", "ROS", "Embedded Systems"],
            {"ros2": "ros", "nvidia jetson": "embedded systems"},
        ),
        raising=False,
    )

    report = gap_analysis.analyze_role_gap(160, profile)

    assert report.skills.coverage > 0.70
    assert "ros" in report.skills.matched_skills
    assert "embedded systems" in report.skills.matched_skills
    assert "robotics" not in report.skills.missing_skills
    assert "ros" not in report.skills.missing_skills


def test_roadmap_timeline_is_bounded_by_readiness() -> None:
    assert timeline_from_readiness(0.80) == "3 months"
    assert timeline_from_readiness(0.60) == "6 months"
    assert timeline_from_readiness(0.45) == "9 months"
    assert timeline_from_readiness(0.26) == "12 months"
