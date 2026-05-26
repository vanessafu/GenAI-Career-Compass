import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "review_german_salary_seed.py"
)
spec = importlib.util.spec_from_file_location("review_german_salary_seed", SCRIPT_PATH)
review_german_salary_seed = importlib.util.module_from_spec(spec)
sys.modules["review_german_salary_seed"] = review_german_salary_seed
spec.loader.exec_module(review_german_salary_seed)


def seed_row(**overrides):
    row = {
        "role_id": "1",
        "job_title": "Software Developer",
        "domain_tags": "software_engineering",
        "kldb_code": "43413",
        "entgeltatlas_match_title": "Softwareentwickler/in",
        "salary_group_code": "434",
        "salary_source_group_title": "Softwareentwicklung und Programmierung",
        "salary_selected_column": "Spezialisten",
        "salary_median_monthly_gross_eur": "6082",
        "salary_fachkraefte_monthly_gross_eur": "4449",
        "salary_spezialisten_monthly_gross_eur": "6082",
        "salary_experten_monthly_gross_eur": "6144",
        "salary_band": "high",
        "salary_score": "3",
        "match_confidence": "domain_fallback",
        "source_status": "salary_table_success",
        "needs_review": "true",
    }
    row.update(overrides)
    return row


def sanity_row(**overrides):
    row = {
        "role_id": "1",
        "job_title": "Software Developer",
        "sanity_status": "acceptable_for_class_project",
        "sanity_flags": "",
        "recommended_action": "",
        "sanity_notes": "",
        "benchmark_context": "",
    }
    row.update(overrides)
    return row


class ReviewGermanSalarySeedTests(unittest.TestCase):
    def test_junior_high_salary_gets_fachkraefte_override(self):
        seed = seed_row(
            job_title="Junior Software Developer",
            match_confidence="exact_title",
        )
        sanity = sanity_row(
            job_title="Junior Software Developer",
            sanity_status="manual_override_recommended",
            sanity_flags="junior_salary_likely_high",
        )

        decision = review_german_salary_seed.review_seed_row(seed, sanity)
        override = review_german_salary_seed.override_from_decision(decision)

        self.assertEqual(decision.review_decision, "propose_salary_level_override")
        self.assertEqual(decision.proposed_action, "use_fachkraefte_level")
        self.assertEqual(decision.proposed_kldb_code, "43412")
        self.assertEqual(decision.proposed_salary_median_monthly_gross_eur, 4449)
        self.assertEqual(decision.proposed_salary_band, "medium")
        self.assertEqual(decision.proposed_salary_score, 2)
        self.assertEqual(override["kldb_code"], "43412")
        self.assertEqual(override["salary_median_monthly_gross_eur"], "4449")

    def test_senior_low_salary_gets_expert_override(self):
        seed = seed_row(
            job_title="Senior DevOps Engineer",
            kldb_code="43102",
            entgeltatlas_match_title="Fachinformatiker/in - Systemintegration",
            salary_group_code="431",
            salary_source_group_title="Informatik",
            salary_selected_column="Fachkräfte",
            salary_median_monthly_gross_eur="4960",
            salary_fachkraefte_monthly_gross_eur="4960",
            salary_spezialisten_monthly_gross_eur="6267",
            salary_experten_monthly_gross_eur="6457",
        )
        sanity = sanity_row(
            job_title="Senior DevOps Engineer",
            sanity_status="manual_override_recommended",
            sanity_flags="senior_salary_likely_low",
        )

        decision = review_german_salary_seed.review_seed_row(seed, sanity)

        self.assertEqual(decision.proposed_action, "use_experten_level")
        self.assertEqual(decision.proposed_kldb_code, "43104")
        self.assertEqual(decision.proposed_salary_median_monthly_gross_eur, 6457)
        self.assertEqual(decision.proposed_salary_band, "high")

    def test_creative_questionable_mapping_requires_research_without_override(self):
        seed = seed_row(
            job_title="UX Designer",
            kldb_code="43104",
            salary_group_code="431",
            salary_selected_column="Experten",
            salary_median_monthly_gross_eur="6457",
        )
        sanity = sanity_row(
            job_title="UX Designer",
            sanity_status="manual_override_recommended",
            sanity_flags="creative_mapping_questionable",
        )

        decision = review_german_salary_seed.review_seed_row(seed, sanity)
        override = review_german_salary_seed.override_from_decision(decision)

        self.assertEqual(decision.review_decision, "manual_research_required")
        self.assertEqual(decision.proposed_action, "find_better_kldb_mapping")
        self.assertEqual(override, {})

    def test_non_core_senior_low_mapping_requires_research_without_override(self):
        seed = seed_row(
            job_title="Information Architect",
            kldb_code="23223",
            salary_group_code="232",
            salary_selected_column="Spezialisten",
            salary_median_monthly_gross_eur="3713",
            salary_spezialisten_monthly_gross_eur="3713",
            salary_experten_monthly_gross_eur="3917",
        )
        sanity = sanity_row(
            job_title="Information Architect",
            sanity_status="manual_override_recommended",
            sanity_flags="non_core_it_salary_group;senior_salary_likely_low",
        )

        decision = review_german_salary_seed.review_seed_row(seed, sanity)

        self.assertEqual(decision.review_decision, "manual_research_required")
        self.assertEqual(decision.proposed_action, "review_manually")
        self.assertEqual(review_german_salary_seed.override_from_decision(decision), {})

    def test_acceptable_row_is_approved_without_override(self):
        decision = review_german_salary_seed.review_seed_row(seed_row(), sanity_row())

        self.assertEqual(decision.review_decision, "approve")
        self.assertEqual(decision.proposed_action, "keep_current")
        self.assertEqual(review_german_salary_seed.override_from_decision(decision), {})

    def test_cli_writes_decisions_and_only_concrete_overrides(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            seed_path = base / "seed.csv"
            sanity_path = base / "sanity.csv"
            decisions_path = base / "decisions.csv"
            overrides_path = base / "overrides.csv"

            review_german_salary_seed.write_csv(
                seed_path,
                [
                    seed_row(role_id="1", job_title="Junior Software Developer"),
                    seed_row(role_id="2", job_title="UX Designer", kldb_code="43104"),
                ],
                review_german_salary_seed.required_seed_fields(),
            )
            review_german_salary_seed.write_csv(
                sanity_path,
                [
                    sanity_row(
                        role_id="1",
                        job_title="Junior Software Developer",
                        sanity_status="manual_override_recommended",
                        sanity_flags="junior_salary_likely_high",
                    ),
                    sanity_row(
                        role_id="2",
                        job_title="UX Designer",
                        sanity_status="manual_override_recommended",
                        sanity_flags="creative_mapping_questionable",
                    ),
                ],
                review_german_salary_seed.SANITY_FIELDNAMES,
            )

            exit_code = review_german_salary_seed.main(
                [
                    "--seed",
                    str(seed_path),
                    "--sanity-review",
                    str(sanity_path),
                    "--output",
                    str(decisions_path),
                    "--overrides-output",
                    str(overrides_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            with decisions_path.open(newline="", encoding="utf-8") as handle:
                decisions = list(csv.DictReader(handle))
            with overrides_path.open(newline="", encoding="utf-8") as handle:
                overrides = list(csv.DictReader(handle))
            self.assertEqual(len(decisions), 2)
            self.assertEqual(len(overrides), 1)
            self.assertEqual(overrides[0]["role_id"], "1")


if __name__ == "__main__":
    unittest.main()
