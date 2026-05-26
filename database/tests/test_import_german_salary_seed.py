import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "import_german_salary_seed.py"
)
spec = importlib.util.spec_from_file_location("import_german_salary_seed", SCRIPT_PATH)
import_german_salary_seed = importlib.util.module_from_spec(spec)
sys.modules["import_german_salary_seed"] = import_german_salary_seed
spec.loader.exec_module(import_german_salary_seed)


class ImportGermanSalarySeedTests(unittest.TestCase):
    def test_seed_row_maps_to_role_salaries_payload(self):
        payload = import_german_salary_seed.role_salary_payload_from_seed_row(
            {
                "role_id": "42",
                "salary_band": "high",
                "salary_score": "3",
                "salary_median_monthly_gross_eur": "6457",
                "region": "Deutschland",
                "entgeltatlas_match_title": "Informatiker/in",
                "needs_review": "true",
                "kldb_code": "43104",
            }
        )

        self.assertEqual(
            payload,
            {
                "role_id": 42,
                "salary_band": "high",
                "salary_score": 3.0,
                "salary_median_monthly_gross_eur": 6457.0,
                "region": "Deutschland",
                "entgeltatlas_match_title": "Informatiker/in",
                "needs_review": True,
                "kldb_code": "43104",
            },
        )

    def test_region_can_be_overridden(self):
        payload = import_german_salary_seed.role_salary_payload_from_seed_row(
            {
                "role_id": "42",
                "salary_band": "medium",
                "salary_score": "2",
                "salary_median_monthly_gross_eur": "4960",
                "region": "Deutschland",
                "entgeltatlas_match_title": "Fachinformatiker/in",
                "needs_review": "false",
            },
            region_override="DE",
        )

        self.assertEqual(payload["region"], "DE")
        self.assertFalse(payload["needs_review"])

    def test_empty_salary_and_missing_review_flag_are_allowed(self):
        payload = import_german_salary_seed.role_salary_payload_from_seed_row(
            {
                "role_id": "1",
                "salary_band": "unknown",
                "salary_score": "0",
                "salary_median_monthly_gross_eur": "",
                "region": "Deutschland",
                "entgeltatlas_match_title": "",
            }
        )

        self.assertIsNone(payload["salary_median_monthly_gross_eur"])
        self.assertFalse(payload["needs_review"])

    def test_sanity_review_overrides_seed_needs_review(self):
        payload = import_german_salary_seed.role_salary_payload_from_seed_row(
            {
                "role_id": "1",
                "salary_band": "high",
                "salary_score": "3",
                "salary_median_monthly_gross_eur": "6457",
                "region": "Deutschland",
                "entgeltatlas_match_title": "Data Engineer",
                "needs_review": "true",
            },
            sanity_needs_review_by_role_id={"1": False},
        )

        self.assertFalse(payload["needs_review"])

    def test_invalid_needs_review_value_is_rejected(self):
        with self.assertRaises(ValueError):
            import_german_salary_seed.role_salary_payload_from_seed_row(
                {
                    "role_id": "1",
                    "salary_band": "unknown",
                    "salary_score": "0",
                    "needs_review": "maybe",
                }
            )

    def test_load_seed_payloads_rejects_duplicate_primary_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "seed.csv"
            path.write_text(
                "role_id,salary_band,salary_score,salary_median_monthly_gross_eur,"
                "region,entgeltatlas_match_title,kldb_code,needs_review\n"
                "1,high,3,6000,Deutschland,A,43104,false\n"
                "1,medium,2,5000,Deutschland,B,43104,true\n",
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                import_german_salary_seed.load_seed_payloads(path)

    def test_load_dotenv_file_does_not_overwrite_existing_environment(self):
        previous_url = os.environ.get("SUPABASE_URL")
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".env"
            path.write_text(
                "SUPABASE_URL=https://from-file.supabase.co\n",
                encoding="utf-8",
            )
            try:
                os.environ["SUPABASE_URL"] = "https://already-set.supabase.co"
                import_german_salary_seed.load_dotenv_file(path)
                self.assertEqual(
                    os.environ["SUPABASE_URL"],
                    "https://already-set.supabase.co",
                )
            finally:
                if previous_url is None:
                    os.environ.pop("SUPABASE_URL", None)
                else:
                    os.environ["SUPABASE_URL"] = previous_url


if __name__ == "__main__":
    unittest.main()
