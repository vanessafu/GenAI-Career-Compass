import importlib.util
import sys
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "map_roles_to_esco.py"
spec = importlib.util.spec_from_file_location("map_roles_to_esco", SCRIPT_PATH)
map_roles_to_esco = importlib.util.module_from_spec(spec)
sys.modules["map_roles_to_esco"] = map_roles_to_esco
spec.loader.exec_module(map_roles_to_esco)


class MapRolesToEscoTests(unittest.TestCase):
    def test_cosine_similarity_handles_basic_vectors_and_zero_vectors(self):
        self.assertAlmostEqual(
            map_roles_to_esco.cosine_similarity([1.0, 0.0], [1.0, 0.0]),
            1.0,
        )
        self.assertAlmostEqual(
            map_roles_to_esco.cosine_similarity([1.0, 0.0], [0.0, 1.0]),
            0.0,
        )
        self.assertEqual(map_roles_to_esco.cosine_similarity([0.0], [1.0]), 0.0)

    def test_role_profile_includes_title_description_domain_skills_and_certifications(self):
        role = map_roles_to_esco.CareerRoleProfile(
            role_id="10",
            job_title="DevOps Engineer",
            job_description="Builds deployment platforms.",
            raw_skills="Docker, Kubernetes, Terraform",
            raw_certifications="AWS Certified DevOps Engineer",
            domain_tags="devops,cloud",
            normalized_skills=["docker", "kubernetes", "docker", ""],
            raw_skill_names=["Docker", "K8s"],
            certifications=["CKA", "CKA"],
        )

        profile = map_roles_to_esco.build_career_role_profile_text(role)

        self.assertIn("Role title: DevOps Engineer", profile)
        self.assertIn("Description: Builds deployment platforms.", profile)
        self.assertIn("Domain tags: devops,cloud", profile)
        self.assertIn("Skills: docker, kubernetes", profile)
        self.assertIn("Certifications: CKA", profile)
        self.assertNotIn("AWS Certified DevOps Engineer", profile)

    def test_role_profile_falls_back_to_raw_skills_and_certifications(self):
        role = map_roles_to_esco.CareerRoleProfile(
            role_id="11",
            job_title="Support Analyst",
            job_description="",
            raw_skills="Windows, Troubleshooting",
            raw_certifications="ITIL Foundation, CompTIA A+",
            domain_tags="support",
            normalized_skills=[],
            raw_skill_names=["Windows", "Troubleshooting"],
            certifications=[],
        )

        profile = map_roles_to_esco.build_career_role_profile_text(role)

        self.assertIn("Skills: Windows, Troubleshooting", profile)
        self.assertIn("Certifications: ITIL Foundation, CompTIA A+", profile)

    def test_esco_profile_separates_essential_optional_and_other_skills(self):
        occupation = map_roles_to_esco.EscoOccupationProfile(
            esco_uri="uri:occupation",
            isco_code="2522",
            name="Systems administrator",
            definition="Maintains ICT systems.",
            skill_links=[
                map_roles_to_esco.EscoSkillLink(
                    preferred_label="manage backups",
                    relation_type="optional",
                ),
                map_roles_to_esco.EscoSkillLink(
                    preferred_label="administer ICT system",
                    relation_type="essential",
                ),
                map_roles_to_esco.EscoSkillLink(
                    preferred_label="write reports",
                    relation_type="",
                ),
                map_roles_to_esco.EscoSkillLink(
                    preferred_label="",
                    relation_type="essential",
                ),
            ],
        )

        profile = map_roles_to_esco.build_esco_occupation_profile_text(occupation)

        self.assertIn("ESCO occupation: Systems administrator", profile)
        self.assertIn("Definition: Maintains ICT systems.", profile)
        self.assertLess(
            profile.index("Essential skills: administer ICT system"),
            profile.index("Optional skills: manage backups"),
        )
        self.assertIn("Other linked skills: write reports", profile)

    def test_final_score_combines_semantic_skill_overlap_and_domain_hint(self):
        self.assertAlmostEqual(
            map_roles_to_esco.calculate_final_mapping_score(
                semantic_score=0.8,
                skill_overlap_score=0.5,
                domain_hint_score=1.0,
            ),
            0.75,
        )

    def test_skill_overlap_uses_exact_esco_uri_links_when_labels_differ(self):
        role = map_roles_to_esco.CareerRoleProfile(
            role_id="20",
            job_title="Python Developer",
            job_description="",
            raw_skills="",
            raw_certifications="",
            domain_tags="software_engineering",
            normalized_skills=["python", "linux"],
            raw_skill_names=[],
            certifications=[],
            normalized_skill_esco_uris={
                "python": ["uri:skill:python"],
                "linux": ["uri:skill:linux"],
            },
        )
        occupation = map_roles_to_esco.EscoOccupationProfile(
            esco_uri="uri:occupation",
            isco_code="2512",
            name="Software developer",
            definition="",
            skill_links=[
                map_roles_to_esco.EscoSkillLink(
                    esco_skill_uri="uri:skill:python",
                    preferred_label="Python (computer programming)",
                    relation_type="essential",
                )
            ],
        )

        score, overlap_count, role_skill_count = map_roles_to_esco.skill_overlap_details(
            role,
            occupation,
        )

        self.assertEqual(overlap_count, 1)
        self.assertEqual(role_skill_count, 2)
        self.assertEqual(score, 0.5)

    def test_mapping_status_thresholds_are_calibrated_to_observed_embedding_scores(self):
        self.assertEqual(
            map_roles_to_esco.classify_mapping_status(0.56, 0.50),
            "auto_accepted",
        )
        self.assertEqual(
            map_roles_to_esco.classify_mapping_status(0.56, 0.53),
            "needs_review",
        )
        self.assertEqual(
            map_roles_to_esco.classify_mapping_status(0.45, 0.20),
            "needs_review",
        )
        self.assertEqual(
            map_roles_to_esco.classify_mapping_status(0.42, 0.10),
            "low_confidence",
        )

    def test_manual_override_wins_over_automatic_mapping(self):
        role = map_roles_to_esco.CareerRoleProfile(
            role_id="42",
            job_title="Cloud Engineer",
            job_description="",
            raw_skills="",
            raw_certifications="",
            domain_tags="cloud",
            normalized_skills=[],
            raw_skill_names=[],
            certifications=[],
        )
        automatic = [
            map_roles_to_esco.CandidateScore(
                esco_uri="uri:auto",
                esco_title="Automatic result",
                isco_code="2521",
                final_score=0.99,
                semantic_score=0.99,
                skill_overlap_score=0.0,
                domain_hint_score=0.0,
                brief_reason="Automatic top match.",
            )
        ]
        override = map_roles_to_esco.ManualOverride(
            role_id="42",
            job_title="Cloud Engineer",
            esco_uri="uri:manual",
            esco_title="Manual result",
            notes="Reviewed by instructor.",
        )
        occupations_by_uri = {
            "uri:manual": map_roles_to_esco.EscoOccupationProfile(
                esco_uri="uri:manual",
                isco_code="2522",
                name="Manual result",
                definition="",
                skill_links=[],
            )
        }

        decision = map_roles_to_esco.choose_mapping_decision(
            role,
            automatic,
            override,
            occupations_by_uri,
        )

        self.assertTrue(decision.manual_override)
        self.assertEqual(decision.mapping_status, "manual_override")
        self.assertEqual(decision.selected.esco_uri, "uri:manual")
        self.assertEqual(decision.notes, "Reviewed by instructor.")

    def test_mapping_payload_keeps_database_row_compact(self):
        role = map_roles_to_esco.CareerRoleProfile(
            role_id="42",
            job_title="Cloud Engineer",
            job_description="",
            raw_skills="",
            raw_certifications="",
            domain_tags="cloud",
        )
        selected = map_roles_to_esco.CandidateScore(
            esco_uri="uri:occupation",
            esco_title="Cloud engineer",
            isco_code="2522",
            final_score=0.7654321,
            semantic_score=0.8,
            skill_overlap_score=0.5,
            domain_hint_score=1.0,
            brief_reason="Strong match.",
        )
        decision = map_roles_to_esco.MappingDecision(
            role=role,
            selected=selected,
            top_candidates=[selected],
            mapping_status="auto_accepted",
            manual_override=False,
            margin_to_second=None,
        )

        payload = map_roles_to_esco.mapping_payload(decision)

        self.assertEqual(
            payload,
            {
                "role_id": "42",
                "esco_uri": "uri:occupation",
                "esco_title": "Cloud engineer",
                "match_score": 0.765432,
            },
        )

    def test_openai_error_format_redacts_key_like_values(self):
        body = (
            '{"error":{"message":"Incorrect API key provided: '
            'sk-proj-abc123MASKEDxyz. Check your key."}}'
        )

        message = map_roles_to_esco.format_openai_error(body)

        self.assertNotIn("sk-proj-", message)
        self.assertNotIn("abc123MASKEDxyz", message)
        self.assertIn("[redacted]", message)

    def test_client_resolves_certifications_through_mapping_table(self):
        test_case = self

        class FakeClient(map_roles_to_esco.SupabaseRestClient):
            def __init__(self):
                self.schema = map_roles_to_esco.DEFAULT_SCHEMA

            def _request(
                self,
                method,
                table,
                query=None,
                payload=None,
                prefer=None,
                extra_headers=None,
            ):
                test_case.assertEqual(method, "GET")
                if table == self.schema.certifications_mapping_table:
                    return [
                        {"role_id": 10, "certification_id": 100},
                        {"role_id": 10, "certification_id": 101},
                        {"role_id": 11, "certification_id": 100},
                    ]
                if table == self.schema.certifications_table:
                    return [
                        {
                            "certification_id": 100,
                            "certification_name": "CKA",
                        },
                        {
                            "certification_id": 101,
                            "certification_name": "AWS Certified Developer",
                        },
                    ]
                raise AssertionError(f"Unexpected table: {table}")

        certifications = FakeClient().list_certifications_by_role_id(["10", "11"])

        self.assertEqual(
            certifications,
            {
                "10": ["CKA", "AWS Certified Developer"],
                "11": ["CKA"],
            },
        )


if __name__ == "__main__":
    unittest.main()
