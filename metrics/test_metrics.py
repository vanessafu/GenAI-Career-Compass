from pathlib import Path

from metrics.common import (
    comparable_cv_fields,
    evaluate_matching_roles,
    load_json,
    score_list_field,
    score_scalar_field,
)
from metrics.run_cv_metrics import (
    default_models,
    render_model_detail_markdown,
    render_summary_markdown,
    safe_model_name,
)
from metrics.run_matching_metrics import render_markdown as render_matching_markdown


def test_scalar_score_matches_normalized_text():
    result = score_scalar_field("Junior Data Analyst", " junior data analyst ")

    assert result["score"] == 1.0


def test_scalar_score_accepts_extra_detail():
    result = score_scalar_field(
        "Product Data Analyst",
        "Product Data Analyst | Experimentation, BI, Growth Analytics",
    )

    assert result["score"] == 1.0


def test_scalar_score_rejects_different_text():
    result = score_scalar_field("Junior Data Analyst", "Backend Engineer")

    assert result["score"] == 0.0


def test_list_score_uses_set_f1_for_partial_match():
    result = score_list_field(["Python", "SQL", "Power BI"], ["python", "SQL", "Excel"])

    assert result["precision"] == 2 / 3
    assert result["recall"] == 2 / 3
    assert result["f1"] == 2 / 3
    assert result["score"] == 2 / 3


def test_list_score_accepts_extra_detail():
    result = score_list_field(
        ["github.com/alithorpe/game"],
        ["https://github.com/alithorpe/game"],
    )

    assert result["score"] == 1.0


def test_empty_expected_and_actual_list_scores_one():
    result = score_list_field([], [])

    assert result["score"] == 1.0


def test_expected_list_with_empty_actual_scores_zero():
    result = score_list_field(["Python"], [])

    assert result["score"] == 0.0


def test_comparable_cv_fields_include_dates_and_detail_fields():
    result = comparable_cv_fields(
        {
            "personal_info": {
                "full_name": "Maya Rodriguez",
                "email": "maya@example.com",
                "links": ["linkedin.com/in/maya"],
            },
            "experience": [
                {
                    "role": "Product Analyst",
                    "organization": "MarketFleet AG",
                    "start_date": "Jul 2020",
                    "end_date": "Dec 2022",
                    "location": "Berlin",
                    "core_responsibilities": ["Built dashboards"],
                    "contextual_skills": ["SQL"],
                }
            ],
            "education": [
                {
                    "entry_type": "degree",
                    "degree_type": "M.Sc.",
                    "field_of_study": "Data Science",
                    "institution": "HTW Berlin",
                    "start_date": "2018",
                    "end_date": "2020",
                    "grade": "1.4",
                    "courses": ["Machine Learning"],
                }
            ],
            "projects": [
                {
                    "title": "Retention Model",
                    "description": "churn risk model for trial users",
                    "technologies": ["Python", "Snowflake"],
                    "start_date": "2024",
                    "end_date": "Present",
                }
            ],
        }
    )

    assert result["full_name"] == "Maya Rodriguez"
    assert result["email"] == "maya@example.com"
    assert result["links"] == ["linkedin.com/in/maya"]
    assert result["experience_organizations"] == ["MarketFleet AG"]
    assert result["experience_date_ranges"] == ["2020 2022"]
    assert result["experience_responsibilities"] == ["Built dashboards"]
    assert result["experience_contextual_skills"] == ["SQL"]
    assert result["education_entry_types"] == ["degree"]
    assert result["education_institutions"] == ["HTW Berlin"]
    assert result["education_date_ranges"] == ["2018 2020"]
    assert result["education_grades"] == ["1.4"]
    assert result["education_courses"] == ["Machine Learning"]
    assert result["project_descriptions"] == ["churn risk model for trial users"]
    assert result["project_technologies"] == ["Python", "Snowflake"]
    assert result["project_date_ranges"] == ["2024 present"]


def test_cv_fixture_fields_are_supported_by_metric():
    expected = comparable_cv_fields({})
    fixture = load_json(Path(__file__).parent / "fixtures" / "cv_expected.json")
    fixture_fields = {
        field_name
        for cv_fixture in fixture["cvs"]
        for field_name in cv_fixture["fields"]
    }

    assert fixture_fields <= set(expected)


def test_education_text_match_accepts_degree_abbreviations():
    result = score_list_field(
        ["Master of Science in Informatics Computer Science"],
        ["M.Sc. Informatics (Computer Science)"],
    )

    assert result["score"] == 1.0


def test_matching_ndcg_rewards_better_ranked_graded_roles():
    judged = [
        {"role_id": "ideal", "title": "Data Analyst", "relevance": 3},
        {"role_id": "good", "title": "Business Intelligence Analyst", "relevance": 2},
    ]

    best_first = evaluate_matching_roles(
        [
            {"role_id": "ideal", "title": "Data Analyst", "bucket": "ready_now"},
            {"role_id": "good", "title": "Business Intelligence Analyst", "bucket": "next_step"},
        ],
        judged,
    )
    best_second = evaluate_matching_roles(
        [
            {"role_id": "good", "title": "Business Intelligence Analyst", "bucket": "next_step"},
            {"role_id": "ideal", "title": "Data Analyst", "bucket": "ready_now"},
        ],
        judged,
    )

    assert best_first["ndcg_at_9"] > best_second["ndcg_at_9"]


