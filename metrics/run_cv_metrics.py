from __future__ import annotations

import argparse
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.core.openai_client import openai_client_lifespan
from backend.app.features.cv_parsing.service import (
    extract_text_from_pdf_bytes,
    parse_cv_to_pydantic,
)
from metrics.common import format_percent, load_json, score_cv_fixture

ROOT = Path(__file__).resolve().parents[1]
METRICS_DIR = Path(__file__).resolve().parent
DEFAULT_FIXTURE = METRICS_DIR / "fixtures" / "cv_expected.json"
DEFAULT_OUTPUT_DIR = METRICS_DIR / "outputs"
DEFAULT_SETTINGS = METRICS_DIR / "settings.json"
FIELD_GROUPS = {
    "Contact and identity": {
        "full_name",
        "email",
        "phone",
        "location",
        "current_role",
        "links",
        "years_of_experience",
    },
    "Experience": {
        "experience_roles",
        "experience_organizations",
        "experience_industries",
        "experience_locations",
        "experience_date_ranges",
        "experience_responsibilities",
        "experience_contextual_skills",
    },
    "Education": {
        "education_entry_types",
        "education",
        "education_institutions",
        "education_date_ranges",
        "education_grades",
        "education_theses",
        "education_courses",
    },
    "Skills and interests": {"skills", "languages", "interests"},
    "Projects and certifications": {
        "projects",
        "project_organizations",
        "project_roles",
        "project_descriptions",
        "project_technologies",
        "project_outcomes",
        "project_links",
        "project_date_ranges",
        "certifications",
        "certification_issuers",
        "certification_issue_dates",
        "certification_expiration_dates",
        "thesis_titles",
        "thesis_technologies",
    },
}


def default_models(settings_path: Path = DEFAULT_SETTINGS) -> list[str]:
    settings = load_json(settings_path)
    return [str(model) for model in settings.get("cv_models", []) if str(model).strip()]


