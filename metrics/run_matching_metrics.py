from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.app.features.role_matching.embedder import MODEL_NAME
from backend.app.features.role_matching.schemas import RecommendationMode, UserCareerProfile
from backend.app.features.role_matching.service import _match_roles_sync
from metrics.common import (
    evaluate_matching_roles,
    format_percent,
    load_json,
    write_timestamped_markdown,
)

METRICS_DIR = Path(__file__).resolve().parent
DEFAULT_FIXTURE = METRICS_DIR / "fixtures" / "matching_profiles.json"
DEFAULT_OUTPUT_DIR = METRICS_DIR / "outputs"


def _role_records_and_buckets(response: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    roles = [
        *response.buckets.ready_now,
        *response.buckets.next_step,
        *response.buckets.aspirational,
    ]
    records = [
        {
            "role_id": str(role.role_id),
            "title": role.job_title,
            "bucket": role.bucket.value,
            "final_score": role.final_score,
            "matched_skills": role.matched_skills,
            "matched_domains": role.matched_domains,
            "signal_breakdown": role.signal_breakdown.model_dump(mode="json"),
        }
        for role in roles
    ]
    bucket_counts = {
        "ready_now": len(response.buckets.ready_now),
        "next_step": len(response.buckets.next_step),
        "aspirational": len(response.buckets.aspirational),
    }
    return records, bucket_counts


def _catalog_role_count() -> int | None:
    try:
        from backend.app.core.database import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM career_roles
                    WHERE capability_embedding IS NOT NULL
                      AND intent_embedding IS NOT NULL
                    """
                )
                return int(cur.fetchone()[0])
    except Exception:
        return None


def _mean(results: list[dict[str, Any]], key: str) -> float:
    return sum(float(result.get(key) or 0.0) for result in results) / len(results) if results else 0.0


def evaluate_matching(fixtures: list[dict[str, Any]], fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    results: list[dict[str, Any]] = []

    for fixture in fixtures:
        try:
            response = _match_roles_sync(
                UserCareerProfile.model_validate(fixture["profile"]),
                top_k=9,
                mode=RecommendationMode.BALANCED,
                include_debug=False,
            )
            roles, bucket_counts = _role_records_and_buckets(response)
            metrics = evaluate_matching_roles(roles, fixture["judged_roles"])
            results.append(
                {
                    "name": fixture["name"],
                    "status": "ok",
                    "bucket_counts": bucket_counts,
                    **metrics,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "name": fixture["name"],
                    "status": "error",
                    "bucket_counts": {"ready_now": 0, "next_step": 0, "aspirational": 0},
                    "ndcg_at_9": 0.0,
                    "precision_at_3": 0.0,
                    "mrr_at_9": 0.0,
                    "bucket_accuracy": None,
                    "bucket_accuracy_count": 0,
                    "bucket_accuracy_total": 0,
                    "duplicate_titles_at_9": 0,
                    "unjudged_roles_at_9": 0,
                    "first_relevant_rank": None,
                    "top_relevant_title": "",
                    "returned_roles": [],
                    "error": str(exc),
                }
            )

    total = len(results)
    bucket_total = sum(result.get("bucket_accuracy_total", 0) for result in results)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "metadata": {
            "fixture": str(fixture_path),
            "embedding_model": MODEL_NAME,
            "catalog_role_count": _catalog_role_count(),
        },
        "total_count": total,
        "success_count": sum(1 for result in results if result["status"] == "ok"),
        "ndcg_at_9": _mean(results, "ndcg_at_9"),
        "precision_at_3": _mean(results, "precision_at_3"),
        "mrr_at_9": _mean(results, "mrr_at_9"),
        "bucket_accuracy": (
            sum(result.get("bucket_accuracy_count", 0) for result in results) / bucket_total
            if bucket_total
            else None
        ),
        "duplicate_titles_at_9": _mean(results, "duplicate_titles_at_9"),
        "unjudged_roles_at_9": _mean(results, "unjudged_roles_at_9"),
        "profiles": results,
    }


def _format_count(value: float | int | None) -> str:
    return "-" if value is None else f"{float(value):.2f}"


def render_markdown(report: dict[str, Any]) -> str:
    metadata = report.get("metadata", {})
    lines = [
        "# Matching Metrics",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Fixture | `{metadata.get('fixture', '-')}` |",
        f"| Embedding model | `{metadata.get('embedding_model', '-')}` |",
        f"| Catalog roles | {metadata.get('catalog_role_count') or '-'} |",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| nDCG@9 | {format_percent(report['ndcg_at_9'])} |",
        f"| Precision@3 | {format_percent(report['precision_at_3'])} |",
        f"| MRR@9 | {format_percent(report['mrr_at_9'])} |",
        f"| Bucket accuracy | {format_percent(report['bucket_accuracy'])} |",
        f"| Duplicate titles@9 | {_format_count(report['duplicate_titles_at_9'])} |",
        f"| Unjudged roles@9 | {_format_count(report['unjudged_roles_at_9'])} |",
        f"| Successful runs | {report['success_count']}/{report['total_count']} |",
        "",
        "## Profiles",
        "",
        "| Profile | nDCG@9 | P@3 | MRR@9 | Bucket acc. | Dups | Unjudged | First relevant role | Buckets |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]

    for result in report["profiles"]:
        buckets = result["bucket_counts"]
        bucket_text = (
            f"ready {buckets['ready_now']}, next {buckets['next_step']}, "
            f"aspirational {buckets['aspirational']}"
        )
        lines.append(
            f"| {result['name']} | {format_percent(result['ndcg_at_9'])} | "
            f"{format_percent(result['precision_at_3'])} | {format_percent(result['mrr_at_9'])} | "
            f"{format_percent(result['bucket_accuracy'])} | "
            f"{result['duplicate_titles_at_9']} | {result['unjudged_roles_at_9']} | "
            f"{result.get('top_relevant_title') or '-'} | {bucket_text} |"
        )

    lines.extend(["", "## Returned Roles"])
    for result in report["profiles"]:
        lines.extend(["", f"### {result['name']}"])
        if result["status"] != "ok":
            lines.append(result.get("error", "No details."))
            continue
        lines.append("")
        lines.append("| Rank | Role ID | Title | Bucket | Relevance | Expected bucket | Judged |")
        lines.append("| ---: | --- | --- | --- | ---: | --- | --- |")
        for role in result["returned_roles"]:
            judged = "yes" if role["judged"] else "unjudged"
            if role.get("duplicate_title"):
                judged = f"{judged}, duplicate"
            lines.append(
                f"| {role['rank']} | {role['role_id']} | {role['title']} | {role['bucket']} | "
                f"{role['relevance']} | {role.get('expected_bucket') or '-'} | {judged} |"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score role matching against fixed profiles.")
    parser.add_argument("--profiles", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = evaluate_matching(load_json(args.profiles)["profiles"], args.profiles)
    path = write_timestamped_markdown(args.output_dir, "matching_metrics", render_markdown(report))
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