def test_matching_wrong_keyword_role_scores_zero():
    result = evaluate_matching_roles(
        [{"role_id": "wrong", "title": "Data Wizard", "bucket": "ready_now"}],
        [{"role_id": "wrong", "title": "Data Wizard", "relevance": 0}],
    )

    assert result["precision_at_3"] == 0.0
    assert result["mrr_at_9"] == 0.0
    assert result["returned_roles"][0]["relevance"] == 0


def test_matching_duplicate_titles_do_not_inflate_relevance():
    result = evaluate_matching_roles(
        [
            {"role_id": "first", "title": "Data Analyst", "bucket": "ready_now"},
            {"role_id": "copy", "title": "Data Analyst", "bucket": "next_step"},
        ],
        [
            {"role_id": "first", "title": "Data Analyst", "relevance": 3},
            {"role_id": "copy", "title": "Data Analyst", "relevance": 3},
        ],
    )

    assert result["duplicate_titles_at_9"] == 1
    assert result["ndcg_at_9"] == 1.0
    assert result["precision_at_3"] == 1 / 3
    assert result["returned_roles"][1]["relevance"] == 0


def test_matching_bucket_accuracy_uses_only_relevant_judged_roles():
    result = evaluate_matching_roles(
        [
            {"role_id": "good", "title": "Data Analyst", "bucket": "next_step"},
            {"role_id": "bad", "title": "Backend Engineer", "bucket": "ready_now"},
        ],
        [
            {
                "role_id": "good",
                "title": "Data Analyst",
                "relevance": 2,
                "expected_bucket": "ready_now",
            },
            {
                "role_id": "bad",
                "title": "Backend Engineer",
                "relevance": 0,
                "expected_bucket": "aspirational",
            },
        ],
    )

    assert result["bucket_accuracy"] == 0.0
    assert result["bucket_accuracy_count"] == 0
    assert result["bucket_accuracy_total"] == 1


def test_matching_report_shows_unjudged_roles():
    report = {
        "generated_at": "2026-06-29T12:00:00",
        "metadata": {
            "fixture": "metrics/fixtures/matching_profiles.json",
            "embedding_model": "BAAI/bge-base-en-v1.5",
            "catalog_role_count": 486,
        },
        "total_count": 1,
        "success_count": 1,
        "ndcg_at_9": 0.0,
        "precision_at_3": 0.0,
        "mrr_at_9": 0.0,
        "bucket_accuracy": None,
        "duplicate_titles_at_9": 0.0,
        "unjudged_roles_at_9": 1.0,
        "profiles": [
            {
                "name": "sample",
                "status": "ok",
                "bucket_counts": {"ready_now": 1, "next_step": 0, "aspirational": 0},
                "ndcg_at_9": 0.0,
                "precision_at_3": 0.0,
                "mrr_at_9": 0.0,
                "bucket_accuracy": None,
                "duplicate_titles_at_9": 0,
                "unjudged_roles_at_9": 1,
                "returned_roles": [
                    {
                        "rank": 1,
                        "role_id": "new",
                        "title": "Unjudged Role",
                        "bucket": "ready_now",
                        "relevance": 0,
                        "judged": False,
                    }
                ],
            }
        ],
    }

    markdown = render_matching_markdown(report)

    assert "Unjudged Role" in markdown
    assert "unjudged" in markdown


def test_cv_report_renders_three_model_comparison():
    report = {
        "generated_at": "2026-06-29T12:00:00",
        "parsed_output_dir": "metrics/outputs/cv_parses_20260629_120000",
        "fixtures": [{"name": "cv_one"}],
        "models": [
            {
                "model": "small",
                "overall_score": 0.25,
                "success_count": 1,
                "total_count": 1,
                "field_scores": {"skills": 0.25},
                "fixtures": [{"name": "cv_one", "status": "ok", "score": 0.25, "fields": {}}],
            },
            {
                "model": "medium",
                "overall_score": 0.5,
                "success_count": 1,
                "total_count": 1,
                "field_scores": {"skills": 0.5},
                "fixtures": [{"name": "cv_one", "status": "ok", "score": 0.5, "fields": {}}],
            },
            {
                "model": "large",
                "overall_score": 0.75,
                "success_count": 1,
                "total_count": 1,
                "field_scores": {"skills": 0.75},
                "fixtures": [{"name": "cv_one", "status": "ok", "score": 0.75, "fields": {}}],
            },
        ],
    }
    markdown = render_summary_markdown(report)
    detail = render_model_detail_markdown(report, report["models"][0])

    assert "| 3 | `large` | 75.0% | 1/1 | +25.0pp |" in markdown
    assert "| cv_one | 25.0% | 50.0% | 75.0% |" in markdown
    assert "## Field Group Averages" in markdown
    assert "## Details" not in markdown
    assert "# CV Parsing Detail: small" in detail
    assert "## Details" in detail
    assert safe_model_name("gpt/large:test") == "gpt_large_test"


def test_cv_models_load_from_settings_file(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"cv_models": ["small", "medium", "large"]}', encoding="utf-8")

    assert default_models(settings) == ["small", "medium", "large"]
