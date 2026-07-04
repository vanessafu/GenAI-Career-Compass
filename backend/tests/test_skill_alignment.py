from __future__ import annotations

from backend.app.features.role_matching.skill_alignment import (
    build_skill_evidence_from_confirmed_profile,
    align_skills,
    skill_importance_tier,
)
from backend.app.features.role_matching import gap_analysis
from backend.app.features.role_matching.career_path import timeline_from_readiness
from backend.app.features.role_matching.prepared_skills import SkillEvidence, prepare_user_skills
from backend.app.features.role_matching.schemas import (
    CareerIdentity,
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


def test_align_skills_attaches_domain_to_gaps_when_given() -> None:
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(
        ["Robotics", "Kubernetes"],
        evidence,
        alias_map={},
        skill_domains={"robotics": "Robotics", "kubernetes": "DevOps"},
    )

    domains_by_skill = {gap["required_skill"]: gap["domain"] for gap in result.skill_gaps}
    assert domains_by_skill == {"robotics": "Robotics", "kubernetes": "DevOps"}


def test_align_skills_domain_defaults_to_empty_when_not_given() -> None:
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(["Kubernetes"], evidence, alias_map={})

    assert result.skill_gaps[0]["domain"] == ""


def test_align_skills_domain_scores_average_per_domain_using_raw_domain_label() -> None:
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(
        ["ROS", "LiDAR", "Kubernetes"],
        evidence,
        alias_map={},
        # "Robotics" is the raw domain label straight from sort_skills - it must
        # come back exactly as given, not lowercased/canonicalized.
        skill_domains={"ros": "Robotics", "lidar": "Robotics", "kubernetes": "DevOps"},
    )

    # ROS and LiDAR both have strong evidence -> Robotics domain averages high.
    assert result.domain_scores["Robotics"] > 0.7
    # Kubernetes has zero evidence and is the only skill in DevOps -> 0.0.
    assert result.domain_scores["DevOps"] == 0.0
    assert set(result.domain_skills["Robotics"]) == {"ros", "lidar"}
    assert result.domain_skills["DevOps"] == ["kubernetes"]


def test_align_skills_domain_scores_fall_back_to_ontology_domain_when_no_llm_domain_given() -> None:
    """No LLM-curated domain tag given, but "Kubernetes" resolves in the vendored
    MIND ontology, whose technicalDomains ("DevOps") is used as the tier-2
    fallback instead of degenerating straight to a per-skill pseudo-domain."""
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(["Kubernetes"], evidence, alias_map={})

    assert result.domain_scores == {"DevOps": 0.0}
    assert result.domain_skills == {"DevOps": ["kubernetes"]}


def test_align_skills_domain_scores_fall_back_to_skill_name_when_ontology_cannot_resolve() -> None:
    """A skill unknown to both the LLM domain tags and the ontology falls all
    the way back to the pre-existing per-skill pseudo-domain behavior."""
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())

    result = align_skills(["Zzyzx Custom Internal Tool"], evidence, alias_map={})

    assert result.domain_scores == {"zzyzx custom internal tool": 0.0}


def test_skill_display_preserves_original_casing_in_domain_fallback_and_gaps() -> None:
    """sort_skills stores properly-cased text ("UI/UX Design"); the tier-3
    pseudo-domain fallback and each gap's `display` field should show that
    casing instead of the lowercase normalize_skill_key matching key, while
    the numeric coverage/domain_scores stay identical either way."""
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())
    skill_display = {"ui ux design": "UI/UX Design"}

    with_display = align_skills(["UI/UX Design"], evidence, alias_map={}, skill_display=skill_display)
    without_display = align_skills(["UI/UX Design"], evidence, alias_map={})

    assert with_display.domain_scores == {"UI/UX Design": without_display.domain_scores["ui ux design"]}
    assert with_display.domain_skills == {"UI/UX Design": ["UI/UX Design"]}
    assert with_display.skill_gaps[0]["display"] == "UI/UX Design"
    assert with_display.coverage == without_display.coverage


