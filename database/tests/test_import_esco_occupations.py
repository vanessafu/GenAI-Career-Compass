import csv
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "import_esco_occupations.py"
)
spec = importlib.util.spec_from_file_location("import_esco_occupations", SCRIPT_PATH)
import_esco_occupations = importlib.util.module_from_spec(spec)
sys.modules["import_esco_occupations"] = import_esco_occupations
spec.loader.exec_module(import_esco_occupations)


class FakeClient:
    def __init__(self):
        self.rows = {}
        self.inserted_rows = []
        self.updated_rows = []

    def find_occupation_by_uri(self, esco_uri):
        row = self.rows.get(esco_uri)
        if row is None:
            return None
        return dict(row)

    def insert_occupation(self, occupation):
        row = occupation.to_payload()
        self.rows[occupation.esco_uri] = row
        self.inserted_rows.append(row)

    def update_occupation(self, occupation):
        row = occupation.to_payload()
        self.rows[occupation.esco_uri] = row
        self.updated_rows.append(row)


class ImportEscoOccupationsTests(unittest.TestCase):
    def write_csv(self, rows, fieldnames):
        directory = TemporaryDirectory()
        path = Path(directory.name) / "occupations_en.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        self.addCleanup(directory.cleanup)
        return path

    def test_parse_filters_camel_case_ict_occupations_and_review_rows(self):
        path = self.write_csv(
            [
                {
                    "conceptType": "Occupation",
                    "conceptUri": "http://data.europa.eu/esco/occupation/software",
                    "iscoGroup": "2512",
                    "preferredLabel": " software analyst ",
                    "definition": " Defines systems. ",
                    "description": "Fallback should not win.",
                    "scopeNote": "Last fallback.",
                },
                {
                    "conceptType": "Occupation",
                    "conceptUri": "http://data.europa.eu/esco/occupation/teacher",
                    "iscoGroup": "2359",
                    "preferredLabel": "teacher",
                    "definition": "Teaches.",
                },
                {
                    "conceptType": "OccupationGroup",
                    "conceptUri": "http://data.europa.eu/esco/group/ict",
                    "iscoGroup": "25",
                    "preferredLabel": "ICT professionals",
                    "definition": "Group row.",
                },
                {
                    "conceptType": "Occupation",
                    "conceptUri": "",
                    "iscoGroup": "2529",
                    "preferredLabel": "missing uri",
                    "definition": "Skipped.",
                },
            ],
            [
                "conceptType",
                "conceptUri",
                "iscoGroup",
                "preferredLabel",
                "definition",
                "description",
                "scopeNote",
            ],
        )

        result = import_esco_occupations.parse_occupations_csv(path)

        self.assertEqual(result.stats.rows_read, 4)
        self.assertEqual(result.stats.rows_included, 1)
        self.assertEqual(result.stats.rows_skipped_missing_required, 1)
        self.assertEqual(result.stats.rows_skipped_non_occupation, 1)
        self.assertEqual(result.stats.rows_skipped_outside_isco_filter, 1)
        self.assertEqual(result.detected_mapping.esco_uri, "conceptUri")
        self.assertEqual(result.detected_mapping.name, "preferredLabel")
        self.assertEqual(result.detected_mapping.isco_code, "iscoGroup")
        self.assertEqual(
            result.detected_mapping.definition,
            "definition, description, scopeNote",
        )

        occupation = result.occupations[0]
        self.assertEqual(
            occupation.esco_uri,
            "http://data.europa.eu/esco/occupation/software",
        )
        self.assertEqual(occupation.isco_code, "2512")
        self.assertEqual(occupation.name, "software analyst")
        self.assertEqual(occupation.definition, "Defines systems.")

        review = result.review_rows
        self.assertEqual(
            [(row.source_row_number, row.included, row.skip_reason) for row in review],
            [
                (2, True, ""),
                (3, False, "isco_code_outside_allowed_prefixes"),
                (4, False, "concept_type_not_occupation"),
                (5, False, "missing_esco_uri"),
            ],
        )

    def test_parse_supports_human_readable_columns_and_ignores_removed_parent_fields(self):
        path = self.write_csv(
            [
                {
                    "Concept URI": "http://data.europa.eu/esco/occupation/support",
                    "Concept type": "OC",
                    "ISCO code": "3512",
                    "Concept PT": "ICT help desk agent",
                    "Definition": "",
                    "Parent Concept URI": "http://data.europa.eu/esco/isco/C3512",
                    "Parent ISCO code": "3512",
                },
                {
                    "Concept URI": "http://data.europa.eu/esco/occupation/group",
                    "Concept type": "OG",
                    "ISCO code": "351",
                    "Concept PT": "ICT operations technicians",
                    "Definition": "Group.",
                    "Parent Concept URI": "",
                    "Parent ISCO code": "",
                },
            ],
            [
                "Concept URI",
                "Concept type",
                "ISCO code",
                "Concept PT",
                "Definition",
                "Parent Concept URI",
                "Parent ISCO code",
            ],
        )

        result = import_esco_occupations.parse_occupations_csv(path)

        self.assertEqual(len(result.occupations), 1)
        occupation = result.occupations[0]
        self.assertEqual(occupation.isco_code, "3512")
        self.assertEqual(occupation.name, "ICT help desk agent")
        self.assertEqual(occupation.definition, "")
        self.assertEqual(
            result.review_rows[1].skip_reason,
            "concept_type_not_occupation",
        )

    def test_parse_without_concept_type_assumes_occupations(self):
        path = self.write_csv(
            [
                {
                    "conceptUri": "http://data.europa.eu/esco/occupation/admin",
                    "iscoGroup": "2529",
                    "preferredLabel": "ICT security administrator",
                    "description": "Keeps systems secure.",
                },
            ],
            ["conceptUri", "iscoGroup", "preferredLabel", "description"],
        )

        result = import_esco_occupations.parse_occupations_csv(path)

        self.assertTrue(result.concept_type_missing)
        self.assertEqual(len(result.occupations), 1)
        self.assertEqual(result.occupations[0].definition, "Keeps systems secure.")

    def test_adjacent_ict_prefixes_only_apply_when_requested(self):
        path = self.write_csv(
            [
                {
                    "conceptType": "Occupation",
                    "conceptUri": "http://data.europa.eu/esco/occupation/cad",
                    "iscoGroup": "3114",
                    "preferredLabel": "CAD technician",
                    "definition": "Prepares drawings.",
                },
            ],
            ["conceptType", "conceptUri", "iscoGroup", "preferredLabel", "definition"],
        )

        default_result = import_esco_occupations.parse_occupations_csv(path)
        adjacent_result = import_esco_occupations.parse_occupations_csv(
            path,
            include_adjacent_ict=True,
        )

        self.assertEqual(default_result.stats.rows_included, 0)
        self.assertEqual(
            default_result.review_rows[0].skip_reason,
            "isco_code_outside_allowed_prefixes",
        )
        self.assertEqual(adjacent_result.stats.rows_included, 1)

    def test_definition_fallback_prefers_definition_then_description_then_scope_note(self):
        path = self.write_csv(
            [
                {
                    "conceptUri": "uri:def",
                    "iscoGroup": "2511",
                    "preferredLabel": "systems analyst",
                    "definition": "Definition wins.",
                    "description": "Description loses.",
                    "scopeNote": "Scope loses.",
                },
                {
                    "conceptUri": "uri:description",
                    "iscoGroup": "2512",
                    "preferredLabel": "software analyst",
                    "definition": "",
                    "description": "Description wins.",
                    "scopeNote": "Scope loses.",
                },
                {
                    "conceptUri": "uri:scope",
                    "iscoGroup": "2513",
                    "preferredLabel": "SEO expert",
                    "definition": "",
                    "description": "",
                    "scopeNote": "Scope wins.",
                },
            ],
            [
                "conceptUri",
                "iscoGroup",
                "preferredLabel",
                "definition",
                "description",
                "scopeNote",
            ],
        )

        result = import_esco_occupations.parse_occupations_csv(path)

        self.assertEqual(
            [occupation.definition for occupation in result.occupations],
            ["Definition wins.", "Description wins.", "Scope wins."],
        )

    def test_write_review_csv(self):
        review_path_directory = TemporaryDirectory()
        self.addCleanup(review_path_directory.cleanup)
        review_path = Path(review_path_directory.name) / "review.csv"
        rows = [
            import_esco_occupations.ReviewRow(
                source_row_number=2,
                esco_uri="uri",
                concept_type="Occupation",
                isco_code="2512",
                name="software analyst",
                included=True,
                skip_reason="",
            )
        ]

        import_esco_occupations.write_review_csv(review_path, rows)

        with review_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            self.assertEqual(
                list(reader),
                [
                    {
                        "source_row_number": "2",
                        "esco_uri": "uri",
                        "concept_type": "Occupation",
                        "isco_code": "2512",
                        "name": "software analyst",
                        "included": "true",
                        "skip_reason": "",
                    }
                ],
            )

    def test_import_reuses_existing_rows_by_default_and_updates_with_force(self):
        occupation = import_esco_occupations.EscoOccupation(
            esco_uri="uri:existing",
            isco_code="2512",
            name="software analyst",
            definition="New definition.",
        )
        client = FakeClient()
        client.rows["uri:existing"] = {
            "esco_uri": "uri:existing",
            "isco_code": "2512",
            "name": "old label",
            "definition": "Old definition.",
        }

        default_stats = import_esco_occupations.import_occupations(
            [occupation],
            client,
        )
        force_stats = import_esco_occupations.import_occupations(
            [occupation],
            client,
            force=True,
        )

        self.assertEqual(default_stats.rows_inserted, 0)
        self.assertEqual(default_stats.rows_reused, 1)
        self.assertEqual(default_stats.rows_updated, 0)
        self.assertEqual(force_stats.rows_inserted, 0)
        self.assertEqual(force_stats.rows_reused, 0)
        self.assertEqual(force_stats.rows_updated, 1)
        self.assertEqual(client.updated_rows[0]["name"], "software analyst")

    def test_import_inserts_missing_rows(self):
        occupation = import_esco_occupations.EscoOccupation(
            esco_uri="uri:new",
            isco_code="2529",
            name="ICT security administrator",
            definition="Administers security.",
        )
        client = FakeClient()

        stats = import_esco_occupations.import_occupations([occupation], client)

        self.assertEqual(stats.rows_inserted, 1)
        self.assertEqual(stats.rows_reused, 0)
        self.assertEqual(stats.rows_updated, 0)
        self.assertEqual(client.inserted_rows[0]["esco_uri"], "uri:new")

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

            import_esco_occupations.load_dotenv_file(path)

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
