from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from metrics.common import evaluate_matching_roles
from backend.app.features.role_matching.schemas import (
    CareerIdentity,
    RoleMatchRequest,
    UserCareerProfile,
    UserCertification,
    UserExperience,
)
from backend.app.features.role_matching.service import (
    build_capability_text,
    build_intent_text,
    infer_seniority_gap,
    match_roles_for_profile,
    normalize_user_certifications,
    normalize_user_skills,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def mock_frontend_profiles() -> dict[str, UserCareerProfile]:
    return {
        "frontend_student": UserCareerProfile(
            career_identity=CareerIdentity(title="Frontend student"),
            skills=["React", "JavaScript", "HTML", "CSS", "Git"],
            interests=["cloud", "ux", "web development"],
        ),
        "python_data_student": UserCareerProfile(
            career_identity=CareerIdentity(title="Python/data student"),
            skills=["Python", "SQL", "pandas", "statistics", "data visualization"],
            certifications=[
                UserCertification(name="Google Data Analytics Certificate"),
            ],
            interests=["AI", "analytics", "data"],
        ),
        "it_support_beginner": UserCareerProfile(
            career_identity=CareerIdentity(title="IT support beginner"),
            skills=["Windows", "Linux", "networking", "troubleshooting", "Active Directory"],
            certifications=[UserCertification(name="CompTIA A+")],
            interests=["cybersecurity", "cloud"],
        ),
        "backend_developer": UserCareerProfile(
            career_identity=CareerIdentity(title="Backend developer"),
            experience=[UserExperience(role="Backend Developer")],
            skills=["Java", "SQL", "APIs", "Git", "Docker", "Spring"],
            certifications=[
                UserCertification(name="Oracle Certified Associate Java Programmer"),
            ],
            interests=["DevOps", "architecture", "cloud"],
        ),
        "design_frontend": UserCareerProfile(
            career_identity=CareerIdentity(title="Design/frontend profile"),
            skills=[
                "Figma",
                "HTML",
                "CSS",
                "JavaScript",
                "accessibility",
                "responsive design",
            ],
            interests=["UX", "frontend", "design"],
        ),
    }


class MockProfileEvaluationFixturesTests(unittest.TestCase):
    def test_mock_frontend_profiles_match_public_schema(self) -> None:
        for name, profile in mock_frontend_profiles().items():
            with self.subTest(name=name):
                request = RoleMatchRequest(profile=profile, top_k=9)
                self.assertEqual(profile, request.profile)

    def test_mock_frontend_profiles_build_split_query_texts(self) -> None:
        for name, profile in mock_frontend_profiles().items():
            with self.subTest(name=name):
                capability_text = build_capability_text(profile)
                intent_text = build_intent_text(profile)

                self.assertTrue(capability_text)
                self.assertTrue(intent_text)
                self.assertNotIn("Interests:", capability_text)
                self.assertNotIn("Skills:", intent_text)
                self.assertNotIn("possible", intent_text.casefold())

    def test_mock_profile_aliases_cover_known_evaluation_gaps(self) -> None:
        backend_skills = normalize_user_skills(
            mock_frontend_profiles()["backend_developer"].skills,
            {},
        )
        design_skills = normalize_user_skills(
            mock_frontend_profiles()["design_frontend"].skills,
            {},
        )
        data_certs = normalize_user_certifications(
            cert.name for cert in mock_frontend_profiles()["python_data_student"].certifications
        )
        backend_certs = normalize_user_certifications(
            cert.name for cert in mock_frontend_profiles()["backend_developer"].certifications
        )

        self.assertIn("rest apis", backend_skills)
        self.assertIn("spring framework", backend_skills)
        self.assertIn("figma", design_skills)
        self.assertIn("web accessibility guidelines", design_skills)
        self.assertIn("google data analytics professional certificate", data_certs)
        self.assertIn("oracle certified associate oca java", backend_certs)

    def test_sparse_student_and_beginner_profiles_infer_junior_seniority(self) -> None:
        frontend_gap, frontend_fit = infer_seniority_gap(
            "Frontend student",
            "Senior Front End Developer",
        )
        support_gap, support_fit = infer_seniority_gap(
            "IT support beginner",
            "IT Apprentice",
        )

        self.assertEqual("stretch", frontend_gap)
        self.assertLess(frontend_fit, 0.5)
        self.assertEqual(("match", 1.0), (support_gap, support_fit))


@unittest.skipUnless(
    os.getenv("RUN_LIVE_MATCHING_EVAL") == "1",
    "Set RUN_LIVE_MATCHING_EVAL=1 to run against live embeddings and Supabase data.",
)
class LiveMockProfileEvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_profiles_surface_expected_role_families(self) -> None:
        fixture = json.loads(
            (REPO_ROOT / "metrics" / "fixtures" / "matching_profiles.json").read_text(
                encoding="utf-8"
            )
        )
        judged_roles = {
            profile["name"]: profile["judged_roles"]
            for profile in fixture["profiles"]
        }

        for name, profile in mock_frontend_profiles().items():
            with self.subTest(name=name):
                response = await match_roles_for_profile(profile, top_k=9, include_debug=True)
                roles = [
                    {
                        "role_id": str(role.role_id),
                        "title": role.job_title,
                        "bucket": role.bucket.value,
                    }
                    for role in [
                        *response.buckets.ready_now,
                        *response.buckets.next_step,
                        *response.buckets.aspirational,
                    ]
                ]
                metrics = evaluate_matching_roles(roles, judged_roles[name])

                self.assertGreater(metrics["ndcg_at_9"], 0.0, roles)


if __name__ == "__main__":
    unittest.main()