def test_canon_maps_prefer_the_self_canonical_entry_over_an_aliased_duplicate() -> None:
    """Regression: sort_skills can list both "UI/UX Design" and "Figma" as
    separate entries, and skill_aliases (real DB data) treats "figma" as an
    alias of "ui ux design" for matching - so both canonicalize to the same
    key. A plain dict comprehension keyed by _canon() would let whichever
    entry happens to be processed last silently overwrite the other's
    weight/domain/display; the self-canonical entry ("UI/UX Design" itself)
    must always win regardless of iteration order."""
    evidence = build_skill_evidence_from_confirmed_profile(robotics_profile())
    aliases = {"figma": "ui ux design"}

    # "Figma" listed after "UI/UX Design" - naive last-write-wins would keep Figma's values.
    after = align_skills(
        ["UI/UX Design"],
        evidence,
        alias_map=aliases,
        skill_weights={"UI/UX Design": 0.90, "Figma": 0.83},
        skill_domains={"UI/UX Design": "Frontend", "Figma": "Tools"},
        skill_display={"UI/UX Design": "UI/UX Design", "Figma": "Figma"},
    )
    # "Figma" listed before "UI/UX Design" - order must not matter either.
    before = align_skills(
        ["UI/UX Design"],
        evidence,
        alias_map=aliases,
        skill_weights={"Figma": 0.83, "UI/UX Design": 0.90},
        skill_domains={"Figma": "Tools", "UI/UX Design": "Frontend"},
        skill_display={"Figma": "Figma", "UI/UX Design": "UI/UX Design"},
    )

    for result in (after, before):
        assert result.skill_gaps[0]["display"] == "UI/UX Design"
        assert result.skill_gaps[0]["domain"] == "Frontend"
        assert result.skill_gaps[0]["importance"] == skill_importance_tier(0.90)


def test_skill_display_recovers_user_closest_skill_casing() -> None:
    """The user's own explicit/context terms keep their original casing for
    user_closest_skill, instead of the lowercase canonical matching form."""
    evidence = SkillEvidence(explicit_terms=["Docker"], context_terms=[])

    result = align_skills(
        ["Kubernetes"], evidence=evidence, alias_map={}, enable_ontology_tiers=True
    )

    assert result.skill_gaps[0]["user_closest_skill"] == "Docker"


def test_ontology_implied_tier_requires_opt_in() -> None:
    """The /match recommendation flow calls align_skills(evidence=...) without
    opting in, so it must see the exact pre-ontology two-tier behavior (no
    ontology_implied/reverse_partial credit) even though the ontology can
    resolve the skill."""
    evidence = SkillEvidence(explicit_terms=["Next.js"], context_terms=[])

    result = align_skills(["React"], evidence=evidence, alias_map={})

    assert result.coverage == 0.0
    assert result.skill_gaps[0]["source"] == ""


def test_ontology_implied_tier_credits_a_hop_one_implication() -> None:
    evidence = SkillEvidence(explicit_terms=["Next.js"], context_terms=[])

    result = align_skills(
        ["React"], evidence=evidence, alias_map={}, enable_ontology_tiers=True
    )

    assert result.skill_gaps[0]["source"] == "ontology_implied"
    assert result.skill_gaps[0]["transferability"] == 0.65
    assert result.coverage == 0.65


def test_reverse_prerequisite_tier_credits_a_lesser_but_related_skill() -> None:
    """Role wants Kubernetes, user only has Docker (a prerequisite of it) -
    should get partial credit, not a flat miss."""
    evidence = SkillEvidence(explicit_terms=["Docker"], context_terms=[])

    result = align_skills(
        ["Kubernetes"], evidence=evidence, alias_map={}, enable_ontology_tiers=True
    )

    assert result.skill_gaps[0]["source"] == "reverse_partial"
    assert result.skill_gaps[0]["transferability"] == 0.40


