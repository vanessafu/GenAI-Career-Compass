import csv
import importlib.util
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "normalize_role_skills.py"
spec = importlib.util.spec_from_file_location("normalize_role_skills", SCRIPT_PATH)
normalize_role_skills = importlib.util.module_from_spec(spec)
sys.modules["normalize_role_skills"] = normalize_role_skills
spec.loader.exec_module(normalize_role_skills)


class NormalizeRoleSkillsTests(unittest.TestCase):
    def alias_map(self):
        return normalize_role_skills.alias_map_from_seed_rows(
            normalize_role_skills.DEFAULT_SEED_ALIAS_ROWS
        )

    def normalize(self, raw_skill_name):
        result = normalize_role_skills.normalize_skill(
            raw_skill_name,
            self.alias_map(),
            esco_lookup=None,
            esco_linking=True,
        )
        return result.canonical_key

    def test_seed_alias_examples_normalize_to_expected_canonical_keys(self):
        cases = {
            "JS": "javascript",
            "JavaScript Programming": "javascript",
            "React.js": "react",
            "K8s": "kubernetes",
            "CI CD": "ci/cd",
            ".NET Core": ".net",
            "Postgres": "postgresql",
            "AWS": "aws",
        }

        for raw_skill_name, expected in cases.items():
            with self.subTest(raw_skill_name=raw_skill_name):
                self.assertEqual(self.normalize(raw_skill_name), expected)

    def test_do_not_merge_examples_remain_distinct(self):
        cases = {
            "Java": "java",
            "React Native": "react native",
            "Cloud Platforms": "cloud platforms",
            "GitHub Actions": "github actions",
            "SQL": "sql",
            "PostgreSQL": "postgresql",
            "C": "c",
            "C++": "c++",
            "C#": "c#",
            "Machine Learning": "machine learning",
            "Artificial Intelligence": "artificial intelligence",
        }

        for raw_skill_name, expected in cases.items():
            with self.subTest(raw_skill_name=raw_skill_name):
                self.assertEqual(self.normalize(raw_skill_name), expected)

    def test_alias_key_normalization_preserves_meaningful_punctuation(self):
        cases = {
            "  C++  ": "c++",
            "C#": "c#",
            " Node.js ": "node.js",
            "Vue.js": "vue.js",
            "CI/CD": "ci/cd",
            "TCP/IP": "tcp/ip",
            "HTML/CSS": "html/css",
            "UI/UX": "ui/ux",
            "  'JavaScript'  ": "javascript",
            "Infrastructure-as-Code": "infrastructure-as-code",
        }

        for raw_skill_name, expected in cases.items():
            with self.subTest(raw_skill_name=raw_skill_name):
                self.assertEqual(
                    normalize_role_skills.normalize_alias_key(raw_skill_name),
                    expected,
                )

    def test_alias_key_normalization_preserves_balanced_internal_parentheses(self):
        cases = {
            "Customer Relationship Management (CRM)": (
                "customer relationship management (crm)"
            ),
            "TFS (Team Foundation Server)": "tfs (team foundation server)",
            "(Flask)": "flask",
            "Flask)": "flask",
        }

        for raw_skill_name, expected in cases.items():
            with self.subTest(raw_skill_name=raw_skill_name):
                self.assertEqual(
                    normalize_role_skills.normalize_alias_key(raw_skill_name),
                    expected,
                )

    def test_exact_esco_lookup_links_unique_labels_and_marks_ambiguous_labels(self):
        esco_rows = [
            {
                "esco_skill_uri": "uri:skill:javascript",
                "preferred_label": "JavaScript",
                "alt_labels": "JavaScript programming\nJS",
                "hidden_labels": "",
            },
            {
                "esco_skill_uri": "uri:skill:testing-a",
                "preferred_label": "Testing",
                "alt_labels": "",
                "hidden_labels": "",
            },
            {
                "esco_skill_uri": "uri:skill:testing-b",
                "preferred_label": "Testing",
                "alt_labels": "",
                "hidden_labels": "",
            },
        ]
        lookup = normalize_role_skills.build_esco_label_lookup(esco_rows)

        linked = normalize_role_skills.normalize_skill(
            "JavaScript Programming",
            self.alias_map(),
            esco_lookup=lookup,
            esco_linking=True,
        )
        ambiguous = normalize_role_skills.normalize_skill(
            "Testing",
            self.alias_map(),
            esco_lookup=lookup,
            esco_linking=True,
        )

        self.assertEqual(linked.esco_skill_uri, "uri:skill:javascript")
        self.assertEqual(linked.esco_match_status, "matched")
        self.assertIsNone(ambiguous.esco_skill_uri)
        self.assertEqual(ambiguous.esco_match_status, "ambiguous")

    def test_skill_alias_payload_matches_compact_database_schema(self):
        alias = normalize_role_skills.SkillAlias(
            alias_key="js",
            alias_display="JS",
            canonical_key="javascript",
            canonical_display="JavaScript",
            source="phase5_seed",
            confidence="high",
            notes="Common abbreviation.",
            esco_skill_uri="uri:skill:javascript",
        )

        self.assertEqual(
            alias.to_payload(),
            {
                "alias_key": "js",
                "alias_display": "JS",
                "canonical_key": "javascript",
                "canonical_display": "JavaScript",
                "esco_skill_uri": "uri:skill:javascript",
            },
        )

    def test_duplicate_collapse_report_groups_raw_skills_by_role_and_canonical_key(self):
        role_skills = [
            normalize_role_skills.RoleSkillRow(
                row_id=None,
                role_id="10",
                skill_name="JS",
                normalized_skill_name="js",
            ),
            normalize_role_skills.RoleSkillRow(
                row_id=None,
                role_id="10",
                skill_name="JavaScript Programming",
                normalized_skill_name="javascript programming",
            ),
            normalize_role_skills.RoleSkillRow(
                row_id=None,
                role_id="11",
                skill_name="React",
                normalized_skill_name="react",
            ),
        ]
        normalized = {
            row.identity_key: normalize_role_skills.normalize_skill(
                row.skill_name,
                self.alias_map(),
                esco_lookup=None,
                esco_linking=True,
            )
            for row in role_skills
        }

        duplicates = normalize_role_skills.find_duplicate_collapses(
            role_skills,
            normalized,
            job_titles_by_role_id={"10": "Frontend Developer"},
        )

        self.assertEqual(len(duplicates), 1)
        duplicate = duplicates[0]
        self.assertEqual(duplicate.role_id, "10")
        self.assertEqual(duplicate.job_title, "Frontend Developer")
        self.assertEqual(duplicate.canonical_key, "javascript")
        self.assertEqual(
            duplicate.raw_skill_names_that_collapsed,
            ["JS", "JavaScript Programming"],
        )

    def test_seed_alias_csv_loader_rejects_dangerous_do_not_merge_alias(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "skill_aliases.seed.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "alias_key",
                    "alias_display",
                    "canonical_key",
                    "canonical_display",
                    "source",
                    "confidence",
                    "notes",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "alias_key": "java",
                    "alias_display": "Java",
                    "canonical_key": "javascript",
                    "canonical_display": "JavaScript",
                    "source": "manual_seed",
                    "confidence": "high",
                    "notes": "unsafe",
                }
            )

        with self.assertRaisesRegex(ValueError, "Unsafe alias"):
            normalize_role_skills.load_seed_aliases(path)


if __name__ == "__main__":
    unittest.main()
