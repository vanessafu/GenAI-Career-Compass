import csv
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "import_kaggle_roles.py"
spec = importlib.util.spec_from_file_location("import_kaggle_roles", SCRIPT_PATH)
import_kaggle_roles = importlib.util.module_from_spec(spec)
sys.modules["import_kaggle_roles"] = import_kaggle_roles
spec.loader.exec_module(import_kaggle_roles)


class FakeClient:
    def __init__(self):
        self.roles = {}
        self.role_source_hashes = {}
        self.role_data = {}
        self.next_role_id = 100
        self.deleted_skills = []
        self.deleted_certifications = []
        self.inserted_skills = []
        self.inserted_certifications = []
        self.inserted_roles = []
        self.updated_roles = []
        self.updated_role_titles = []

    def find_role_by_title(self, job_title):
        role_id = self.roles.get(job_title)
        if role_id is None:
            return None
        return {"role_id": role_id, "job_title": job_title}

    def list_roles(self):
        rows = []
        for job_title, role_id in self.roles.items():
            row = {"role_id": role_id, "job_title": job_title}
            if job_title in self.role_source_hashes:
                row["source_row_hash"] = self.role_source_hashes[job_title]
            row.update(self.role_data.get(job_title, {}))
            rows.append(row)
        return rows

    def insert_role(self, role):
        role_id = self.next_role_id
        self.next_role_id += 1
        self.inserted_roles.append((role_id, role.job_title, role.source_row_hash))
        self.roles[role.job_title] = role_id
        self.role_source_hashes[role.job_title] = role.source_row_hash
        return {"role_id": role_id, "job_title": role.job_title}

    def insert_roles(self, roles):
        return [self.insert_role(role) for role in roles]

    def update_role(self, role_id, role):
        self.updated_roles.append((role_id, role.job_title))
        for existing_title, existing_role_id in list(self.roles.items()):
            if existing_role_id == role_id:
                self.role_source_hashes[existing_title] = role.source_row_hash

    def update_role_title(self, role_id, job_title):
        self.updated_role_titles.append((role_id, job_title))
        for existing_title, existing_role_id in list(self.roles.items()):
            if existing_role_id == role_id:
                del self.roles[existing_title]
                self.roles[job_title] = role_id
                return

    def delete_role_skills_for_roles(self, role_ids):
        self.deleted_skills.extend(role_ids)

    def delete_role_certifications_for_roles(self, role_ids):
        self.deleted_certifications.extend(role_ids)

    def delete_role_skills(self, role_id):
        self.deleted_skills.append(role_id)

    def delete_role_certifications(self, role_id):
        self.deleted_certifications.append(role_id)

    def insert_role_skills(self, rows):
        self.inserted_skills.extend(rows)

    def insert_role_certifications(self, rows):
        self.inserted_certifications.extend(rows)