def test_prepared_path_matches_on_the_fly_path_for_ontology_tiers() -> None:
    """prepare_user_skills() (computed once) must produce identical align_skills
    results to the equivalent evidence= + enable_ontology_tiers=True call."""
    evidence = SkillEvidence(explicit_terms=["Next.js", "Docker"], context_terms=["Fullstack team"])
    prepared = prepare_user_skills(evidence)
    required = ["React", "Kubernetes", "FastAPI"]

    from_prepared = align_skills(required, prepared=prepared)
    from_evidence = align_skills(required, evidence=evidence, enable_ontology_tiers=True)

    assert from_prepared.coverage == from_evidence.coverage
    assert from_prepared.matched_skills == from_evidence.matched_skills
    assert [g["source"] for g in from_prepared.skill_gaps] == [
        g["source"] for g in from_evidence.skill_gaps
    ]


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
        def encode_queries(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] for _ in texts]

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

    response = _match_roles_sync(profile, top_k=2, include_debug=True)
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
        "fetch_skill_aliases",
        lambda: {"ros2": "ros", "nvidia jetson": "embedded systems"},
        raising=False,
    )
    monkeypatch.setattr(
        gap_analysis,
        "_fetch_role_skills_from_table",
        lambda role_id: ["Robotics", "ROS", "Embedded Systems"],
        raising=False,
    )

    report = gap_analysis.analyze_role_gap(160, profile)

    assert report.skills.coverage > 0.70
    assert "ros" in report.skills.matched_skills
    assert "embedded systems" in report.skills.matched_skills
    assert "robotics" not in report.skills.missing_skills
    assert "ros" not in report.skills.missing_skills


def test_gap_analysis_uses_prepared_skills_when_present_and_current(monkeypatch) -> None:
    """A profile carrying a fresh prepared_skills payload should route through
    align_skills(prepared=...) - ontology_implied credit for React (implied by
    Next.js) should show up in coverage/domain_coverage, and matched_skills
    still requires the higher explicit/token bar."""
    profile = robotics_profile()
    evidence = SkillEvidence(explicit_terms=["Next.js"], context_terms=[])
    profile.prepared_skills = prepare_user_skills(evidence)

    monkeypatch.setattr(
        gap_analysis,
        "_fetch_role",
        lambda role_id: {
            "role_id": role_id,
            "job_title": "Frontend Engineer",
            "job_description": "Builds UIs.",
            "raw_skills": "React",
            "domain_tags": "frontend",
        },
    )
    monkeypatch.setattr(gap_analysis, "_fetch_role_certs", lambda role_id: [])
    monkeypatch.setattr(gap_analysis, "fetch_skill_aliases", lambda: {}, raising=False)
    monkeypatch.setattr(
        gap_analysis, "_fetch_role_skills_from_table", lambda role_id: ["React"], raising=False
    )

    report = gap_analysis.analyze_role_gap(161, profile)

    assert report.skills.coverage == 0.65
    assert report.skills.skill_gaps[0].source == "ontology_implied"
    assert "react" not in report.skills.matched_skills


def test_match_endpoint_credits_ontology_implied_skills(monkeypatch) -> None:
    """/match now opts into the ontology tiers (service.py passes
    enable_ontology_tiers=True) - a profile that only lists "Next.js" should
    get nonzero skill-overlap credit against a role that requires "React"."""
    profile = UserCareerProfile(
        career_identity=CareerIdentity(title="Frontend Engineer", summary="Builds web UIs."),
        skills=["Next.js"],
    )

    class FakeEmbedder:
        def encode_queries(self, texts: list[str]) -> list[list[float]]:
            return [[0.1] for _ in texts]

    rows = [
        {
            "role_id": "frontend",
            "job_title": "Frontend Engineer",
            "job_description": "Builds React UIs.",
            "raw_skills": "",
            "domain_tags": "frontend",
            "salary_median_monthly_gross_eur": None,
            "capability_vector_similarity": 0.5,
            "intent_vector_similarity": 0.5,
            "esco_title": "Frontend Engineer",
            "esco_uri": "frontend",
        },
    ]

    monkeypatch.setattr(
        "backend.app.features.role_matching.embedder.get_embedder",
        lambda: FakeEmbedder(),
    )
    monkeypatch.setattr(
        "backend.app.features.role_matching.service._fetch_catalog",
        lambda *_: (rows, {}, {"frontend": ["react"]}, {}),
    )

    response = _match_roles_sync(profile, top_k=1, include_debug=True)
    role = response.buckets.ready_now[0] if response.buckets.ready_now else (
        response.buckets.next_step[0] if response.buckets.next_step else response.buckets.aspirational[0]
    )

    assert role.signal_breakdown.normalized_skill_overlap > 0.0


def test_roadmap_timeline_is_bounded_by_readiness() -> None:
    assert timeline_from_readiness(0.80) == "1-3 months"
    assert timeline_from_readiness(0.60) == "3-5 months"
    assert timeline_from_readiness(0.45) == "3-5 months"
    assert timeline_from_readiness(0.26) == "5-8 months"
