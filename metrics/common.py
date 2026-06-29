from __future__ import annotations

import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


_DEGREE_REPLACEMENTS = (
    (re.compile(r"\bm\s*\.?\s*sc\b"), "master science"),
    (re.compile(r"\bb\s*\.?\s*sc\b"), "bachelor science"),
    (re.compile(r"\bm\s*\.?\s*eng\b"), "master engineering"),
    (re.compile(r"\bb\s*\.?\s*eng\b"), "bachelor engineering"),
    (re.compile(r"\bm\s*\.?\s*a\b"), "master arts"),
    (re.compile(r"\bb\s*\.?\s*a\b"), "bachelor arts"),
    (re.compile(r"\bmsc\b"), "master science"),
    (re.compile(r"\bbsc\b"), "bachelor science"),
)
_LIGHT_STOPWORDS = {"a", "an", "and", "for", "in", "of", "the", "with"}


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.casefold()
    for pattern, replacement in _DEGREE_REPLACEMENTS:
        text = pattern.sub(replacement, text)
    text = re.sub(r"[^\w\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def format_percent(value: float | int | None) -> str:
    return "-" if value is None else f"{float(value) * 100:.1f}%"


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def write_timestamped_markdown(output_dir: Path, prefix: str, markdown: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{prefix}_{timestamp()}.md"
    path.write_text(markdown, encoding="utf-8")
    return path


def score_scalar_field(expected: Any, actual: Any) -> dict[str, Any]:
    expected_norm = normalize_text(expected)
    actual_norm = normalize_text(actual)
    return {
        "expected": expected,
        "actual": actual,
        "score": 1.0 if _text_match(expected_norm, actual_norm) else 0.0,
    }


def _text_match(expected: str, actual: str) -> bool:
    if _direct_text_match(expected, actual):
        return True
    return _direct_text_match(_without_light_stopwords(expected), _without_light_stopwords(actual))


def _direct_text_match(expected: str, actual: str) -> bool:
    return expected == actual or bool(
        expected and len(expected) >= 4 and (expected in actual or actual in expected)
    )


def _without_light_stopwords(text: str) -> str:
    return " ".join(token for token in text.split() if token not in _LIGHT_STOPWORDS)


def score_list_field(expected: list[Any], actual: list[Any]) -> dict[str, Any]:
    expected_set = sorted({normal for item in expected if (normal := normalize_text(item))})
    actual_set = sorted({normal for item in actual if (normal := normalize_text(item))})
    used_actual: set[str] = set()
    matched_expected: set[str] = set()

    for expected_item in expected_set:
        match = next(
            (
                actual_item
                for actual_item in actual_set
                if actual_item not in used_actual and _text_match(expected_item, actual_item)
            ),
            None,
        )
        if match is not None:
            matched_expected.add(expected_item)
            used_actual.add(match)

    if not expected_set and not actual_set:
        precision = recall = f1 = 1.0
    else:
        precision = len(used_actual) / len(actual_set) if actual_set else 0.0
        recall = len(matched_expected) / len(expected_set) if expected_set else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "expected_count": len(expected_set),
        "actual_count": len(actual_set),
        "matched_count": len(matched_expected),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "score": f1,
        "missing": sorted(set(expected_set) - matched_expected),
        "extra": sorted(set(actual_set) - used_actual),
    }


def _as_dict(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json") if hasattr(value, "model_dump") else value


def _items(data: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = data.get(key) or []
    return value if isinstance(value, list) else []


def _field(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _join_parts(*parts: Any) -> str:
    return " ".join(str(part).strip() for part in parts if str(part or "").strip())


def _date_range(item: dict[str, Any]) -> str:
    text = _join_parts(item.get("start_date"), item.get("end_date"))
    years = re.findall(r"\b(?:19|20)\d{2}\b", text)
    if re.search(r"\b(?:present|current|now|ongoing)\b", text, re.IGNORECASE):
        years.append("present")
    return " ".join(dict.fromkeys(years))


def _flatten(items: list[dict[str, Any]], key: str) -> list[str]:
    values: list[str] = []
    for item in items:
        value = item.get(key)
        if isinstance(value, list):
            values.extend(str(entry) for entry in value if str(entry or "").strip())
        elif str(value or "").strip():
            values.append(str(value))
    return values


def comparable_cv_fields(cv_data: Any) -> dict[str, Any]:
    data = _as_dict(cv_data)
    experience = _items(data, "experience")
    education = _items(data, "education")
    projects = _items(data, "projects")
    certifications = _items(data, "certifications")
    thesis = _items(data, "thesis")
    skills = _field(data, "skills_extracted") or {}

    technical_skills = [
        item.get("name")
        for item in skills.get("technical_skills", [])
        if isinstance(item, dict) and item.get("name")
    ]
    soft_skills = [
        item for item in skills.get("soft_skills", []) if isinstance(item, str) and item.strip()
    ]
    languages = [
        _join_parts(item.get("language"), item.get("level"))
        for item in skills.get("languages", [])
        if isinstance(item, dict) and item.get("language")
    ]

    return {
        "full_name": _field(data, "personal_info", "full_name"),
        "email": _field(data, "personal_info", "email"),
        "phone": _field(data, "personal_info", "phone"),
        "location": _field(data, "personal_info", "location"),
        "current_role": _field(data, "personal_info", "current_role"),
        "links": _field(data, "personal_info", "links") or [],
        "profile_summary": _field(data, "profile_summary", "summary"),
        "current_seniority_level": _field(data, "profile_summary", "current_seniority_level"),
        "years_of_experience": _field(data, "profile_summary", "years_of_experience"),
        "experience_roles": _flatten(experience, "role"),
        "experience_organizations": _flatten(experience, "organization"),
        "experience_industries": _flatten(experience, "industry"),
        "experience_locations": _flatten(experience, "location"),
        "experience_date_ranges": [
            date_range for item in experience if (date_range := _date_range(item))
        ],
        "experience_responsibilities": _flatten(experience, "core_responsibilities"),
        "experience_contextual_skills": _flatten(experience, "contextual_skills"),
        "education_entry_types": _flatten(education, "entry_type"),
        "education": [
            degree
            for item in education
            if (degree := _join_parts(item.get("degree_type"), item.get("field_of_study")))
        ],
        "education_institutions": _flatten(education, "institution"),
        "education_date_ranges": [
            date_range for item in education if (date_range := _date_range(item))
        ],
        "education_grades": _flatten(education, "grade"),
        "education_theses": _flatten(education, "thesis_title"),
        "education_courses": _flatten(education, "courses"),
        "skills": [*technical_skills, *soft_skills],
        "languages": languages,
        "interests": [
            item for item in data.get("interests", []) if isinstance(item, str) and item.strip()
        ],
        "projects": _flatten(projects, "title"),
        "project_organizations": _flatten(projects, "organization"),
        "project_roles": _flatten(projects, "role"),
        "project_descriptions": _flatten(projects, "description"),
        "project_technologies": _flatten(projects, "technologies"),
        "project_outcomes": _flatten(projects, "outcomes"),
        "project_links": _flatten(projects, "links"),
        "project_date_ranges": [
            date_range for item in projects if (date_range := _date_range(item))
        ],
        "certifications": _flatten(certifications, "name"),
        "certification_issuers": _flatten(certifications, "issuing_organization"),
        "certification_issue_dates": _flatten(certifications, "issue_date"),
        "certification_expiration_dates": _flatten(certifications, "expiration_date"),
        "thesis_titles": _flatten(thesis, "title"),
        "thesis_technologies": _flatten(thesis, "technologies"),
    }


def score_cv_fixture(expected_fields: dict[str, Any], actual_cv_data: Any) -> dict[str, Any]:
    actual_fields = comparable_cv_fields(actual_cv_data)
    fields: dict[str, dict[str, Any]] = {}

    for field_name, expected_value in expected_fields.items():
        actual_value = actual_fields.get(field_name)
        if isinstance(expected_value, list):
            actual_list = actual_value if isinstance(actual_value, list) else []
            fields[field_name] = score_list_field(expected_value, actual_list)
        else:
            fields[field_name] = score_scalar_field(expected_value, actual_value)

    scores = [field["score"] for field in fields.values()]
    return {"score": sum(scores) / len(scores) if scores else 0.0, "fields": fields}


def _role_title(role: dict[str, Any]) -> str:
    return str(role.get("title") or role.get("job_title") or "")


def _role_bucket(role: dict[str, Any]) -> str:
    bucket = role.get("bucket") or ""
    return str(getattr(bucket, "value", bucket))


def _judgment_maps(judged_roles: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_id: dict[str, dict[str, Any]] = {}
    by_title: dict[str, dict[str, Any]] = {}
    for judgment in judged_roles:
        item = dict(judgment)
        item["relevance"] = int(item.get("relevance") or 0)
        role_id = str(item.get("role_id") or "")
        title_key = normalize_text(item.get("title"))
        if role_id:
            by_id[role_id] = item
        if title_key:
            by_title.setdefault(title_key, item)
    return by_id, by_title


def _dcg(relevances: list[int]) -> float:
    return sum((2**relevance - 1) / math.log2(rank + 2) for rank, relevance in enumerate(relevances))


def _ideal_relevances(judged_roles: list[dict[str, Any]], k: int) -> list[int]:
    best_by_title: dict[str, int] = {}
    for judgment in judged_roles:
        key = normalize_text(judgment.get("title")) or str(judgment.get("role_id") or "")
        if not key:
            continue
        relevance = int(judgment.get("relevance") or 0)
        best_by_title[key] = max(best_by_title.get(key, 0), relevance)
    return sorted(best_by_title.values(), reverse=True)[:k]


def evaluate_matching_roles(
    roles: list[dict[str, Any]],
    judged_roles: list[dict[str, Any]],
    *,
    k: int = 9,
) -> dict[str, Any]:
    top_roles = roles[:k]
    judgments_by_id, judgments_by_title = _judgment_maps(judged_roles)
    seen_titles: set[str] = set()
    relevances: list[int] = []
    returned_roles: list[dict[str, Any]] = []
    bucket_matches = 0
    bucket_total = 0
    duplicate_titles = 0
    unjudged_roles = 0

    for rank, role in enumerate(top_roles, start=1):
        role_id = str(role.get("role_id") or "")
        title = _role_title(role)
        title_key = normalize_text(title)
        judgment = judgments_by_id.get(role_id) or judgments_by_title.get(title_key)
        judged = judgment is not None
        duplicate = bool(title_key and title_key in seen_titles)
        if title_key:
            seen_titles.add(title_key)
        if duplicate:
            duplicate_titles += 1

        raw_relevance = int(judgment.get("relevance") or 0) if judgment else 0
        relevance = 0 if duplicate else raw_relevance
        bucket = _role_bucket(role)
        expected_bucket = str(judgment.get("expected_bucket") or "") if judgment else ""

        if not judged:
            unjudged_roles += 1
        if judged and relevance > 0 and expected_bucket:
            bucket_total += 1
            if bucket == expected_bucket:
                bucket_matches += 1

        relevances.append(relevance)
        returned_roles.append(
            {
                "rank": rank,
                "role_id": role_id,
                "title": title,
                "bucket": bucket,
                "relevance": relevance,
                "raw_relevance": raw_relevance,
                "expected_bucket": expected_bucket,
                "judged": judged,
                "duplicate_title": duplicate,
                "final_score": role.get("final_score"),
                "matched_skills": role.get("matched_skills", []),
                "matched_domains": role.get("matched_domains", []),
                "signal_breakdown": role.get("signal_breakdown", {}),
            }
        )

    ideal_relevances = _ideal_relevances(judged_roles, k)
    ideal_dcg = _dcg(ideal_relevances)
    first_relevant_rank = next(
        (rank for rank, relevance in enumerate(relevances, start=1) if relevance > 0),
        None,
    )

    return {
        "ndcg_at_9": _dcg(relevances) / ideal_dcg if ideal_dcg else 0.0,
        "precision_at_3": sum(1 for relevance in relevances[:3] if relevance > 0) / 3,
        "mrr_at_9": 1 / first_relevant_rank if first_relevant_rank else 0.0,
        "bucket_accuracy": bucket_matches / bucket_total if bucket_total else None,
        "bucket_accuracy_count": bucket_matches,
        "bucket_accuracy_total": bucket_total,
        "duplicate_titles_at_9": duplicate_titles,
        "unjudged_roles_at_9": unjudged_roles,
        "judged_roles_at_9": len(top_roles) - unjudged_roles,
        "relevant_roles_at_9": sum(1 for relevance in relevances if relevance > 0),
        "first_relevant_rank": first_relevant_rank,
        "top_relevant_title": returned_roles[first_relevant_rank - 1]["title"]
        if first_relevant_rank
        else "",
        "returned_roles": returned_roles,
    }