class ImportKaggleRolesTests(unittest.TestCase):
    def write_csv(self, rows, fieldnames=None):
        fieldnames = fieldnames or [
            "Job Title",
            "Job Description",
            "Skills",
            "Certifications",
        ]
        directory = TemporaryDirectory()
        path = Path(directory.name) / "roles.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(directory.cleanup)
        return path

    def test_parse_roles_trims_skips_empty_titles_and_deduplicates_children(self):
        path = self.write_csv(
            [
                {
                    "Job Title": "  Platform Engineer  ",
                    "Job Description": "  Keeps systems running.  ",
                    "Skills": " Python, python , C++, CI/CD, , Node.js ",
                    "Certifications": " AWS Certified Cloud Practitioner, aws certified cloud practitioner, ",
                },
                {
                    "Job Title": "   ",
                    "Job Description": "Skipped",
                    "Skills": "Linux",
                    "Certifications": "Linux+",
                },
            ]
        )

        roles, stats = import_kaggle_roles.parse_csv(path)

        self.assertEqual(stats.rows_read, 2)
        self.assertEqual(stats.rows_skipped, 1)
        self.assertEqual(len(roles), 1)
        role = roles[0]
        self.assertEqual(role.job_title, "Platform Engineer")
        self.assertEqual(role.job_description, "Keeps systems running.")
        self.assertEqual(role.raw_skills, "Python, python , C++, CI/CD, , Node.js")
        self.assertEqual(
            [skill.skill_name for skill in role.skills],
            ["Python", "C++", "CI/CD", "Node.js"],
        )
        self.assertEqual(
            [skill.normalized_skill_name for skill in role.skills],
            ["python", "c++", "ci/cd", "node.js"],
        )
        self.assertEqual(
            [cert.certification_name for cert in role.certifications],
            ["AWS Certified Cloud Practitioner"],
        )
        self.assertEqual(
            [cert.normalized_certification_name for cert in role.certifications],
            ["aws certified cloud practitioner"],
        )

    def test_normalize_job_title_title_cases_full_caps_with_known_exceptions(self):
        cases = {
            "ACCESSIBILITY SPECIALIST": "Accessibility Specialist",
            "IT SUPPORT ANALYST": "IT Support Analyst",
            "QA ENGINEER": "QA Engineer",
            "UX/UI DESIGNER": "UX/UI Designer",
            "SQL DATABASE ADMINISTRATOR": "SQL Database Administrator",
            "AWS SAP ELK DEVOPS SPECIALIST": "AWS SAP ELK DevOps Specialist",
            "RUBY ON RAILS DEVELOPER": "Ruby on Rails Developer",
            "Artificial intelligence Architect": "Artificial Intelligence Architect",
        }

        for raw_title, expected_title in cases.items():
            with self.subTest(raw_title=raw_title):
                self.assertEqual(
                    import_kaggle_roles.normalize_job_title(raw_title),
                    expected_title,
                )

    def test_source_row_hash_ignores_title_case_and_whitespace(self):
        first = import_kaggle_roles.ParsedRole(
            job_title="Data Engineer",
            job_description="Builds pipelines.",
            raw_skills="Python, SQL",
            raw_certifications="AWS Certified Data Engineer",
        )
        second = import_kaggle_roles.ParsedRole(
            job_title="  DATA   ENGINEER  ",
            job_description="Builds pipelines.",
            raw_skills="Python, SQL",
            raw_certifications="AWS Certified Data Engineer",
        )

        first_hash = import_kaggle_roles.compute_source_row_hash(first)
        second_hash = import_kaggle_roles.compute_source_row_hash(second)

        self.assertEqual(first_hash, second_hash)
        self.assertRegex(first_hash, r"^[0-9a-f]{64}$")

    def test_parse_csv_keeps_same_title_variants_with_different_payloads(self):
        path = self.write_csv(
            [
                {
                    "Job Title": "DevOps Engineer",
                    "Job Description": "First version.",
                    "Skills": "Docker",
                    "Certifications": "Docker Certification",
                },
                {
                    "Job Title": "DEVOPS ENGINEER",
                    "Job Description": "Second version.",
                    "Skills": "Kubernetes, Terraform",
                    "Certifications": "CKA",
                },
            ]
        )

        roles, stats = import_kaggle_roles.parse_csv(path)

        self.assertEqual(stats.rows_read, 2)
        self.assertEqual(stats.duplicate_source_rows, 0)
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0].job_title, "DevOps Engineer")
        self.assertEqual(roles[0].job_description, "First version.")
        self.assertEqual(roles[1].job_title, "DevOps Engineer")
        self.assertEqual(roles[1].job_description, "Second version.")
        self.assertNotEqual(roles[0].source_row_hash, roles[1].source_row_hash)
        self.assertEqual(
            [skill.skill_name for skill in roles[1].skills],
            ["Kubernetes", "Terraform"],
        )
        self.assertEqual(
            [cert.certification_name for cert in roles[1].certifications],
            ["CKA"],
        )

    def test_parse_csv_deduplicates_certifications_by_normalized_name(self):
        path = self.write_csv(
            [
                {
                    "Job Title": "Cloud Engineer",
                    "Job Description": "Builds cloud platforms.",
                    "Skills": "AWS",
                    "Certifications": (
                        "AWS Certified Developer \u2013 Associate, "
                        "AWS Certified Developer - Associate, "
                        "CompTIA IT Fundamentals+, "
                        "CompTIA IT Fundamentals"
                    ),
                },
            ]
        )

        roles, stats = import_kaggle_roles.parse_csv(path)

        self.assertEqual(stats.rows_read, 1)
        self.assertEqual(
            [cert.certification_name for cert in roles[0].certifications],
            [
                "AWS Certified Developer \u2013 Associate",
                "CompTIA IT Fundamentals+",
                "CompTIA IT Fundamentals",
            ],
        )
        self.assertEqual(
            [cert.normalized_certification_name for cert in roles[0].certifications],
            [
                "aws certified developer - associate",
                "comptia it fundamentals+",
                "comptia it fundamentals",
            ],
        )

    def test_parse_csv_collapses_duplicate_source_rows_with_last_row_winning(self):
        path = self.write_csv(
            [
                {
                    "Job Title": "DevOps Engineer",
                    "Job Description": "First version.",
                    "Skills": "Docker",
                    "Certifications": "Docker Certification",
                },
                {
                    "Job Title": "DevOps Engineer",
                    "Job Description": "First version.",
                    "Skills": "Docker",
                    "Certifications": "Docker Certification",
                },
            ]
        )

        roles, stats = import_kaggle_roles.parse_csv(path)

        self.assertEqual(stats.rows_read, 2)
        self.assertEqual(stats.duplicate_source_rows, 1)
        self.assertEqual(len(roles), 1)
        self.assertEqual(roles[0].job_description, "First version.")
        self.assertEqual(
            [skill.skill_name for skill in roles[0].skills],
            ["Docker"],
        )
        self.assertEqual(
            [cert.certification_name for cert in roles[0].certifications],
            ["Docker Certification"],
        )

    def test_parse_csv_rejects_missing_required_columns(self):
        path = self.write_csv(
            [{"Job Title": "Missing columns"}],
            fieldnames=["Job Title"],
        )

        with self.assertRaisesRegex(ValueError, "missing required column"):
            import_kaggle_roles.parse_csv(path)

    def test_parse_csv_accepts_windows_1252_exports(self):
        directory = TemporaryDirectory()
        path = Path(directory.name) / "roles.csv"
        self.addCleanup(directory.cleanup)
        path.write_bytes(
            b"Job Title,Job Description,Skills,Certifications\n"
            b"Support Engineer,Handles users\x92 requests,Windows,CompTIA A+\n"
        )

        roles, stats = import_kaggle_roles.parse_csv(path)

        self.assertEqual(stats.rows_read, 1)
        self.assertEqual(roles[0].job_description, "Handles users\u2019 requests")

    def test_import_roles_reuses_existing_roles_and_replaces_children(self):
        role = import_kaggle_roles.ParsedRole(
            job_title="Data Engineer",
            job_description="Builds pipelines.",
            raw_skills="Python, SQL",
            raw_certifications="AWS Certified Data Engineer",
            skills=[
                import_kaggle_roles.ParsedSkill("Python", "python"),
                import_kaggle_roles.ParsedSkill("SQL", "sql"),
            ],
            certifications=[
                import_kaggle_roles.ParsedCertification(
                    "AWS Certified Data Engineer",
                    "aws certified data engineer",
                ),
            ],
        )
        client = FakeClient()
        client.roles["Data Engineer"] = 42
        client.role_source_hashes["Data Engineer"] = (
            import_kaggle_roles.compute_source_row_hash(role)
        )

        stats = import_kaggle_roles.import_roles([role], client)

        self.assertEqual(stats.roles_inserted, 0)
        self.assertEqual(stats.roles_reused_or_updated, 1)
        self.assertEqual(client.updated_roles, [(42, "Data Engineer")])
        self.assertEqual(client.deleted_skills, [42])
        self.assertEqual(client.deleted_certifications, [42])
        self.assertEqual(
            client.inserted_skills,
            [
                {
                    "role_id": 42,
                    "skill_name": "Python",
                    "normalized_skill_name": "python",
                },
                {
                    "role_id": 42,
                    "skill_name": "SQL",
                    "normalized_skill_name": "sql",
                },
            ],
        )
        self.assertEqual(
            client.inserted_certifications,
            [
                {
                    "role_id": 42,
                    "certification_name": "AWS Certified Data Engineer",
                    "normalized_certification_name": "aws certified data engineer",
                }
            ],
        )
        self.assertEqual(stats.skills_inserted, 2)
        self.assertEqual(stats.certifications_inserted, 1)

    def test_import_roles_reuses_existing_roles_by_source_row_hash(self):
        role = import_kaggle_roles.ParsedRole(
            job_title="DevOps Engineer",
            job_description="Builds delivery platforms.",
            raw_skills="Kubernetes",
            raw_certifications="CKA",
            skills=[
                import_kaggle_roles.ParsedSkill("Kubernetes", "kubernetes"),
            ],
            certifications=[
                import_kaggle_roles.ParsedCertification("CKA", "cka"),
            ],
        )
        client = FakeClient()
        client.roles["DEVOPS ENGINEER"] = 42
        client.role_source_hashes["DEVOPS ENGINEER"] = (
            import_kaggle_roles.compute_source_row_hash(role)
        )

        stats = import_kaggle_roles.import_roles([role], client)

        self.assertEqual(stats.roles_inserted, 0)
        self.assertEqual(stats.roles_reused_or_updated, 1)
        self.assertEqual(client.updated_roles, [(42, "DevOps Engineer")])
        self.assertEqual(client.deleted_skills, [42])
        self.assertEqual(client.deleted_certifications, [42])

    def test_import_roles_inserts_same_title_variant_with_different_source_row_hash(self):
        existing_role = import_kaggle_roles.ParsedRole(
            job_title="DevOps Engineer",
            job_description="Builds delivery platforms.",
            raw_skills="Kubernetes",
            raw_certifications="CKA",
        )
        new_variant = import_kaggle_roles.ParsedRole(
            job_title="DevOps Engineer",
            job_description="Leads platform automation.",
            raw_skills="Ansible",
            raw_certifications="Red Hat Certified Specialist",
            skills=[
                import_kaggle_roles.ParsedSkill("Ansible", "ansible"),
            ],
            certifications=[
                import_kaggle_roles.ParsedCertification(
                    "Red Hat Certified Specialist",
                    "red hat certified specialist",
                ),
            ],
        )
        client = FakeClient()
        client.roles["DevOps Engineer"] = 42
        client.role_source_hashes["DevOps Engineer"] = (
            import_kaggle_roles.compute_source_row_hash(existing_role)
        )

        stats = import_kaggle_roles.import_roles([new_variant], client)

        self.assertEqual(stats.roles_inserted, 1)
        self.assertEqual(stats.roles_reused_or_updated, 0)
        self.assertEqual(
            client.inserted_roles,
            [
                (
                    100,
                    "DevOps Engineer",
                    import_kaggle_roles.compute_source_row_hash(new_variant),
                )
            ],
        )

    def test_normalize_existing_role_titles_updates_only_changed_titles(self):
        client = FakeClient()
        client.roles["DATA ANALYST"] = 41
        client.roles["QA Engineer"] = 42

        stats = import_kaggle_roles.normalize_existing_role_titles(client)

        self.assertEqual(stats.roles_checked, 2)
        self.assertEqual(stats.titles_normalized, 1)
        self.assertEqual(client.updated_role_titles, [(41, "Data Analyst")])
        self.assertEqual(client.roles["Data Analyst"], 41)
        self.assertEqual(client.roles["QA Engineer"], 42)

    def test_normalized_skill_name_keeps_meaningful_punctuation(self):
        self.assertEqual(import_kaggle_roles.normalize_skill_name("  C++  "), "c++")
        self.assertEqual(import_kaggle_roles.normalize_skill_name("CI/CD"), "ci/cd")
        self.assertEqual(import_kaggle_roles.normalize_skill_name(" Node.js "), "node.js")
        self.assertEqual(
            import_kaggle_roles.normalize_skill_name("Cloud   Computing"),
            "cloud computing",
        )

    def test_normalized_certification_name_is_conservative(self):
        cases = {
            "  AWS   Certified Developer - Associate  ": (
                "aws certified developer - associate"
            ),
            "AWS Certified Developer \u2013 Associate": (
                "aws certified developer - associate"
            ),
            "AWS Certified Developer \u00e2\u20ac\u201c Associate": (
                "aws certified developer - associate"
            ),
            "Microsoft Certified : Azure Developer Associate": (
                "microsoft certified: azure developer associate"
            ),
            "CompTIA IT Fundamentals+": "comptia it fundamentals+",
            "HashiCorp Certified: Terraform Associate": (
                "hashicorp certified: terraform associate"
            ),
            "HashiCorp Certified Terraform Associate": (
                "hashicorp certified terraform associate"
            ),
        }

        for raw_name, expected_name in cases.items():
            with self.subTest(raw_name=raw_name):
                self.assertEqual(
                    import_kaggle_roles.normalize_certification_name(raw_name),
                    expected_name,
                )

    def test_normalize_supabase_url_converts_dashboard_project_url(self):
        self.assertEqual(
            import_kaggle_roles.normalize_supabase_url(
                "https://supabase.com/dashboard/project/gcgfpmpbcgrdysnelcls"
            ),
            "https://gcgfpmpbcgrdysnelcls.supabase.co",
        )

    def test_secret_key_headers_do_not_send_authorization_bearer(self):
        client = import_kaggle_roles.SupabaseRestClient(
            "https://example.supabase.co",
            "sb_secret_abc123",
        )

        headers = client._auth_headers()

        self.assertEqual(headers["apikey"], "sb_secret_abc123")
        self.assertNotIn("Authorization", headers)

    def test_legacy_jwt_headers_send_authorization_bearer(self):
        client = import_kaggle_roles.SupabaseRestClient(
            "https://example.supabase.co",
            "header.payload.signature",
        )

        headers = client._auth_headers()

        self.assertEqual(headers["Authorization"], "Bearer header.payload.signature")

    def test_load_dotenv_file_sets_missing_values_without_overwriting_environment(self):
        directory = TemporaryDirectory()
        path = Path(directory.name) / ".env"
        self.addCleanup(directory.cleanup)
        path.write_text(
            "\n".join(
                [
                    "SUPABASE_URL=https://from-file.supabase.co",
                    "SUPABASE_SERVICE_ROLE_KEY='sb_secret_from_file'",
                ]
            ),
            encoding="utf-8",
        )

        previous_url = os.environ.get("SUPABASE_URL")
        previous_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        try:
            os.environ["SUPABASE_URL"] = "https://from-env.supabase.co"
            os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)

            import_kaggle_roles.load_dotenv_file(path)

            self.assertEqual(
                os.environ["SUPABASE_URL"],
                "https://from-env.supabase.co",
            )
            self.assertEqual(
                os.environ["SUPABASE_SERVICE_ROLE_KEY"],
                "sb_secret_from_file",
            )
        finally:
            if previous_url is None:
                os.environ.pop("SUPABASE_URL", None)
            else:
                os.environ["SUPABASE_URL"] = previous_url
            if previous_key is None:
                os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)
            else:
                os.environ["SUPABASE_SERVICE_ROLE_KEY"] = previous_key


if __name__ == "__main__":
    unittest.main()
