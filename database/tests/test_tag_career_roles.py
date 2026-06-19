import csv
import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "tag_career_roles.py"
spec = importlib.util.spec_from_file_location("tag_career_roles", SCRIPT_PATH)
tag_career_roles = importlib.util.module_from_spec(spec)
sys.modules["tag_career_roles"] = tag_career_roles
spec.loader.exec_module(tag_career_roles)


def role(
    role_id,
    job_title,
    job_description="",
    raw_skills="",
    raw_certifications="",
    domain_tags=None,
    role_skills=None,
):
    return tag_career_roles.RoleRecord(
        role_id=role_id,
        job_title=job_title,
        job_description=job_description,
        raw_skills=raw_skills,
        raw_certifications=raw_certifications,
        domain_tags=domain_tags,
        role_skills=role_skills or [],
    )


class TagCareerRolesTests(unittest.TestCase):
    def classify(self, item):
        taxonomy = tag_career_roles.build_taxonomy([item], discover_new_tags=False)
        return tag_career_roles.classify_role(item, taxonomy)

    def test_frontend_developer_gets_frontend(self):
        result = self.classify(
            role(1, "React Frontend Developer", raw_skills="React, TypeScript, CSS")
        )

        self.assertIn("frontend", result.assigned_tags)

    def test_devops_cloud_role_gets_devops_and_cloud(self):
        result = self.classify(
            role(
                2,
                "DevOps Engineer",
                raw_skills="AWS, Docker, Kubernetes, CI/CD",
            )
        )

        self.assertIn("devops", result.assigned_tags)
        self.assertIn("cloud", result.assigned_tags)

    def test_data_analyst_gets_data_analytics(self):
        result = self.classify(
            role(3, "Data Analyst", raw_skills="SQL, Tableau, Power BI")
        )

        self.assertEqual(result.assigned_tags[0], "data_analytics")

    def test_machine_learning_engineer_gets_ai_ml(self):
        result = self.classify(
            role(
                4,
                "Machine Learning Engineer",
                raw_skills="PyTorch, TensorFlow, NLP",
            )
        )

        self.assertIn("ai_ml", result.assigned_tags)

    def test_security_analyst_gets_cybersecurity(self):
        result = self.classify(
            role(
                5,
                "Security Analyst",
                raw_skills="SIEM, firewall, incident response",
            )
        )

        self.assertIn("cybersecurity", result.assigned_tags)

    def test_it_support_specialist_gets_support(self):
        result = self.classify(
            role(
                6,
                "IT Support Specialist",
                raw_skills="troubleshooting, help desk, Windows",
            )
        )

        self.assertIn("support", result.assigned_tags)

    def test_repeated_erp_crm_cluster_auto_adds_and_uses_erp_crm(self):
        roles = [
            role(
                10,
                "SAP ERP Consultant",
                job_description="Implements enterprise resource planning systems.",
                raw_skills="SAP, ERP, S/4HANA",
            ),
            role(
                11,
                "CRM Administrator",
                job_description="Maintains customer relationship management workflows.",
                raw_skills="Salesforce, CRM",
            ),
            role(
                12,
                "ERP CRM Business Systems Analyst",
                raw_skills="SAP, Salesforce, Microsoft Dynamics 365",
            ),
        ]

        taxonomy = tag_career_roles.build_taxonomy(roles, discover_new_tags=True)
        result = tag_career_roles.classify_role(roles[0], taxonomy)

        self.assertIn("erp_crm", taxonomy)
        self.assertEqual(taxonomy["erp_crm"].status, "auto_added")
        self.assertIn("erp_crm", result.assigned_tags)

    def test_repeated_documentation_cluster_auto_adds_technical_writing(self):
        roles = [
            role(20, "Technical Writer", raw_skills="API documentation, manuals"),
            role(21, "Documentation Specialist", raw_skills="knowledge base, docs"),
            role(22, "Content Writer for Developer Tools", raw_skills="developer documentation"),
        ]

        taxonomy = tag_career_roles.build_taxonomy(roles, discover_new_tags=True)
        result = tag_career_roles.classify_role(roles[0], taxonomy)

        self.assertIn("technical_writing", taxonomy)
        self.assertEqual(taxonomy["technical_writing"].status, "auto_added")
        self.assertIn("technical_writing", result.assigned_tags)

    def test_weak_new_tag_evidence_needs_review_and_is_not_applied(self):
        item = role(
            30,
            "SAP ERP Consultant",
            job_description="Implements enterprise resource planning systems.",
            raw_skills="SAP, ERP",
        )

        taxonomy = tag_career_roles.build_taxonomy([item], discover_new_tags=True)
        result = tag_career_roles.classify_role(item, taxonomy)

        self.assertEqual(taxonomy["erp_crm"].status, "needs_review")
        self.assertNotIn("erp_crm", result.assigned_tags)

    def test_user_approved_discovered_tags_auto_apply_with_single_role_evidence(self):
        roles = [
            role(31, "Robotics Engineer", raw_skills="ROS, robotics, autonomous systems"),
            role(32, "AR VR Developer", raw_skills="Unity, augmented reality, virtual reality"),
            role(33, "Tech Sales Engineer", raw_skills="pre-sales, technical sales"),
        ]

        taxonomy = tag_career_roles.build_taxonomy(roles, discover_new_tags=True)

        for tag_slug, item in [
            ("robotics", roles[0]),
            ("ar_vr", roles[1]),
            ("sales_engineering", roles[2]),
        ]:
            result = tag_career_roles.classify_role(item, taxonomy)
            self.assertEqual(taxonomy[tag_slug].status, "auto_added")
            self.assertIn(tag_slug, result.assigned_tags)

    def test_machine_learning_cluster_does_not_discover_training_from_learning_word(self):
        roles = [
            role(31, "Machine Learning Engineer", raw_skills="PyTorch, TensorFlow"),
            role(32, "Machine Learning Scientist", raw_skills="NLP, model training"),
            role(33, "Machine Learning Architect", raw_skills="deep learning"),
        ]

        taxonomy = tag_career_roles.build_taxonomy(roles, discover_new_tags=True)
        result = tag_career_roles.classify_role(roles[0], taxonomy)

        self.assertNotIn("education_training", taxonomy)
        self.assertNotIn("education_training", result.assigned_tags)

    def test_previous_low_confidence_roles_get_at_least_one_tag(self):
        roles = [
            role(60, "COMPUTER GRAPHICS ANIMATOR"),
            role(61, "ELK ENGINEER"),
            role(610, "FLUENTD ENGINEER"),
            role(611, "GRAFANA ENGINEER"),
            role(62, "GERRIT ADMINISTRATOR"),
            role(63, "PRINCIPLE ENGINEER IN DATA ANALYSIS"),
            role(64, "DIGITAL TRANSFORMATION CONSULTANT"),
            role(65, "GEOGRAPHIC INFORMATION SYSTEMS (GIS) ANALYST"),
            role(66, "MAINFRAME DEVELOPER"),
            role(67, "WEBMASTER"),
            role(68, "VFX ARTIST"),
            role(69, "COMPOSITOR"),
        ]

        taxonomy = tag_career_roles.build_taxonomy(roles, discover_new_tags=True)
        results = [tag_career_roles.classify_role(item, taxonomy) for item in roles]
        results_by_title = {result.role.job_title: result for result in results}

        self.assertTrue(all(result.assigned_tags for result in results))
        self.assertIn("animation_graphics", results_by_title["COMPUTER GRAPHICS ANIMATOR"].assigned_tags)
        self.assertIn("observability", results_by_title["ELK ENGINEER"].assigned_tags)
        self.assertIn("devops", results_by_title["GERRIT ADMINISTRATOR"].assigned_tags)
        self.assertIn("data_analytics", results_by_title["PRINCIPLE ENGINEER IN DATA ANALYSIS"].assigned_tags)
        self.assertIn("business_analysis", results_by_title["DIGITAL TRANSFORMATION CONSULTANT"].assigned_tags)
        self.assertIn("gis_geospatial", results_by_title["GEOGRAPHIC INFORMATION SYSTEMS (GIS) ANALYST"].assigned_tags)
        self.assertIn("software_engineering", results_by_title["MAINFRAME DEVELOPER"].assigned_tags)
        self.assertIn("frontend", results_by_title["WEBMASTER"].assigned_tags)
        self.assertIn("animation_graphics", results_by_title["VFX ARTIST"].assigned_tags)

    def test_manual_override_by_role_id_takes_precedence_and_adds_taxonomy_tag(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "domain_tags_overrides.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["role_id", "job_title", "domain_tags", "notes"],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "role_id": "40",
                    "job_title": "SAP Analyst",
                    "domain_tags": "erp_crm,business_analysis",
                    "notes": "Course team override",
                }
            )

        taxonomy = tag_career_roles.build_taxonomy([], discover_new_tags=False)
        overrides = tag_career_roles.load_manual_overrides(path, taxonomy)
        result = tag_career_roles.classify_role(
            role(40, "SAP Analyst", raw_skills="SAP"),
            taxonomy,
            overrides=overrides,
        )

        self.assertEqual(result.assigned_tags, ["erp_crm", "business_analysis"])
        self.assertEqual(taxonomy["erp_crm"].source, "manual_override")
        self.assertEqual(taxonomy["business_analysis"].source, "manual_override")

    def test_update_domain_tags_updates_only_changed_domain_tags_values(self):
        class FakeClient:
            def __init__(self):
                self.updated = []

            def update_role_domain_tags(self, role_id, domain_tags):
                self.updated.append((role_id, domain_tags))

        client = FakeClient()
        classifications = [
            tag_career_roles.ClassificationResult(
                role=role(50, "Frontend Developer", domain_tags=None),
                assigned_tags=["frontend"],
                confidence="high",
                tag_scores={"frontend": 8},
                matched_keywords={"frontend": ["frontend"]},
                reason="frontend matched",
                new_tags_used=[],
                needs_human_review=False,
                used_override=False,
            ),
            tag_career_roles.ClassificationResult(
                role=role(51, "Data Analyst", domain_tags="data_analytics"),
                assigned_tags=["data_analytics"],
                confidence="high",
                tag_scores={"data_analytics": 8},
                matched_keywords={"data_analytics": ["data analyst"]},
                reason="already tagged",
                new_tags_used=[],
                needs_human_review=False,
                used_override=False,
            ),
            tag_career_roles.ClassificationResult(
                role=role(52, "Cloud Engineer", domain_tags="infrastructure"),
                assigned_tags=["cloud"],
                confidence="high",
                tag_scores={"cloud": 8},
                matched_keywords={"cloud": ["cloud"]},
                reason="existing different tag is protected without force",
                new_tags_used=[],
                needs_human_review=False,
                used_override=False,
            ),
        ]

        stats = tag_career_roles.update_domain_tags(
            classifications,
            client,
            dry_run=False,
            force=False,
        )

        self.assertEqual(client.updated, [(50, "frontend")])
        self.assertEqual(stats.roles_updated, 1)
        self.assertEqual(stats.roles_unchanged, 1)
        self.assertEqual(stats.roles_skipped_existing, 1)

    def test_client_resolves_role_certifications_through_mapping_table(self):
        class FakeClient(tag_career_roles.SupabaseRestClient):
            def __init__(self):
                self.schema = tag_career_roles.DEFAULT_SCHEMA

            def _paged_get(self, table, select, extra_query=None):
                if table == self.schema.certifications_mapping_table:
                    return [
                        {"role_id": 10, "certification_id": 100},
                        {"role_id": 10, "certification_id": 101},
                    ]
                if table == self.schema.certifications_table:
                    return [
                        {
                            "certification_id": 100,
                            "certification_name": "CKA",
                            "normalized_certification_name": "cka",
                        },
                        {
                            "certification_id": 101,
                            "certification_name": "AWS Certified Developer",
                            "normalized_certification_name": "aws certified developer",
                        },
                    ]
                raise AssertionError(f"Unexpected table: {table}")

        certifications = FakeClient().list_role_certifications_by_role_id()

        self.assertEqual(
            certifications,
            {
                "10": [
                    "CKA",
                    "cka",
                    "AWS Certified Developer",
                    "aws certified developer",
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
