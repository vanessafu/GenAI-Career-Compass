from __future__ import annotations

import asyncio
import json
import unittest
from unittest.mock import patch
from pathlib import Path

from pydantic import ValidationError

import backend.app.features.role_matching.schemas as role_schemas
from backend.app.features.role_matching.recommendation import (
    Candidate,
    _effective_domain_overlap,
    _mmr_select,
    _role_similarity,
    recommend,
)
from backend.app.features.role_matching.schemas import (
    CareerIdentity,
    RecommendationBucket,
    RoleMatchRequest,
    UserCareerProfile,
    UserCertification,
    UserEducation,
    UserExperience,
    UserProject,
)
from backend.app.features.role_matching.service import (
    _apply_role_summaries,
    _clean_role_card_summary,
    _cert_overlap,
    _match_roles_sync,
    _role_required_skills,
    build_capability_text,
    build_identity_text,
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

        self.assertEqual(request.profile.career_identity.title, "Robust Systems Architect")
        with self.assertRaises(ValidationError):
            RoleMatchRequest(profile=sample_profile(), include_debug=True)

    def test_role_match_request_defaults_to_nine_results(self) -> None:
        request = RoleMatchRequest(profile=sample_profile())

        self.assertEqual(9, request.top_k)
        with self.assertRaises(ValidationError):
            RoleMatchRequest(profile=sample_profile(), top_k=10)

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
                    bucket=RecommendationBucket.READY_NOW,
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
                        "matching_score": 95,
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

    def test_matching_score_reports_the_normalized_score(self) -> None:
        roles = [
            role_schemas.RoleMatch(
                role_id="ready",
                job_title="Ready Role",
                final_score=0.42,
                bucket=RecommendationBucket.READY_NOW,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
            role_schemas.RoleMatch(
                role_id="next",
                job_title="Next Role",
                final_score=0.42,
                bucket=RecommendationBucket.NEXT_STEP,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
            role_schemas.RoleMatch(
                role_id="stretch",
                job_title="Stretch Role",
                final_score=0.42,
                bucket=RecommendationBucket.ASPIRATIONAL,
                signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
            ),
        ]

        scores = [
            role_schemas.CareerResultV1.from_role_match(role).matching_score
            for role in roles
        ]

        self.assertEqual([42, 42, 42], scores)


class RoleCardSummaryGenerationTests(unittest.TestCase):
    def test_generated_card_summaries_describe_roles_not_user_fit(self) -> None:
        role = role_schemas.RoleMatch(
            role_id=123,
            job_title="Business Intelligence Analyst",
            description="Analyzes data to provide insights and support business decision-making.",
            final_score=0.72,
            bucket=RecommendationBucket.READY_NOW,
            salary="EUR 67k",
            esco_title="Business analyst",
            matched_skills=["python", "sql", "tableau"],
            missing_skills=["business acumen"],
            matched_domains=["data_analytics"],
            matched_certifications=["Google Data Analytics Certificate"],
            signal_breakdown=role_schemas.RoleMatchSignalBreakdown(),
        )
        response = role_schemas.RoleMatchResponse(
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
                            "Turns business data into dashboards leaders can use. "
                            "Helps teams spot trends and act faster."
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

        self.assertIn("one or two present-tense sentences", system_prompt)
        self.assertIn("concrete day-to-day work", system_prompt)
        self.assertIn("Avoid repetitive generic openers", system_prompt)
        self.assertIn("Do not mention the user", system_prompt)
        self.assertIn("Do not list skills", system_prompt)
        self.assertNotIn("profile", payload)
        self.assertEqual(
            {"role_id", "title", "esco_title", "description"},
            set(payload_role),
        )
        self.assertEqual(
            "Turns business data into dashboards leaders can use. Helps teams spot trends and act faster.",
            role.description,
        )

    def test_role_card_summary_cleaner_keeps_two_sentences_with_a_short_cap(self) -> None:
        summary = _clean_role_card_summary(
            " Keeps workplace technology running by diagnosing device issues.  "
            "Guides users through fixes and escalates harder problems. "
            "This third sentence should not appear."
        )

        self.assertEqual(
            "Keeps workplace technology running by diagnosing device issues. "
            "Guides users through fixes and escalates harder problems.",
            summary,
        )
        self.assertLessEqual(len(summary or ""), 180)
        self.assertNotIn("third sentence", summary or "")


class CleanProfileTextBuilderTests(unittest.TestCase):
    def test_capability_text_contains_profile_evidence_sections(self) -> None:
        text = build_capability_text(sample_profile())

        self.assertIn("Experience 1: Senior Backend Developer", text)
        self.assertIn("Education 1: MSc Computer Science", text)
        self.assertIn("Skills: Python, RESTful APIs, PostgreSQL", text)
        self.assertIn("Certification 1: AWS Certified Developer - Associate", text)
        self.assertIn("Project 1: Payment microservice migration", text)

    def test_intent_text_contains_potential_direction_and_interests_only(self) -> None:
        profile = sample_profile().model_copy(
            update={"potential_direction": "Could grow into a platform reliability specialization."}
        )
        text = build_intent_text(profile)

        self.assertIn("Potential direction: Could grow into a platform reliability specialization.", text)
        self.assertIn("Interests: Artificial Intelligence, Big Data scale", text)
        self.assertNotIn("Career identity", text)
        self.assertNotIn("Robust Systems Architect", text)
        self.assertNotIn("Payment microservice migration", text)
        self.assertNotIn("AWS Certified Developer", text)

    def test_identity_text_contains_career_identity_only(self) -> None:
        text = build_identity_text(sample_profile())

        self.assertIn("Career identity: Robust Systems Architect", text)
        self.assertIn("Strong backend, cloud infrastructure", text)
        self.assertNotIn("Interests", text)
        self.assertNotIn("Payment microservice migration", text)


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

    def test_default_skill_aliases_keep_distinct_tools_and_concepts(self) -> None:
        normalized = normalize_user_skills(
            ["APIs", "Spring", "Figma", "UX", "pandas", "analytics", "data"],
            {},
        )

        self.assertEqual(
            [
                "rest apis",
                "spring framework",
                "figma",
                "ui ux design",
                "pandas",
                "data analysis",
                "data",
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


class RoleRequiredSkillsSourceTests(unittest.TestCase):
    def test_prefers_sort_skills_over_role_skills_table_and_raw_skills(self) -> None:
        row = {
            "role_id": "1",
            "raw_skills": "Databases",
            "sort_skills": [{"skill": "PostgreSQL", "domain": "Databases", "score": 0.9}],
        }

        required = _role_required_skills(row, role_skills={"1": ["databases"]}, alias_map={})

        self.assertEqual(required, ["postgresql"])

    def test_falls_back_to_role_skills_table_when_sort_skills_missing(self) -> None:
        row = {"role_id": "1", "raw_skills": "Databases", "sort_skills": None}

        required = _role_required_skills(row, role_skills={"1": ["postgresql"]}, alias_map={})

        self.assertEqual(required, ["postgresql"])

    def test_falls_back_to_raw_skills_when_neither_sort_skills_nor_table_available(self) -> None:
        row = {"role_id": "1", "raw_skills": "PostgreSQL, Docker", "sort_skills": []}

        required = _role_required_skills(row, role_skills={}, alias_map={})

        self.assertEqual(required, ["postgresql", "docker"])


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
            identity_vector_similarity=0.60,
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
            identity_vector_similarity=0.20,
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

        buckets = recommend([unrelated, backend], top_k=2)

        self.assertEqual(buckets.ready_now[0].role_id, 1)
        self.assertEqual(buckets.ready_now[0].bucket, RecommendationBucket.READY_NOW)
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
                    capability_vector_similarity=0.75,
                    intent_vector_similarity=0.6,
                    identity_vector_similarity=0.65,
                    skill_overlap=0.75,
                    domain_overlap=0.1,
                    seniority_fit=0.9,
                    seniority_gap="match",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"next-{i}",
                    job_title=f"Next {i}",
                    capability_vector_similarity=0.55,
                    intent_vector_similarity=0.55,
                    identity_vector_similarity=0.55,
                    skill_overlap=0.45,
                    domain_overlap=0.85,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"asp-{i}",
                    job_title=f"Aspirational {i}",
                    capability_vector_similarity=0.35,
                    intent_vector_similarity=0.75,
                    identity_vector_similarity=0.70,
                    skill_overlap=0.1,
                    domain_overlap=0.2,
                    seniority_fit=0.6,
                    seniority_gap="unknown",
                )
            )

        buckets = recommend(candidates, top_k=6)

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
                    capability_vector_similarity=0.55,
                    intent_vector_similarity=0.55,
                    identity_vector_similarity=0.55,
                    skill_overlap=0.45,
                    domain_overlap=0.85,
                    seniority_fit=0.7,
                    seniority_gap="unknown",
                )
            )
            candidates.append(
                Candidate(
                    role_id=f"asp-{i}",
                    job_title=f"Aspirational {i}",
                    capability_vector_similarity=0.35,
                    intent_vector_similarity=0.75,
                    identity_vector_similarity=0.70,
                    skill_overlap=0.1,
                    domain_overlap=0.2,
                    seniority_fit=0.6,
                    seniority_gap="unknown",
                )
            )

        buckets = recommend(candidates, top_k=6)

        self.assertEqual(0, len(buckets.ready_now))
        self.assertEqual(3, len(buckets.next_step))
        self.assertEqual(3, len(buckets.aspirational))

    def test_default_match_path_returns_nine_unique_roles(self) -> None:
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
                        "domain_tags": "backend",
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
            def encode_queries(self, texts: list[str]) -> list[list[float]]:
                return [[0.1] for _ in texts]

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
                include_debug=False,
            )

        roles = [
            *response.buckets.ready_now,
            *response.buckets.next_step,
            *response.buckets.aspirational,
        ]
        self.assertEqual(9, len(roles))
        self.assertEqual(9, len({role.role_id for role in roles}))
    def test_certification_overlap_is_display_only_and_does_not_affect_score(self) -> None:
        """Certification is no longer a scoring dimension (dropped in favor of
        identity_vector_similarity) - matched_certifications still displays,
        but two otherwise-identical candidates score identically regardless
        of certification_overlap."""
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

        buckets = recommend([without_cert, with_cert], top_k=2)
        all_roles = [*buckets.ready_now, *buckets.next_step, *buckets.aspirational]

        scores = {role.role_id: role.final_score for role in all_roles}
        self.assertEqual(scores[1], scores[2])
        matched_certs = {role.role_id: role.matched_certifications for role in all_roles}
        self.assertEqual(matched_certs[2], ["AWS Certified Developer - Associate"])
        self.assertEqual(matched_certs[1], [])

    def test_identity_vector_similarity_is_a_weighted_scoring_dimension(self) -> None:
        low_identity = Candidate(
            role_id="low",
            job_title="Low identity match",
            capability_vector_similarity=0.5,
            intent_vector_similarity=0.5,
            identity_vector_similarity=0.0,
            seniority_fit=0.5,
        )
        high_identity = Candidate(
            role_id="high",
            job_title="High identity match",
            capability_vector_similarity=0.5,
            intent_vector_similarity=0.5,
            identity_vector_similarity=1.0,
            seniority_fit=0.5,
        )

        buckets = recommend([low_identity, high_identity], top_k=2)

        all_roles = [*buckets.ready_now, *buckets.next_step, *buckets.aspirational]
        scores = {role.role_id: role.final_score for role in all_roles}
        self.assertGreater(scores["high"], scores["low"])
        self.assertAlmostEqual(
            scores["high"] - scores["low"],
            role_schemas.DEFAULT_WEIGHTS.identity_vector_similarity,
            places=4,
        )

    def test_ai_interest_can_lift_a_stretch_role_without_overpowering_skill_mismatch(self) -> None:
        ready_backend = Candidate(
            role_id=1,
            job_title="Backend Engineer",
            capability_vector_similarity=0.72,
            intent_vector_similarity=0.45,
            identity_vector_similarity=0.60,
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
            identity_vector_similarity=0.60,
            skill_overlap=0.15,
            domain_overlap=1.0,
            certification_overlap=0.0,
            seniority_fit=0.7,
            seniority_gap="unknown",
        )

        buckets = recommend([ai_stretch, ready_backend], top_k=2)

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

        buckets = recommend([intent_only], top_k=1)

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

        # java_architect's raw domain_overlap (1.0) is double java_developer's (0.50), but
        # its thinner skill_overlap (0.25 vs 0.40) drops it into the damping bracket that caps
        # effective domain at 0.50 - so the two end up with the *same* effective domain, and
        # java_developer's stronger skill signal should make it score higher overall.
        self.assertEqual(_effective_domain_overlap(java_developer), 0.50)
        self.assertEqual(_effective_domain_overlap(java_architect), 0.50)

        buckets = recommend([java_architect, java_developer], top_k=2)
        combined = [*buckets.ready_now, *buckets.next_step, *buckets.aspirational]
        self.assertGreater(
            next(r.final_score for r in combined if r.role_id == 1),
            next(r.final_score for r in combined if r.role_id == 2),
        )

    def test_senior_profile_is_not_penalized_for_senior_role(self) -> None:
        self.assertEqual(
            infer_seniority_gap("Senior Backend Developer", "Senior Backend Engineer"),
            ("match", 1.0),
        )

    def test_student_identity_is_a_stretch_for_senior_roles(self) -> None:
        gap, fit = infer_seniority_gap("Frontend student", "Senior Front End Developer")

        self.assertEqual("stretch", gap)
        self.assertLess(fit, 0.5)

    def test_role_similarity_is_jaccard_over_skills_and_domains(self) -> None:
        a = Candidate(
            role_id="a", job_title="A", required_skills=["python", "django"], domain_tags=["backend"]
        )
        b = Candidate(
            role_id="b", job_title="B", required_skills=["python", "django"], domain_tags=["backend"]
        )
        c = Candidate(
            role_id="c", job_title="C", required_skills=["rust", "firmware"], domain_tags=["embedded"]
        )
        empty = Candidate(role_id="e", job_title="E")

        self.assertEqual(_role_similarity(a, b), 1.0)
        self.assertEqual(_role_similarity(a, c), 0.0)
        self.assertEqual(_role_similarity(a, empty), 0.0)

    def test_mmr_select_prefers_diversity_over_a_near_duplicate_runner_up(self) -> None:
        best = Candidate(
            role_id="best",
            job_title="Best",
            required_skills=["python", "django", "postgresql", "docker"],
        )
        best.final_score = 0.90
        near_duplicate = Candidate(
            role_id="near_duplicate",
            job_title="Near Duplicate",
            required_skills=["python", "django", "postgresql", "redis"],
        )
        near_duplicate.final_score = 0.88
        distinct = Candidate(
            role_id="distinct", job_title="Distinct", required_skills=["rust", "embedded", "firmware"]
        )
        distinct.final_score = 0.70

        selected = _mmr_select([near_duplicate, best, distinct], k=2)

        self.assertEqual([c.role_id for c in selected], ["best", "distinct"])

    def test_mmr_select_falls_back_to_relevance_when_pool_fits_exactly(self) -> None:
        only = Candidate(role_id="only", job_title="Only")
        only.final_score = 0.5

        self.assertEqual(_mmr_select([only], k=3), [only])
        self.assertEqual(_mmr_select([], k=3), [])
        self.assertEqual(_mmr_select([only], k=0), [])

    def test_aspirational_bucket_is_mmr_reranked_for_diversity(self) -> None:
        # Thin skill evidence keeps all three candidates aspirational; MMR
        # should still favor a distinct option over a near-duplicate.
        base = dict(seniority_fit=0.3)
        best = Candidate(
            role_id="asp-best",
            job_title="Aspirational Best",
            required_skills=["python", "tensorflow", "pytorch"],
            domain_tags=["ml_ai"],
            capability_vector_similarity=0.15,
            intent_vector_similarity=0.80,
            skill_overlap=0.10,
            domain_overlap=0.05,
            **base,
        )
        near_duplicate = Candidate(
            role_id="asp-near-duplicate",
            job_title="Aspirational Near Duplicate",
            required_skills=["python", "tensorflow", "keras"],
            domain_tags=["ml_ai"],
            capability_vector_similarity=0.13,
            intent_vector_similarity=0.78,
            skill_overlap=0.08,
            domain_overlap=0.05,
            **base,
        )
        distinct = Candidate(
            role_id="asp-distinct",
            job_title="Aspirational Distinct",
            required_skills=["rust", "embedded", "firmware"],
            domain_tags=["embedded_iot"],
            capability_vector_similarity=0.10,
            intent_vector_similarity=0.65,
            skill_overlap=0.05,
            domain_overlap=0.05,
            **base,
        )

        buckets = recommend([near_duplicate, best, distinct], top_k=2)

        self.assertEqual(
            [role.role_id for role in buckets.aspirational],
            ["asp-best", "asp-distinct"],
        )

    def test_leadership_role_is_not_ready_without_seniority_evidence(self) -> None:
        gap, fit = infer_seniority_gap("IT Support Beginner", "Chief Technology Officer")
        candidate = Candidate(
            role_id="cto",
            job_title="Chief Technology Officer",
            capability_vector_similarity=0.80,
            intent_vector_similarity=0.70,
            identity_vector_similarity=0.70,
            skill_overlap=0.75,
            domain_overlap=0.50,
            seniority_gap=gap,
            seniority_fit=fit,
        )

        buckets = recommend([candidate], top_k=1)

        self.assertEqual([], buckets.ready_now)
        self.assertEqual("cto", buckets.aspirational[0].role_id)

    def test_balanced_selection_deduplicates_titles_across_buckets(self) -> None:
        candidates = [
            Candidate(
                role_id="ui-ready",
                job_title="UI Designer",
                capability_vector_similarity=0.75,
                intent_vector_similarity=0.60,
                identity_vector_similarity=0.65,
                skill_overlap=0.75,
                domain_overlap=0.50,
                seniority_fit=0.70,
            ),
            Candidate(
                role_id="ui-next",
                job_title="UI Designer",
                capability_vector_similarity=0.55,
                intent_vector_similarity=0.60,
                identity_vector_similarity=0.55,
                skill_overlap=0.40,
                domain_overlap=0.80,
                seniority_fit=0.70,
            ),
            Candidate(
                role_id="web-next",
                job_title="Web Designer",
                capability_vector_similarity=0.55,
                intent_vector_similarity=0.60,
                identity_vector_similarity=0.55,
                skill_overlap=0.40,
                domain_overlap=0.80,
                seniority_fit=0.70,
            ),
            Candidate(
                role_id="cloud-asp",
                job_title="Cloud Architect",
                capability_vector_similarity=0.35,
                intent_vector_similarity=0.80,
                identity_vector_similarity=0.70,
                skill_overlap=0.10,
                domain_overlap=0.20,
                seniority_fit=0.30,
            ),
            Candidate(
                role_id="data-asp",
                job_title="Data Scientist",
                capability_vector_similarity=0.35,
                intent_vector_similarity=0.80,
                identity_vector_similarity=0.70,
                skill_overlap=0.10,
                domain_overlap=0.20,
                seniority_fit=0.30,
            ),
        ]

        buckets = recommend(candidates, top_k=4)
        roles = [
            *buckets.ready_now,
            *buckets.next_step,
            *buckets.aspirational,
        ]
        normalized_titles = [role.job_title.casefold() for role in roles]

        self.assertEqual(4, len(roles))
        self.assertEqual(len(normalized_titles), len(set(normalized_titles)))

if __name__ == "__main__":
    unittest.main()
