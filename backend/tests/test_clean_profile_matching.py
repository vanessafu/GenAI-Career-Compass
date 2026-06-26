from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from pydantic import ValidationError

import backend.app.features.role_matching.schemas as role_schemas
from backend.app.features.role_matching.recommendation import Candidate, recommend
from backend.app.features.role_matching.schemas import (
    CareerIdentity,
    RecommendationBucket,
    RecommendationMode,
    RoleMatchRequest,
    UserCareerProfile,
    UserCertification,
    UserEducation,
    UserExperience,
    UserProject,
)
from backend.app.features.role_matching.service import (
    _apply_role_summaries,
    _cert_overlap,
    _match_roles_sync,
    build_capability_text,
    build_intent_text,
    infer_seniority_gap,
    map_profile_domains,
    normalize_certification_name,
    normalize_user_certifications,
    normalize_user_skills,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def sample_profile() -> UserCareerProfile:
    return UserCareerProfile(
        career_identity=CareerIdentity(
            title="Robust Systems Architect",
            summary=(
                "Strong backend, cloud infrastructure, AI, and automation "
                "orientation."
            ),
        ),
        education=[
            UserEducation(
                degree="MSc Computer Science",
                institution="TU Muenchen",
                start_year="2015",
                end_year="2017",
            )
        ],
        experience=[
            UserExperience(
                role="Senior Backend Developer",
                organization="Stripe",
                start_date="2022",
                end_date="Present",
                summary="Built scalable payment services.",
                skills=["Java", "PostgreSQL", "RESTful APIs"],
            )
        ],
        skills=[
            "Python",
            "RESTful APIs",
            "PostgreSQL",
            "Java",
            "Microservices Architecture",
        ],
        interests=[
            "Artificial Intelligence",
            "Big Data scale",
            "Process Automation",
            "Open Source",
        ],
        certifications=[
            UserCertification(
                name="AWS Certified Developer - Associate",
                issuer="Amazon Web Services",
                year="2023",
            )
        ],
        projects=[
            UserProject(
                title="Payment microservice migration",
                summary="Migrated monolith to 12 services.",
                technologies=["Java", "PostgreSQL", "Docker"],
                year="2023",
            )
        ],
    )


class CleanProfileSchemaTests(unittest.TestCase):
    def test_valid_screenshot_shaped_profile_is_accepted(self) -> None:
        request = RoleMatchRequest(profile=sample_profile(), top_k=3)

        self.assertEqual(request.mode, RecommendationMode.balanced)
        self.assertFalse(request.include_debug)
        self.assertEqual(request.profile.career_identity.title, "Robust Systems Architect")

    def test_role_match_request_defaults_to_nine_results(self) -> None:
        request = RoleMatchRequest(profile=sample_profile())

        self.assertEqual(9, request.top_k)

    def test_empty_profile_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RoleMatchRequest(profile=UserCareerProfile())

    def test_profile_with_capability_but_no_intent_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RoleMatchRequest(profile=UserCareerProfile(skills=["Python"]))

    def test_old_confirmed_cv_shape_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            RoleMatchRequest.model_validate(
                {
                    "confirmed_profile": {"confirmed_cv_data": {}},
                    "identity": {
                        "career_identity_statement": "Backend engineer",
                        "interests": ["AI"],
                    },
                }
            )


class CareerResultsV1SchemaTests(unittest.TestCase):
    def test_result_item_schema_matches_minimal_frontend_card_contract(self) -> None:
        CareerResultV1 = getattr(role_schemas, "CareerResultV1", None)
        self.assertIsNotNone(CareerResultV1, "CareerResultV1 schema should exist")

        result = CareerResultV1(
            role_id=123,
            bucket="top_match",
            title="Data Engineer",
            matching_score=95,
            salary="EUR 95k",
            description="Designs scalable data pipelines and warehouse systems.",
            esco_title="Data engineer",
            esco_uri="http://data.europa.eu/esco/occupation/example",
        )

        self.assertEqual(
            result.model_dump(),
            {
                "role_id": 123,
                "bucket": "top_match",
                "title": "Data Engineer",
                "matching_score": 95,
                "salary": "EUR 95k",
                "description": "Designs scalable data pipelines and warehouse systems.",
                "esco_title": "Data engineer",
                "esco_uri": "http://data.europa.eu/esco/occupation/example",
                "matched_skills": [],
                "missing_skills": [],
                "matched_domains": [],
                "matched_certifications": [],
            },
        )

    def test_career_results_v1_flattens_internal_bucketed_matches(self) -> None:
        CareerResultsV1 = getattr(role_schemas, "CareerResultsV1", None)
        self.assertIsNotNone(CareerResultsV1, "CareerResultsV1 schema should exist")

        buckets = role_schemas.BucketedRoles(
            ready_now=[
                role_schemas.RoleMatch(
                    role_id=123,
                    job_title="Data Engineer",
                    description="Designs scalable data pipelines.",
                    final_score=0.95,
                    bucket=RecommendationBucket.ready_now,
                    salary="EUR 95k",
                    esco_title="Data engineer",
                    esco_uri="http://data.europa.eu/esco/occupation/example",
                    matched_skills=["python"],
                    missing_skills=["spark"],
                    matched_domains=["data_engineering"],
                    matched_certifications=["AWS Certified Developer - Associate"],
                    signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
                )
            ]
        )

        payload = CareerResultsV1.from_bucketed_roles(buckets).model_dump()

        self.assertEqual(
            payload,
            {
                "results": [
                    {
                        "role_id": 123,
                        "bucket": "ready_now",
                        "title": "Data Engineer",
                        "matching_score": 98,
                        "salary": "EUR 95k",
                        "description": "Designs scalable data pipelines.",
                        "esco_title": "Data engineer",
                        "esco_uri": "http://data.europa.eu/esco/occupation/example",
                        "matched_skills": ["python"],
                        "missing_skills": ["spark"],
                        "matched_domains": ["data_engineering"],
                        "matched_certifications": ["AWS Certified Developer - Associate"],
                    }
                ]
            },
        )

    def test_matching_score_is_calibrated_by_recommendation_bucket(self) -> None:
        roles = [
            role_schemas.RoleMatch(
                role_id="ready",
                job_title="Ready Role",
                final_score=0.42,
                bucket=RecommendationBucket.ready_now,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
            role_schemas.RoleMatch(
                role_id="next",
                job_title="Next Role",
                final_score=0.42,
                bucket=RecommendationBucket.next_step,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
            role_schemas.RoleMatch(
                role_id="stretch",
                job_title="Stretch Role",
                final_score=0.42,
                bucket=RecommendationBucket.aspirational,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
        ]

        scores = [
            role_schemas.CareerResultV1.from_role_match(role).matching_score
            for role in roles
        ]

        self.assertEqual([93, 81, 63], scores)


class RoleCardSummaryGenerationTests(unittest.TestCase):
    def test_generated_card_summaries_describe_roles_not_user_fit(self) -> None:
        role = role_schemas.RoleMatch(
            role_id=123,
            job_title="Business Intelligence Analyst",
            description="Analyzes data to provide insights and support business decision-making.",
            final_score=0.72,
            bucket=RecommendationBucket.ready_now,
            salary="EUR 67k",
            esco_title="Business analyst",
            matched_skills=["python", "sql", "tableau"],
            missing_skills=["business acumen"],
            matched_domains=["data_analytics"],
            matched_certifications=["Google Data Analytics Certificate"],
            signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
        )
        response = role_schemas.RoleMatchResponse(
            mode=RecommendationMode.balanced,
            buckets=role_schemas.BucketedRoles(ready_now=[role]),
        )
        captured: dict[str, object] = {}

        async def fake_parse_structured(messages, response_format, **kwargs):
            captured["messages"] = messages
            captured["payload"] = json.loads(messages[1]["content"])
            return role_schemas.RoleSummaryBatch(
                summaries=[
                    role_schemas.RoleSummaryItem(
                        role_id="123",
                        summary=(
                            "Designs dashboards for business leaders. "
                            "Uses Python, SQL, and Tableau for analysis."
                        ),
                    )
                ]
            )

        with patch(
            "backend.app.features.role_matching.service.openai_client.parse_structured",
            fake_parse_structured,
        ):
            asyncio.run(_apply_role_summaries(sample_profile(), response))

        system_prompt = captured["messages"][0]["content"]  # type: ignore[index]
        payload = captured["payload"]  # type: ignore[assignment]
        payload_role = payload["roles"][0]  # type: ignore[index]

        self.assertIn("one present-tense sentence", system_prompt)
        self.assertIn("Do not mention the user", system_prompt)
        self.assertIn("Do not list skills", system_prompt)
        self.assertNotIn("profile", payload)
        self.assertEqual(
            {"role_id", "title", "esco_title", "description"},
            set(payload_role),
        )
        self.assertEqual("Designs dashboards for business leaders.", role.description)


class CleanProfileTextBuilderTests(unittest.TestCase):
    def test_capability_text_contains_profile_evidence_sections(self) -> None:
        text = build_capability_text(sample_profile())

        self.assertIn("Experience 1: Senior Backend Developer", text)
        self.assertIn("Education 1: MSc Computer Science", text)
        self.assertIn("Skills: Python, RESTful APIs, PostgreSQL", text)
        self.assertIn("Certification 1: AWS Certified Developer - Associate", text)
        self.assertIn("Project 1: Payment microservice migration", text)

    def test_intent_text_contains_identity_and_interests_only(self) -> None:
        text = build_intent_text(sample_profile())

        self.assertIn("Career identity: Robust Systems Architect", text)
        self.assertIn("Strong backend, cloud infrastructure", text)
        self.assertIn("Interests: Artificial Intelligence, Big Data scale", text)
        self.assertNotIn("possible", text.casefold())
        self.assertNotIn("Payment microservice migration", text)
        self.assertNotIn("AWS Certified Developer", text)


class SupabaseBackedNormalizationTests(unittest.TestCase):
    def test_user_skills_normalize_through_alias_map(self) -> None:
        normalized = normalize_user_skills(
            ["postgres", "PostgreSQL", "RESTful APIs", "Unknown Tool"],
            {
                "postgres": "postgresql",
                "postgresql": "postgresql",
                "restful apis": "restful apis",
            },
        )

        self.assertEqual(normalized, ["postgresql", "restful apis", "unknown tool"])

    def test_default_skill_aliases_cover_common_frontend_and_data_inputs(self) -> None:
        normalized = normalize_user_skills(
            ["APIs", "Spring", "Figma", "UX", "pandas", "analytics"],
            {},
        )

        self.assertEqual(
            [
                "rest apis",
                "spring framework",
                "ui ux design",
                "python",
                "data analysis",
            ],
            normalized,
        )

    def test_default_skill_aliases_cover_ci_testing_cloud_and_scripting_inputs(self) -> None:
        normalized = normalize_user_skills(
            [
                "continuous integration (CI)",
                "automated testing",
                "Azure cloud",
                "Linux services",
                "shell scripts",
            ],
            {},
        )

        self.assertEqual(
            ["ci cd", "test automation", "azure", "linux", "scripting"],
            normalized,
        )

    def test_certifications_use_token_cleanup(self) -> None:
        self.assertEqual(
            normalize_certification_name("AWS Certified Developer - Associate"),
            "aws certified developer associate",
        )

    def test_certification_aliases_normalize_to_canonical_match_keys(self) -> None:
        user_certs = normalize_user_certifications(["Google Data Analytics Certificate"])

        self.assertIn("google data analytics professional certificate", user_certs)
        overlap, matched = _cert_overlap(
            [
                (
                    "Google Data Analytics Professional Certificate",
                    "google data analytics professional certificate",
                )
            ],
            user_certs,
        )
        self.assertEqual(1.0, overlap)
        self.assertEqual(["Google Data Analytics Professional Certificate"], matched)

    def test_profile_interests_map_to_supported_domain_tags(self) -> None:
        self.assertEqual(
            map_profile_domains(sample_profile()),
            ["architecture", "backend", "cloud", "ai_ml", "automation_scripting", "data_engineering"],
        )

    def test_tooling_profile_maps_to_devops_and_qa_domains(self) -> None:
        profile = UserCareerProfile(
            career_identity=CareerIdentity(
                title="Java Tooling Engineer",
                summary=(
                    "Builds CI pipelines with Jenkins and Azure, Ansible setup "
                    "automation, and test automation using Selenium and JUnit."
                ),
            ),
            skills=["Java"],
        )

        self.assertEqual(
            map_profile_domains(profile),
            ["cloud", "software_engineering", "automation_scripting", "devops", "qa_testing"],
        )

    def test_role_skill_overlap_uses_supabase_role_skills_not_mind_ontology(self) -> None:
        source = (
            REPO_ROOT
            / "backend"
            / "app"
            / "features"
            / "role_matching"
            / "service.py"
        ).read_text(encoding="utf-8")

        self.assertIn("FROM role_skills", source)
        self.assertIn("skill_aliases", source)
        self.assertNotIn("get_ontology", source)

    def test_matcher_does_not_store_user_profile_or_user_embeddings(self) -> None:
        source = (
            REPO_ROOT
            / "backend"
            / "app"
            / "features"
            / "role_matching"
            / "service.py"
        ).read_text(encoding="utf-8").casefold()

        self.assertNotIn("insert into", source)
        self.assertNotIn("update user", source)
        self.assertNotIn("user_embeddings", source)
        self.assertNotIn("profile_embeddings", source)


class RankingBehaviorTests(unittest.TestCase):
    def test_backend_profile_ranks_backend_role_above_unrelated_role(self) -> None:
        backend = Candidate(
            role_id=1,
            job_title="Backend Engineer",
            description="Builds APIs.",
            required_skills=["java", "postgresql", "restful apis"],
            domain_tags=["backend", "software_engineering"],
            role_certifications=[],
            capability_vector_similarity=0.72,
            intent_vector_similarity=0.55,
            skill_overlap=1.0,
            domain_overlap=0.5,
            certification_overlap=0.0,
            seniority_fit=1.0,
            seniority_gap="match",
            matched_skills=["java", "postgresql", "restful apis"],
            missing_skills=[],
            matched_domains=["backend"],
            matched_certifications=[],
        )
        unrelated = Candidate(
            role_id=2,
            job_title="UX Researcher",
            description="Runs user interviews.",
            required_skills=["user research", "figma"],
            domain_tags=["ux_ui"],
            role_certifications=[],
            capability_vector_similarity=0.2,
            intent_vector_similarity=0.2,
            skill_overlap=0.0,
            domain_overlap=0.0,
            certification_overlap=0.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
            matched_skills=[],
            missing_skills=["user research", "figma"],
            matched_domains=[],
            matched_certifications=[],
        )

        buckets = recommend([unrelated, backend], mode=RecommendationMode.balanced, per_bucket=3)

        self.assertEqual(buckets.ready_now[0].role_id, 1)
        self.assertEqual(buckets.ready_now[0].bucket, RecommendationBucket.ready_now)
        self.assertGreater(
            buckets.ready_now[0].signal_breakdown.normalized_skill_overlap,
            buckets.aspirational[0].signal_breakdown.normalized_skill_overlap,
        )

    def test_recommend_top_k_is_total_and_balanced_across_sections(self) -> None:
        candidates: list[Candidate] = []
        for i in range(6):
            candidates.append(
                Candidate(
                    role_id=f"ready-{i}",
                    job_title=f"Ready {i}",
                    capability_vector_similarity=0.7,
                    intent_vector_similarity=0.7,
                    skill_overlap=0.7,
                    seniority_fit=1.0,
                    seniority_gap="match",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"next-{i}",
                    job_title=f"Next {i}",
                    capability_vector_similarity=0.7,
                    intent_vector_similarity=0.7,
                    skill_overlap=0.4,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"asp-{i}",
                    job_title=f"Aspirational {i}",
                    capability_vector_similarity=0.7,
                    intent_vector_similarity=0.7,
                    skill_overlap=0.1,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )

        buckets = recommend(candidates, mode=RecommendationMode.balanced, top_k=6)

        self.assertEqual(2, len(buckets.ready_now))
        self.assertEqual(2, len(buckets.next_step))
        self.assertEqual(2, len(buckets.aspirational))

    def test_recommend_redistributes_total_slots_when_a_section_is_empty(self) -> None:
        candidates: list[Candidate] = []
        for i in range(6):
            candidates.append(
                Candidate(
                    role_id=f"next-{i}",
                    job_title=f"Next {i}",
                    capability_vector_similarity=0.7,
                    intent_vector_similarity=0.7,
                    skill_overlap=0.4,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"asp-{i}",
                    job_title=f"Aspirational {i}",
                    capability_vector_similarity=0.7,
                    intent_vector_similarity=0.7,
                    skill_overlap=0.1,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )

        buckets = recommend(candidates, mode=RecommendationMode.balanced, top_k=6)

        self.assertEqual(0, len(buckets.ready_now))
        self.assertEqual(3, len(buckets.next_step))
        self.assertEqual(3, len(buckets.aspirational))

    def test_default_match_path_does_not_redistribute_empty_bucket_slots(self) -> None:
        rows = []
        role_skills: dict[str, list[str]] = {}
        for i in range(6):
            next_id = f"next-{i}"
            asp_id = f"asp-{i}"
            rows.extend(
                [
                    {
                        "role_id": next_id,
                        "job_title": f"Next {i}",
                        "job_description": "Builds useful data tools.",
                        "raw_skills": "",
                        "domain_tags": "",
                        "salary_median_monthly_gross_eur": None,
                        "capability_vector_similarity": 0.7,
                        "intent_vector_similarity": 0.7,
                        "esco_title": "Data engineer",
                        "esco_uri": "http://data.europa.eu/esco/occupation/next",
                    },
                    {
                        "role_id": asp_id,
                        "job_title": f"Aspirational {i}",
                        "job_description": "Builds platform systems.",
                        "raw_skills": "",
                        "domain_tags": "",
                        "salary_median_monthly_gross_eur": None,
                        "capability_vector_similarity": 0.7,
                        "intent_vector_similarity": 0.7,
                        "esco_title": "Platform engineer",
                        "esco_uri": "http://data.europa.eu/esco/occupation/asp",
                    },
                ]
            )
            role_skills[next_id] = ["python", "postgresql", "spark", "airflow", "dbt"]
            role_skills[asp_id] = ["rust", "go", "kubernetes"]

        class FakeEmbedder:
            def encode_queries(self, texts: list[str]) -> tuple[list[float], list[float]]:
                return [0.1], [0.2]

        with (
            patch("backend.app.features.role_matching.embedder.get_embedder", return_value=FakeEmbedder()),
            patch(
                "backend.app.features.role_matching.service._fetch_catalog",
                return_value=(rows, {}, role_skills, {}),
            ),
        ):
            response = _match_roles_sync(
                sample_profile(),
                top_k=9,
                mode=RecommendationMode.balanced,
                include_debug=False,
            )

        self.assertEqual(0, len(response.buckets.ready_now))
        self.assertEqual(3, len(response.buckets.next_step))
        self.assertEqual(3, len(response.buckets.aspirational))

    def test_ready_now_requires_skill_and_capability_alignment(self) -> None:
        aligned_broad_role = Candidate(
            role_id="aligned",
            job_title="Software Engineer",
            capability_vector_similarity=0.70,
            intent_vector_similarity=0.65,
            skill_overlap=0.60,
            domain_overlap=1.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
        )
        narrow_tool_role = Candidate(
            role_id="tool",
            job_title="Specific Tool Engineer",
            capability_vector_similarity=0.55,
            intent_vector_similarity=0.65,
            skill_overlap=0.70,
            domain_overlap=1.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
        )

        buckets = recommend(
            [aligned_broad_role, narrow_tool_role],
            mode=RecommendationMode.balanced,
            top_k=2,
        )

        self.assertEqual(["aligned"], [role.role_id for role in buckets.ready_now])
        self.assertEqual(["tool"], [role.role_id for role in buckets.next_step])

    def test_exact_certification_match_improves_score(self) -> None:
        without_cert = Candidate(
            role_id=1,
            job_title="Cloud Developer",
            description=None,
            required_skills=["aws"],
            domain_tags=["cloud"],
            role_certifications=["aws certified developer associate"],
            capability_vector_similarity=0.5,
            intent_vector_similarity=0.5,
            skill_overlap=0.5,
            domain_overlap=1.0,
            certification_overlap=0.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
            matched_skills=["aws"],
            missing_skills=[],
            matched_domains=["cloud"],
            matched_certifications=[],
        )
        with_cert = Candidate(
            role_id=2,
            job_title="Cloud Developer Certified",
            description=None,
            required_skills=["aws"],
            domain_tags=["cloud"],
            role_certifications=["aws certified developer associate"],
            capability_vector_similarity=0.5,
            intent_vector_similarity=0.5,
            skill_overlap=0.5,
            domain_overlap=1.0,
            certification_overlap=1.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
            matched_skills=["aws"],
            missing_skills=[],
            matched_domains=["cloud"],
            matched_certifications=["AWS Certified Developer - Associate"],
        )

        buckets = recommend([without_cert, with_cert], mode=RecommendationMode.balanced, per_bucket=2)

        self.assertEqual(buckets.next_step[0].role_id, 2)
        self.assertGreater(
            buckets.next_step[0].final_score,
            buckets.next_step[1].final_score,
        )

    def test_ai_interest_can_lift_a_stretch_role_without_overpowering_skill_mismatch(self) -> None:
        ready_backend = Candidate(
            role_id=1,
            job_title="Backend Engineer",
            capability_vector_similarity=0.72,
            intent_vector_similarity=0.45,
            skill_overlap=1.0,
            domain_overlap=0.5,
            certification_overlap=0.0,
            seniority_fit=1.0,
            seniority_gap="match",
        )
        ai_stretch = Candidate(
            role_id=2,
            job_title="AI Platform Engineer",
            capability_vector_similarity=0.35,
            intent_vector_similarity=0.9,
            skill_overlap=0.15,
            domain_overlap=1.0,
            certification_overlap=0.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
        )

        buckets = recommend([ai_stretch, ready_backend], mode=RecommendationMode.balanced, per_bucket=3)

        self.assertEqual(buckets.ready_now[0].role_id, 1)
        self.assertEqual(buckets.aspirational[0].role_id, 2)

    def test_intent_only_similarity_does_not_promote_to_next_step(self) -> None:
        intent_only = Candidate(
            role_id=1,
            job_title="Cloud Architect",
            capability_vector_similarity=0.30,
            intent_vector_similarity=0.80,
            skill_overlap=0.0,
            domain_overlap=0.0,
            certification_overlap=0.0,
            seniority_fit=0.5,
            seniority_gap="unknown",
        )

        buckets = recommend([intent_only], mode=RecommendationMode.balanced, per_bucket=3)

        self.assertEqual([], buckets.ready_now)
        self.assertEqual([], buckets.next_step)
        self.assertEqual(buckets.aspirational[0].role_id, 1)

    def test_domain_signal_is_gated_by_skill_overlap_in_final_score(self) -> None:
        java_developer = Candidate(
            role_id=1,
            job_title="Java Developer",
            capability_vector_similarity=0.67,
            intent_vector_similarity=0.55,
            skill_overlap=0.40,
            domain_overlap=0.50,
            certification_overlap=0.0,
            seniority_fit=1.0,
            seniority_gap="match",
            matched_skills=["java", "sql"],
            matched_domains=["backend"],
        )
        java_architect = Candidate(
            role_id=2,
            job_title="Java Architect",
            capability_vector_similarity=0.67,
            intent_vector_similarity=0.55,
            skill_overlap=0.25,
            domain_overlap=1.0,
            certification_overlap=0.0,
            seniority_fit=0.5,
            seniority_gap="unknown",
            matched_skills=["java"],
            matched_domains=["architecture", "cloud"],
        )

        buckets = recommend([java_architect, java_developer], mode=RecommendationMode.balanced, per_bucket=3)

        self.assertEqual(buckets.next_step[0].role_id, 1)

    def test_senior_profile_is_not_penalized_for_senior_role(self) -> None:
        self.assertEqual(
            infer_seniority_gap("Senior Backend Developer", "Senior Backend Engineer"),
            ("match", 1.0),
        )

    def test_student_identity_is_a_stretch_for_senior_roles(self) -> None:
        gap, fit = infer_seniority_gap("Frontend student", "Senior Front End Developer")

        self.assertEqual("stretch", gap)
        self.assertLess(fit, 0.5)


if __name__ == "__main__":
    unittest.main()