def safe_model_name(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", model).strip("_")


async def parse_and_score_cv(
    fixture: dict[str, Any],
    *,
    model: str,
    parsed_output_dir: Path,
) -> dict[str, Any]:
    pdf_path = ROOT / fixture["pdf"]
    parsed_path = parsed_output_dir / safe_model_name(model) / f"{pdf_path.stem}.json"
    try:
        raw_text = extract_text_from_pdf_bytes(pdf_path.read_bytes())
        parsed = await parse_cv_to_pydantic(raw_text, model=model)
        parsed_path.parent.mkdir(parents=True, exist_ok=True)
        parsed_path.write_text(parsed.model_dump_json(indent=2), encoding="utf-8")
        scored = score_cv_fixture(fixture["fields"], parsed)
        return {
            "name": fixture["name"],
            "status": "ok",
            "parsed_path": str(parsed_path),
            **scored,
        }
    except Exception as exc:
        return {
            "name": fixture["name"],
            "status": "error",
            "score": 0.0,
            "fields": {},
            "parsed_path": str(parsed_path),
            "error": str(exc),
        }


def summarize_model(model: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    field_scores: dict[str, list[float]] = {}
    for result in results:
        for field_name, field_result in result.get("fields", {}).items():
            field_scores.setdefault(field_name, []).append(field_result["score"])

    return {
        "model": model,
        "total_count": len(results),
        "success_count": sum(1 for result in results if result["status"] == "ok"),
        "overall_score": sum(result["score"] for result in results) / len(results)
        if results
        else 0.0,
        "field_scores": {
            name: sum(scores) / len(scores) for name, scores in sorted(field_scores.items())
        },
        "fixtures": results,
    }


async def evaluate_cv_models(
    fixtures: list[dict[str, Any]],
    *,
    models: list[str],
    parsed_output_dir: Path,
) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    async with openai_client_lifespan():
        for model in models:
            results = [
                await parse_and_score_cv(
                    fixture,
                    model=model,
                    parsed_output_dir=parsed_output_dir,
                )
                for fixture in fixtures
            ]
            reports.append(summarize_model(model, results))
    return reports


def score_for_cv(model_report: dict[str, Any], cv_name: str) -> float | None:
    for result in model_report["fixtures"]:
        if result["name"] == cv_name:
            return result["score"]
    return None


def grouped_field_scores(model_report: dict[str, Any]) -> dict[str, float]:
    scores = model_report["field_scores"]
    grouped: dict[str, float] = {}
    for group_name, field_names in FIELD_GROUPS.items():
        values = [scores[field_name] for field_name in field_names if field_name in scores]
        if values:
            grouped[group_name] = sum(values) / len(values)
    return grouped


def render_summary_markdown(report: dict[str, Any]) -> str:
    models = report["models"]
    lines = [
        "# CV Parsing Summary",
        "",
        f"Generated: {report['generated_at']}",
        f"Fresh parsed JSON: `{report['parsed_output_dir']}`",
        "",
        "## Headline",
        "",
        "| Level | Model | Overall CV score | Parsed successfully | Delta vs previous |",
        "| ---: | --- | ---: | ---: | ---: |",
    ]

    previous_score: float | None = None
    for index, model_report in enumerate(models, start=1):
        score = model_report["overall_score"]
        delta = "-" if previous_score is None else f"{(score - previous_score) * 100:+.1f}pp"
        previous_score = score
        lines.append(
            f"| {index} | `{model_report['model']}` | {format_percent(score)} | "
            f"{model_report['success_count']}/{model_report['total_count']} | {delta} |"
        )

    cv_names = [fixture["name"] for fixture in report["fixtures"]]
    lines.extend(["", "## Per-CV Scores", "", "| CV | " + " | ".join(f"`{m['model']}`" for m in models) + " |"])
    lines.append("| --- | " + " | ".join("---:" for _ in models) + " |")
    for cv_name in cv_names:
        scores = [format_percent(score_for_cv(model_report, cv_name)) for model_report in models]
        lines.append(f"| {cv_name} | " + " | ".join(scores) + " |")

    group_names = list(FIELD_GROUPS)
    lines.extend(["", "## Field Group Averages", "", "| Group | " + " | ".join(f"`{m['model']}`" for m in models) + " |"])
    lines.append("| --- | " + " | ".join("---:" for _ in models) + " |")
    for group_name in group_names:
        scores = [
            format_percent(grouped_field_scores(model_report).get(group_name))
            for model_report in models
        ]
        lines.append(f"| {group_name} | " + " | ".join(scores) + " |")

    lines.append("")
    return "\n".join(lines)


def render_model_detail_markdown(report: dict[str, Any], model_report: dict[str, Any]) -> str:
    lines = [
        f"# CV Parsing Detail: {model_report['model']}",
        "",
        f"Generated: {report['generated_at']}",
        f"Fresh parsed JSON: `{report['parsed_output_dir']}`",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Overall CV score | {format_percent(model_report['overall_score'])} |",
        f"| Parsed successfully | {model_report['success_count']}/{model_report['total_count']} |",
        "",
        "## Per-CV Scores",
        "",
        "| CV | Status | Score | Fields scored |",
        "| --- | --- | ---: | ---: |",
    ]
    for result in model_report["fixtures"]:
        lines.append(
            f"| {result['name']} | {result['status']} | "
            f"{format_percent(result['score'])} | {len(result.get('fields', {}))} |"
        )

    lines.extend(["", "## Field Averages", "", "| Field | Average score |", "| --- | ---: |"])
    for field_name, score in model_report["field_scores"].items():
        lines.append(f"| {field_name} | {format_percent(score)} |")

    lines.extend(["", "## Details"])
    for result in model_report["fixtures"]:
        lines.extend(["", f"### {result['name']}"])
        if result["status"] != "ok":
            lines.append(result.get("error", "No details."))
            continue
        lines.append(f"Parsed JSON: `{result.get('parsed_path', '-')}`")
        lines.extend(["", "| Field | Score | Expected | Actual | Missing |", "| --- | ---: | ---: | ---: | --- |"])
        for field_name, field in result["fields"].items():
            if "expected_count" in field:
                missing = ", ".join(field["missing"][:8])
                if len(field["missing"]) > 8:
                    missing += ", ..."
                lines.append(
                    f"| {field_name} | {format_percent(field['score'])} | "
                    f"{field['expected_count']} | {field['actual_count']} | {missing or '-'} |"
                )
            else:
                lines.append(
                    f"| {field_name} | {format_percent(field['score'])} | 1 | 1 | "
                    f"{'-' if field['score'] else field['expected']} |"
                )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse CVs with three OpenAI models and compare extraction scores.")
    parser.add_argument("--expected", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    models = default_models(args.settings)
    if len(models) != 3:
        raise SystemExit(f"Set exactly three models in {args.settings}.")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    parsed_output_dir = args.output_dir / f"cv_parses_{run_id}"
    fixtures = load_json(args.expected)["cvs"]
    model_reports = asyncio.run(
        evaluate_cv_models(
            fixtures,
            models=models,
            parsed_output_dir=parsed_output_dir,
        )
    )
    report = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "parsed_output_dir": str(parsed_output_dir),
        "fixtures": fixtures,
        "models": model_reports,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / f"cv_metrics_summary_{run_id}.md"
    summary_path.write_text(render_summary_markdown(report), encoding="utf-8")
    print(f"Wrote {summary_path}")

    for model_report in model_reports:
        detail_path = args.output_dir / f"cv_metrics_detail_{safe_model_name(model_report['model'])}_{run_id}.md"
        detail_path.write_text(
            render_model_detail_markdown(report, model_report),
            encoding="utf-8",
        )
        print(f"Wrote {detail_path}")


if __name__ == "__main__":
    main()
