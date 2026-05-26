#!/usr/bin/env python3
"""Import ESCO skills linked to already-imported ESCO occupations.

One-time database population script. Kept for auditability and controlled
reruns while rebuilding the seeded Career Compass database; not app runtime
code. Prefer --dry-run before any write-mode rerun.

Phase 4b reads the official ESCO English skills and occupation-skill relation
CSVs, keeps only relations whose occupation URI already exists in
`esco_occupations`, imports only the skills needed by those relations, and then
imports the matching relation rows into `esco_occupation_skills`.

Examples:

    python scripts/import_esco_skills.py \
      --skills-csv data/raw/esco/skills_en.csv \
      --relations-csv data/raw/esco/occupationSkillRelations_en.csv \
      --dry-run

    python scripts/import_esco_skills.py \
      --skills-csv data/raw/esco/skills_en.csv \
      --relations-csv data/raw/esco/occupationSkillRelations_en.csv

For dry runs and real imports, set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in
your local shell environment or in a local .env file. Never expose the service
role key in frontend/client code.
"""

from __future__ import annotations

import argparse
import collections
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


BATCH_SIZE = 500
LOOKUP_FILTER_BATCH_SIZE = 100
DEFAULT_SKILLS_REVIEW_OUTPUT = Path("data/esco_skills_import_review.csv")
DEFAULT_MISSING_SKILLS_OUTPUT = Path("data/esco_missing_skills_review.csv")
DEFAULT_RELATIONS_REVIEW_OUTPUT = Path(
    "data/esco_occupation_skill_relations_review.csv"
)
EXPECTED_RELATION_TYPES = {"essential", "optional"}


SKILL_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "esco_skill_uri": (
        "conceptUri",
        "Concept URI",
        "skillUri",
        "Skill URI",
        "skill_uri",
    ),
    "skill_type": ("skillType", "Skill type", "skill_type"),
    "reuse_level": ("reuseLevel", "Reuse level", "reuse_level"),
    "preferred_label": ("preferredLabel", "Concept PT", "Preferred label"),
    "alt_labels": ("altLabels", "Alt labels", "Alternative labels"),
    "hidden_labels": ("hiddenLabels", "Hidden labels"),
    "description": ("description", "Description"),
    "scope_note": ("scopeNote", "Scope note", "scope_note"),
}

RELATION_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "occupation_uri": (
        "occupationUri",
        "occupation_uri",
        "occupation concept URI",
        "Occupation concept URI",
        "occupationConceptUri",
    ),
    "skill_uri": (
        "skillUri",
        "skill_uri",
        "skill concept URI",
        "Skill concept URI",
        "skillConceptUri",
    ),
    "relation_type": (
        "relationType",
        "Relation type",
        "Relationship type",
        "relationshipType",
        "relation_type",
    ),
    "skill_type": ("skillType", "Skill type", "skill_type"),
}


@dataclass(frozen=True)
class SchemaConfig:
    occupations_table: str = "esco_occupations"
    skills_table: str = "esco_skills"
    occupation_skills_table: str = "esco_occupation_skills"
    esco_uri_column: str = "esco_uri"
    esco_skill_uri_column: str = "esco_skill_uri"
    skill_type_column: str = "skill_type"
    reuse_level_column: str = "reuse_level"
    preferred_label_column: str = "preferred_label"
    alt_labels_column: str = "alt_labels"
    hidden_labels_column: str = "hidden_labels"
    description_column: str = "description"
    scope_note_column: str = "scope_note"
    relation_type_column: str = "relation_type"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass(frozen=True)
class SkillColumnMapping:
    esco_skill_uri: str | None
    skill_type: str | None
    reuse_level: str | None
    preferred_label: str | None
    alt_labels: str | None
    hidden_labels: str | None
    description: str | None
    scope_note: str | None


@dataclass(frozen=True)
class RelationColumnMapping:
    occupation_uri: str | None
    skill_uri: str | None
    relation_type: str | None
    skill_type: str | None


@dataclass(frozen=True)
class EscoSkill:
    esco_skill_uri: str
    skill_type: str | None
    reuse_level: str | None
    preferred_label: str
    alt_labels: str | None
    hidden_labels: str | None
    description: str | None
    scope_note: str | None

    def to_payload(self, schema: SchemaConfig = DEFAULT_SCHEMA) -> dict[str, Any]:
        return {
            schema.esco_skill_uri_column: self.esco_skill_uri,
            schema.skill_type_column: self.skill_type,
            schema.reuse_level_column: self.reuse_level,
            schema.preferred_label_column: self.preferred_label,
            schema.alt_labels_column: self.alt_labels,
            schema.hidden_labels_column: self.hidden_labels,
            schema.description_column: self.description,
            schema.scope_note_column: self.scope_note,
        }


@dataclass(frozen=True)
class EscoOccupationSkill:
    esco_uri: str
    esco_skill_uri: str
    relation_type: str
    skill_type: str | None

    def identity_key(self) -> tuple[str, str, str]:
        return (self.esco_uri, self.esco_skill_uri, self.relation_type)

    def to_payload(self, schema: SchemaConfig = DEFAULT_SCHEMA) -> dict[str, Any]:
        return {
            schema.esco_uri_column: self.esco_uri,
            schema.esco_skill_uri_column: self.esco_skill_uri,
            schema.relation_type_column: self.relation_type,
            schema.skill_type_column: self.skill_type,
        }


@dataclass(frozen=True)
class SkillReviewRow:
    esco_skill_uri: str
    preferred_label: str
    skill_type: str | None
    reuse_level: str | None
    included: bool
    skip_reason: str


@dataclass(frozen=True)
class MissingSkillRow:
    esco_skill_uri: str
    relation_count: int
    reason: str


@dataclass(frozen=True)
class RelationReviewRow:
    esco_uri: str
    esco_skill_uri: str
    relation_type: str
    included: bool
    skip_reason: str


@dataclass
class RelationParseStats:
    total_relation_rows_read: int = 0
    relation_rows_linked_to_existing_occupations: int = 0
    rows_skipped_missing_occupation_uri: int = 0
    rows_skipped_missing_skill_uri: int = 0
    rows_skipped_occupation_not_imported: int = 0
    rows_skipped_duplicate_relation: int = 0


@dataclass
class SkillParseStats:
    total_skills_rows_read: int = 0
    rows_skipped_missing_skill_uri: int = 0
    rows_skipped_not_needed: int = 0
    rows_skipped_missing_preferred_label: int = 0
    rows_skipped_duplicate_skill_uri: int = 0
    rows_included: int = 0


@dataclass(frozen=True)
class RelationParseResult:
    relations: list[EscoOccupationSkill]
    review_rows: list[RelationReviewRow]
    stats: RelationParseStats
    detected_columns: list[str]
    detected_mapping: RelationColumnMapping
    needed_skill_uris: set[str]
    skill_uri_relation_counts: collections.Counter[str]
    relation_type_counts: collections.Counter[str]
    unusual_relation_types: set[str]


@dataclass(frozen=True)
class SkillParseResult:
    skills: list[EscoSkill]
    review_rows: list[SkillReviewRow]
    missing_skills: list[MissingSkillRow]
    stats: SkillParseStats
    detected_columns: list[str]
    detected_mapping: SkillColumnMapping


@dataclass
class ImportStats:
    skills_inserted: int = 0
    skills_updated: int = 0
    skills_reused: int = 0
    relations_inserted: int = 0
    relations_updated: int = 0
    relations_reused: int = 0

    def merge(self, other: "ImportStats") -> None:
        self.skills_inserted += other.skills_inserted
        self.skills_updated += other.skills_updated
        self.skills_reused += other.skills_reused
        self.relations_inserted += other.relations_inserted
        self.relations_updated += other.relations_updated
        self.relations_reused += other.relations_reused


class SupabaseError(RuntimeError):
    """Raised when Supabase returns an error response."""


def normalize_supabase_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            "SUPABASE_URL must be a full URL, such as "
            "https://your-project-ref.supabase.co"
        )

    dashboard_prefix = "/dashboard/project/"
    if parsed.netloc == "supabase.com" and parsed.path.startswith(dashboard_prefix):
        project_ref = parsed.path[len(dashboard_prefix) :].split("/", 1)[0]
        if project_ref:
            return f"https://{project_ref}.supabase.co"

    return value.strip().rstrip("/")


def load_dotenv_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name or name in os.environ:
            continue

        if (
            (value.startswith('"') and value.endswith('"'))
            or (value.startswith("'") and value.endswith("'"))
        ):
            value = value[1:-1]

        os.environ[name] = value


def get_required_env() -> tuple[str, str]:
    load_dotenv_file(Path(".env"))
    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    missing = []
    if not supabase_url:
        missing.append("SUPABASE_URL")
    if not service_role_key:
        missing.append("SUPABASE_SERVICE_ROLE_KEY")
    if missing:
        raise ValueError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )
    if service_role_key.startswith("sb_publishable_"):
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY must be a secret key "
            "(sb_secret_...) or legacy service_role JWT, not a publishable key."
        )

    return supabase_url, service_role_key


def read_csv_text(path: Path) -> str:
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as error:
            last_error = error

    if last_error is not None:
        raise UnicodeDecodeError(
            last_error.encoding,
            last_error.object,
            last_error.start,
            last_error.end,
            "CSV could not be decoded as UTF-8 or Windows-1252.",
        )

    raise ValueError(f"Could not read CSV file: {path}")


def normalize_column_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def detect_column(fieldnames: Sequence[str], aliases: Sequence[str]) -> str | None:
    normalized_fieldnames = {
        normalize_column_name(fieldname): fieldname for fieldname in fieldnames
    }
    for alias in aliases:
        detected = normalized_fieldnames.get(normalize_column_name(alias))
        if detected is not None:
            return detected
    return None


def detect_skill_columns(fieldnames: Sequence[str]) -> SkillColumnMapping:
    return SkillColumnMapping(
        esco_skill_uri=detect_column(fieldnames, SKILL_COLUMN_ALIASES["esco_skill_uri"]),
        skill_type=detect_column(fieldnames, SKILL_COLUMN_ALIASES["skill_type"]),
        reuse_level=detect_column(fieldnames, SKILL_COLUMN_ALIASES["reuse_level"]),
        preferred_label=detect_column(
            fieldnames,
            SKILL_COLUMN_ALIASES["preferred_label"],
        ),
        alt_labels=detect_column(fieldnames, SKILL_COLUMN_ALIASES["alt_labels"]),
        hidden_labels=detect_column(fieldnames, SKILL_COLUMN_ALIASES["hidden_labels"]),
        description=detect_column(fieldnames, SKILL_COLUMN_ALIASES["description"]),
        scope_note=detect_column(fieldnames, SKILL_COLUMN_ALIASES["scope_note"]),
    )


def detect_relation_columns(fieldnames: Sequence[str]) -> RelationColumnMapping:
    return RelationColumnMapping(
        occupation_uri=detect_column(
            fieldnames,
            RELATION_COLUMN_ALIASES["occupation_uri"],
        ),
        skill_uri=detect_column(fieldnames, RELATION_COLUMN_ALIASES["skill_uri"]),
        relation_type=detect_column(
            fieldnames,
            RELATION_COLUMN_ALIASES["relation_type"],
        ),
        skill_type=detect_column(fieldnames, RELATION_COLUMN_ALIASES["skill_type"]),
    )


def require_skill_columns(mapping: SkillColumnMapping) -> None:
    missing = []
    if mapping.esco_skill_uri is None:
        missing.append("conceptUri or Concept URI")
    if mapping.preferred_label is None:
        missing.append("preferredLabel or Concept PT")
    if missing:
        raise ValueError("skills CSV is missing required column(s): " + ", ".join(missing))


def require_relation_columns(mapping: RelationColumnMapping) -> None:
    missing = []
    if mapping.occupation_uri is None:
        missing.append("occupationUri or occupation concept URI")
    if mapping.skill_uri is None:
        missing.append("skillUri or skill concept URI")
    if missing:
        raise ValueError(
            "occupation-skill relations CSV is missing required column(s): "
            + ", ".join(missing)
        )


def clean_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        key: "" if value is None else str(value).strip()
        for key, value in row.items()
        if key is not None
    }


def get_optional(row: Mapping[str, str], column: str | None) -> str:
    if column is None:
        return ""
    return row.get(column, "").strip()


def get_nullable(row: Mapping[str, str], column: str | None) -> str | None:
    value = get_optional(row, column)
    return value or None


def normalize_relation_type(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def validate_csv_path(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    if not path.is_file():
        raise ValueError(f"CSV path is not a file: {path}")


def parse_relations_csv(
    relations_csv_path: Path | str,
    existing_occupation_uris: set[str],
) -> RelationParseResult:
    path = Path(relations_csv_path)
    validate_csv_path(path)

    stats = RelationParseStats()
    relations: list[EscoOccupationSkill] = []
    review_rows: list[RelationReviewRow] = []
    relation_keys: set[tuple[str, str, str]] = set()
    needed_skill_uris: set[str] = set()
    skill_uri_relation_counts: collections.Counter[str] = collections.Counter()
    relation_type_counts: collections.Counter[str] = collections.Counter()
    unusual_relation_types: set[str] = set()

    csv_text = read_csv_text(path)
    with io.StringIO(csv_text, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("relations CSV file is empty or missing a header row.")

        fieldnames = list(reader.fieldnames)
        mapping = detect_relation_columns(fieldnames)
        require_relation_columns(mapping)

        for raw_row in reader:
            stats.total_relation_rows_read += 1
            row = clean_row(raw_row)
            esco_uri = get_optional(row, mapping.occupation_uri)
            esco_skill_uri = get_optional(row, mapping.skill_uri)
            relation_type = normalize_relation_type(
                get_optional(row, mapping.relation_type)
            )
            skill_type = get_nullable(row, mapping.skill_type)

            if not esco_uri:
                stats.rows_skipped_missing_occupation_uri += 1
                review_rows.append(
                    RelationReviewRow(
                        esco_uri="",
                        esco_skill_uri=esco_skill_uri,
                        relation_type=relation_type,
                        included=False,
                        skip_reason="missing_occupation_uri",
                    )
                )
                continue
            if not esco_skill_uri:
                stats.rows_skipped_missing_skill_uri += 1
                review_rows.append(
                    RelationReviewRow(
                        esco_uri=esco_uri,
                        esco_skill_uri="",
                        relation_type=relation_type,
                        included=False,
                        skip_reason="missing_skill_uri",
                    )
                )
                continue
            if esco_uri not in existing_occupation_uris:
                stats.rows_skipped_occupation_not_imported += 1
                review_rows.append(
                    RelationReviewRow(
                        esco_uri=esco_uri,
                        esco_skill_uri=esco_skill_uri,
                        relation_type=relation_type,
                        included=False,
                        skip_reason="occupation_not_imported",
                    )
                )
                continue

            stats.relation_rows_linked_to_existing_occupations += 1
            needed_skill_uris.add(esco_skill_uri)
            skill_uri_relation_counts[esco_skill_uri] += 1
            relation = EscoOccupationSkill(
                esco_uri=esco_uri,
                esco_skill_uri=esco_skill_uri,
                relation_type=relation_type,
                skill_type=skill_type,
            )
            key = relation.identity_key()
            if key in relation_keys:
                stats.rows_skipped_duplicate_relation += 1
                review_rows.append(
                    RelationReviewRow(
                        esco_uri=esco_uri,
                        esco_skill_uri=esco_skill_uri,
                        relation_type=relation_type,
                        included=False,
                        skip_reason="duplicate_relation",
                    )
                )
                continue

            relation_keys.add(key)
            relations.append(relation)
            relation_type_counts[relation_type] += 1
            if relation_type and relation_type not in EXPECTED_RELATION_TYPES:
                unusual_relation_types.add(relation_type)
            review_rows.append(
                RelationReviewRow(
                    esco_uri=esco_uri,
                    esco_skill_uri=esco_skill_uri,
                    relation_type=relation_type,
                    included=True,
                    skip_reason="",
                )
            )

    return RelationParseResult(
        relations=relations,
        review_rows=review_rows,
        stats=stats,
        detected_columns=fieldnames,
        detected_mapping=mapping,
        needed_skill_uris=needed_skill_uris,
        skill_uri_relation_counts=skill_uri_relation_counts,
        relation_type_counts=relation_type_counts,
        unusual_relation_types=unusual_relation_types,
    )


def parse_skills_csv(
    skills_csv_path: Path | str,
    needed_skill_uris: set[str],
    needed_skill_relation_counts: Mapping[str, int] | None = None,
) -> SkillParseResult:
    path = Path(skills_csv_path)
    validate_csv_path(path)

    relation_counts = needed_skill_relation_counts or {}
    stats = SkillParseStats()
    skills_by_uri: dict[str, EscoSkill] = {}
    review_rows: list[SkillReviewRow] = []
    found_needed_skill_uris: set[str] = set()
    invalid_needed_skill_reasons: dict[str, str] = {}

    csv_text = read_csv_text(path)
    with io.StringIO(csv_text, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("skills CSV file is empty or missing a header row.")

        fieldnames = list(reader.fieldnames)
        mapping = detect_skill_columns(fieldnames)
        require_skill_columns(mapping)

        for raw_row in reader:
            stats.total_skills_rows_read += 1
            row = clean_row(raw_row)
            esco_skill_uri = get_optional(row, mapping.esco_skill_uri)
            preferred_label = get_optional(row, mapping.preferred_label)
            skill_type = get_nullable(row, mapping.skill_type)
            reuse_level = get_nullable(row, mapping.reuse_level)

            if not esco_skill_uri:
                stats.rows_skipped_missing_skill_uri += 1
                review_rows.append(
                    SkillReviewRow(
                        esco_skill_uri="",
                        preferred_label=preferred_label,
                        skill_type=skill_type,
                        reuse_level=reuse_level,
                        included=False,
                        skip_reason="missing_skill_uri",
                    )
                )
                continue
            if esco_skill_uri not in needed_skill_uris:
                stats.rows_skipped_not_needed += 1
                review_rows.append(
                    SkillReviewRow(
                        esco_skill_uri=esco_skill_uri,
                        preferred_label=preferred_label,
                        skill_type=skill_type,
                        reuse_level=reuse_level,
                        included=False,
                        skip_reason="skill_not_linked_to_imported_occupations",
                    )
                )
                continue

            found_needed_skill_uris.add(esco_skill_uri)
            if esco_skill_uri in skills_by_uri:
                stats.rows_skipped_duplicate_skill_uri += 1
                review_rows.append(
                    SkillReviewRow(
                        esco_skill_uri=esco_skill_uri,
                        preferred_label=preferred_label,
                        skill_type=skill_type,
                        reuse_level=reuse_level,
                        included=False,
                        skip_reason="duplicate_skill_uri",
                    )
                )
                continue
            if not preferred_label:
                stats.rows_skipped_missing_preferred_label += 1
                invalid_needed_skill_reasons[esco_skill_uri] = "missing_preferred_label"
                review_rows.append(
                    SkillReviewRow(
                        esco_skill_uri=esco_skill_uri,
                        preferred_label="",
                        skill_type=skill_type,
                        reuse_level=reuse_level,
                        included=False,
                        skip_reason="missing_preferred_label",
                    )
                )
                continue

            skill = EscoSkill(
                esco_skill_uri=esco_skill_uri,
                skill_type=skill_type,
                reuse_level=reuse_level,
                preferred_label=preferred_label,
                alt_labels=get_nullable(row, mapping.alt_labels),
                hidden_labels=get_nullable(row, mapping.hidden_labels),
                description=get_nullable(row, mapping.description),
                scope_note=get_nullable(row, mapping.scope_note),
            )
            skills_by_uri[esco_skill_uri] = skill
            stats.rows_included += 1
            review_rows.append(
                SkillReviewRow(
                    esco_skill_uri=esco_skill_uri,
                    preferred_label=preferred_label,
                    skill_type=skill_type,
                    reuse_level=reuse_level,
                    included=True,
                    skip_reason="",
                )
            )

    missing_skills: list[MissingSkillRow] = []
    for esco_skill_uri in sorted(needed_skill_uris):
        if esco_skill_uri in skills_by_uri:
            continue
        if esco_skill_uri in found_needed_skill_uris:
            reason = invalid_needed_skill_reasons.get(
                esco_skill_uri,
                "not_importable_from_skills_csv",
            )
        else:
            reason = "not_found_in_skills_csv"
        missing_skills.append(
            MissingSkillRow(
                esco_skill_uri=esco_skill_uri,
                relation_count=int(relation_counts.get(esco_skill_uri, 0)),
                reason=reason,
            )
        )

    return SkillParseResult(
        skills=list(skills_by_uri.values()),
        review_rows=review_rows,
        missing_skills=missing_skills,
        stats=stats,
        detected_columns=fieldnames,
        detected_mapping=mapping,
    )


def filter_relations_to_importable_skills(
    relation_result: RelationParseResult,
    imported_skill_uris: set[str],
) -> tuple[list[EscoOccupationSkill], list[RelationReviewRow]]:
    importable_relations = [
        relation
        for relation in relation_result.relations
        if relation.esco_skill_uri in imported_skill_uris
    ]
    final_review_rows: list[RelationReviewRow] = []
    for row in relation_result.review_rows:
        if row.included and row.esco_skill_uri not in imported_skill_uris:
            final_review_rows.append(
                replace(
                    row,
                    included=False,
                    skip_reason="skill_not_imported",
                )
            )
        else:
            final_review_rows.append(row)
    return importable_relations, final_review_rows


def write_skills_review_csv(
    path: Path | str,
    review_rows: Sequence[SkillReviewRow],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "esco_skill_uri",
                "preferred_label",
                "skill_type",
                "reuse_level",
                "included",
                "skip_reason",
            ],
        )
        writer.writeheader()
        for row in review_rows:
            writer.writerow(
                {
                    "esco_skill_uri": row.esco_skill_uri,
                    "preferred_label": row.preferred_label,
                    "skill_type": row.skill_type or "",
                    "reuse_level": row.reuse_level or "",
                    "included": "true" if row.included else "false",
                    "skip_reason": row.skip_reason,
                }
            )


def write_missing_skills_csv(
    path: Path | str,
    missing_skills: Sequence[MissingSkillRow],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["esco_skill_uri", "relation_count", "reason"],
        )
        writer.writeheader()
        for row in missing_skills:
            writer.writerow(
                {
                    "esco_skill_uri": row.esco_skill_uri,
                    "relation_count": row.relation_count,
                    "reason": row.reason,
                }
            )


def write_relations_review_csv(
    path: Path | str,
    review_rows: Sequence[RelationReviewRow],
) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "esco_uri",
                "esco_skill_uri",
                "relation_type",
                "included",
                "skip_reason",
            ],
        )
        writer.writeheader()
        for row in review_rows:
            writer.writerow(
                {
                    "esco_uri": row.esco_uri,
                    "esco_skill_uri": row.esco_skill_uri,
                    "relation_type": row.relation_type,
                    "included": "true" if row.included else "false",
                    "skip_reason": row.skip_reason,
                }
            )


def chunked(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def format_postgrest_in_filter(values: Sequence[str]) -> str:
    quoted_values = []
    for value in values:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        quoted_values.append(f'"{escaped}"')
    return "in.(" + ",".join(quoted_values) + ")"


class SupabaseRestClient:
    def __init__(
        self,
        supabase_url: str,
        service_role_key: str,
        schema: SchemaConfig = DEFAULT_SCHEMA,
        timeout_seconds: int = 30,
    ):
        self.rest_url = normalize_supabase_url(supabase_url) + "/rest/v1"
        self.service_role_key = service_role_key
        self.schema = schema
        self.timeout_seconds = timeout_seconds

    def validate_occupations_schema(self) -> None:
        self._request(
            "GET",
            self.schema.occupations_table,
            query=[
                ("select", self.schema.esco_uri_column),
                ("limit", "1"),
            ],
        )

    def validate_import_schema(self) -> None:
        self._request(
            "GET",
            self.schema.skills_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.esco_skill_uri_column,
                            self.schema.skill_type_column,
                            self.schema.reuse_level_column,
                            self.schema.preferred_label_column,
                            self.schema.alt_labels_column,
                            self.schema.hidden_labels_column,
                            self.schema.description_column,
                            self.schema.scope_note_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )
        self._request(
            "GET",
            self.schema.occupation_skills_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.esco_uri_column,
                            self.schema.esco_skill_uri_column,
                            self.schema.relation_type_column,
                            self.schema.skill_type_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )

    def list_esco_occupation_uris(self) -> set[str]:
        rows = self._paged_get(
            self.schema.occupations_table,
            select=self.schema.esco_uri_column,
            extra_query=[("order", f"{self.schema.esco_uri_column}.asc")],
        )
        return {
            str(row.get(self.schema.esco_uri_column)).strip()
            for row in rows
            if row.get(self.schema.esco_uri_column)
        }

    def list_existing_skills(self, skill_uris: set[str]) -> dict[str, dict[str, Any]]:
        existing: dict[str, dict[str, Any]] = {}
        sorted_uris = sorted(skill_uris)
        for uri_chunk in chunked(sorted_uris, LOOKUP_FILTER_BATCH_SIZE):
            rows = self._request(
                "GET",
                self.schema.skills_table,
                query=[
                    (
                        "select",
                        ",".join(
                            [
                                self.schema.esco_skill_uri_column,
                                self.schema.preferred_label_column,
                            ]
                        ),
                    ),
                    (
                        self.schema.esco_skill_uri_column,
                        format_postgrest_in_filter(uri_chunk),
                    ),
                ],
            )
            for row in rows or []:
                skill_uri = row.get(self.schema.esco_skill_uri_column)
                if skill_uri:
                    existing[str(skill_uri)] = row
        return existing

    def upsert_skills(
        self,
        skills: Sequence[EscoSkill],
        force: bool = False,
    ) -> ImportStats:
        stats = ImportStats()
        skill_uris = {skill.esco_skill_uri for skill in skills}
        existing = self.list_existing_skills(skill_uris)
        if force:
            rows_to_write = [skill.to_payload(self.schema) for skill in skills]
            self._bulk_upsert(
                self.schema.skills_table,
                rows_to_write,
                conflict_columns=self.schema.esco_skill_uri_column,
                force=True,
            )
            stats.skills_inserted = len(skill_uris - set(existing))
            stats.skills_updated = len(skill_uris & set(existing))
            return stats

        missing_skills = [
            skill
            for skill in skills
            if skill.esco_skill_uri not in existing
        ]
        rows_to_write = [skill.to_payload(self.schema) for skill in missing_skills]
        self._bulk_upsert(
            self.schema.skills_table,
            rows_to_write,
            conflict_columns=self.schema.esco_skill_uri_column,
            force=False,
        )
        stats.skills_inserted = len(missing_skills)
        stats.skills_reused = len(skills) - len(missing_skills)
        return stats

    def list_existing_relations(
        self,
        relations: Sequence[EscoOccupationSkill],
    ) -> dict[tuple[str, str, str], dict[str, Any]]:
        wanted_keys = {relation.identity_key() for relation in relations}
        if not wanted_keys:
            return {}

        rows = self._paged_get(
            self.schema.occupation_skills_table,
            select=",".join(
                [
                    self.schema.esco_uri_column,
                    self.schema.esco_skill_uri_column,
                    self.schema.relation_type_column,
                ]
            ),
        )
        existing: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in rows:
            key = (
                str(row.get(self.schema.esco_uri_column) or ""),
                str(row.get(self.schema.esco_skill_uri_column) or ""),
                str(row.get(self.schema.relation_type_column) or ""),
            )
            if key in wanted_keys:
                existing[key] = row
        return existing

    def upsert_relations(
        self,
        relations: Sequence[EscoOccupationSkill],
        force: bool = False,
    ) -> ImportStats:
        stats = ImportStats()
        existing = self.list_existing_relations(relations)
        if force:
            rows_to_write = [relation.to_payload(self.schema) for relation in relations]
            self._bulk_upsert(
                self.schema.occupation_skills_table,
                rows_to_write,
                conflict_columns=",".join(
                    [
                        self.schema.esco_uri_column,
                        self.schema.esco_skill_uri_column,
                        self.schema.relation_type_column,
                    ]
                ),
                force=True,
            )
            relation_keys = {relation.identity_key() for relation in relations}
            stats.relations_inserted = len(relation_keys - set(existing))
            stats.relations_updated = len(relation_keys & set(existing))
            return stats

        missing_relations = [
            relation
            for relation in relations
            if relation.identity_key() not in existing
        ]
        rows_to_write = [
            relation.to_payload(self.schema)
            for relation in missing_relations
        ]
        self._bulk_upsert(
            self.schema.occupation_skills_table,
            rows_to_write,
            conflict_columns=",".join(
                [
                    self.schema.esco_uri_column,
                    self.schema.esco_skill_uri_column,
                    self.schema.relation_type_column,
                ]
            ),
            force=False,
        )
        stats.relations_inserted = len(missing_relations)
        stats.relations_reused = len(relations) - len(missing_relations)
        return stats

    def _bulk_upsert(
        self,
        table: str,
        rows: Sequence[dict[str, Any]],
        conflict_columns: str,
        force: bool,
    ) -> None:
        if not rows:
            return

        resolution = "merge-duplicates" if force else "ignore-duplicates"
        for row_chunk in chunked(list(rows)):
            self._request(
                "POST",
                table,
                query=[("on_conflict", conflict_columns)],
                payload=list(row_chunk),
                prefer=f"resolution={resolution},return=minimal",
            )

    def _paged_get(
        self,
        table: str,
        select: str,
        extra_query: Iterable[tuple[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        start = 0
        while True:
            end = start + BATCH_SIZE - 1
            query = [("select", select)]
            if extra_query:
                query.extend(extra_query)
            page = self._request(
                "GET",
                table,
                query=query,
                extra_headers={
                    "Range-Unit": "items",
                    "Range": f"{start}-{end}",
                },
            )
            if not page:
                break
            rows.extend(page)
            if len(page) < BATCH_SIZE:
                break
            start += BATCH_SIZE
        return rows

    def _request(
        self,
        method: str,
        table: str,
        query: Iterable[tuple[str, str]] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> Any:
        encoded_table = urllib.parse.quote(table, safe="")
        url = f"{self.rest_url}/{encoded_table}"
        if query:
            url += "?" + urllib.parse.urlencode(list(query))

        body = None
        headers = self._auth_headers()
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if prefer:
            headers["Prefer"] = prefer
        if extra_headers:
            headers.update(extra_headers)

        request = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            error_body = error.read().decode("utf-8", errors="replace")
            raise SupabaseError(
                format_supabase_error(error.code, method, table, error_body)
            ) from error
        except urllib.error.URLError as error:
            raise SupabaseError(
                f"Could not reach Supabase REST API for table '{table}': {error.reason}"
            ) from error

        if not response_body:
            return None

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as error:
            raise SupabaseError(
                f"Supabase returned non-JSON data for table '{table}'."
            ) from error

    def _auth_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "apikey": self.service_role_key,
            "User-Agent": "career-compass-esco-skills-importer/1.0",
        }
        if not self.service_role_key.startswith(("sb_secret_", "sb_publishable_")):
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        return headers


def format_supabase_error(
    status_code: int,
    method: str,
    table: str,
    response_body: str,
) -> str:
    try:
        error_json = json.loads(response_body)
    except json.JSONDecodeError:
        detail = response_body.strip()
    else:
        parts = [
            str(error_json.get("message") or "").strip(),
            str(error_json.get("details") or "").strip(),
            str(error_json.get("hint") or "").strip(),
        ]
        detail = " ".join(part for part in parts if part)

    if not detail:
        detail = "No response body returned."

    return (
        f"Supabase {method} failed for table '{table}' "
        f"with HTTP {status_code}: {detail}"
    )


def import_esco_skills(
    skills: Sequence[EscoSkill],
    relations: Sequence[EscoOccupationSkill],
    client: Any,
    force: bool = False,
) -> ImportStats:
    stats = ImportStats()
    stats.merge(client.upsert_skills(skills, force=force))
    stats.merge(client.upsert_relations(relations, force=force))
    return stats


def format_relation_type_counts(counts: Mapping[str, int]) -> str:
    if not counts:
        return "(none)"
    return ", ".join(
        f"{relation_type or '(missing)'}={count}"
        for relation_type, count in sorted(counts.items())
    )


def print_summary(
    occupations_loaded: int,
    relation_result: RelationParseResult,
    skill_result: SkillParseResult,
    importable_relations: Sequence[EscoOccupationSkill],
    import_stats: ImportStats | None,
    skills_review_output: Path,
    missing_skills_output: Path,
    relations_review_output: Path,
    dry_run: bool,
    force: bool,
) -> None:
    importable_relation_counts = collections.Counter(
        relation.relation_type for relation in importable_relations
    )

    print(f"Dry run: {'yes' if dry_run else 'no'}")
    print(f"Force updates: {'yes' if force else 'no'}")
    print(f"ESCO occupations loaded from Supabase: {occupations_loaded}")
    print(
        "Total relation rows read: "
        f"{relation_result.stats.total_relation_rows_read}"
    )
    print(
        "Relation rows linked to existing esco_occupations: "
        f"{relation_result.stats.relation_rows_linked_to_existing_occupations}"
    )
    print(f"Unique skill URIs needed: {len(relation_result.needed_skill_uris)}")
    print(f"Total skills rows read: {skill_result.stats.total_skills_rows_read}")
    print(f"Skills prepared for import: {len(skill_result.skills)}")
    print(f"Missing linked skill URIs: {len(skill_result.missing_skills)}")
    print(f"Occupation-skill relations prepared for import: {len(importable_relations)}")
    print(
        "Linked relation counts by relation_type: "
        + format_relation_type_counts(relation_result.relation_type_counts)
    )
    print(
        "Importable relation counts by relation_type: "
        + format_relation_type_counts(importable_relation_counts)
    )
    if relation_result.unusual_relation_types:
        print(
            "Unusual relation_type values: "
            + ", ".join(sorted(relation_result.unusual_relation_types))
        )
    print(f"Skills review CSV: {skills_review_output}")
    print(f"Missing skills review CSV: {missing_skills_output}")
    print(f"Relations review CSV: {relations_review_output}")

    if import_stats is None:
        print("Skills inserted: 0")
        print("Skills updated: 0")
        print("Skills reused: 0")
        print("Occupation-skill relations inserted: 0")
        print("Occupation-skill relations updated: 0")
        print("Occupation-skill relations reused: 0")
        print("Dry run only. No Supabase writes were made.")
        return

    print(f"Skills inserted: {import_stats.skills_inserted}")
    print(f"Skills updated: {import_stats.skills_updated}")
    print(f"Skills reused: {import_stats.skills_reused}")
    print(
        "Occupation-skill relations inserted: "
        f"{import_stats.relations_inserted}"
    )
    print(
        "Occupation-skill relations updated: "
        f"{import_stats.relations_updated}"
    )
    print(
        "Occupation-skill relations reused: "
        f"{import_stats.relations_reused}"
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database population: import ESCO skills linked to "
            "already-imported ESCO occupations."
        ),
    )
    parser.add_argument(
        "--skills-csv",
        type=Path,
        required=True,
        help="Path to the official ESCO skills_en.csv file.",
    )
    parser.add_argument(
        "--relations-csv",
        type=Path,
        required=True,
        help="Path to the official ESCO occupationSkillRelations_en.csv file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, filter, and write review outputs without writing to Supabase.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing skill and relation metadata from the CSV files.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_SKILLS_REVIEW_OUTPUT,
        help=(
            "Path for the skills review CSV. Defaults to "
            "data/esco_skills_import_review.csv."
        ),
    )
    parser.add_argument(
        "--missing-skills-output",
        type=Path,
        default=DEFAULT_MISSING_SKILLS_OUTPUT,
        help=(
            "Path for linked skill URIs missing from skills_en.csv. Defaults to "
            "data/esco_missing_skills_review.csv."
        ),
    )
    parser.add_argument(
        "--relations-review-output",
        type=Path,
        default=DEFAULT_RELATIONS_REVIEW_OUTPUT,
        help=(
            "Path for the occupation-skill relations review CSV. Defaults to "
            "data/esco_occupation_skill_relations_review.csv."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        supabase_url, service_role_key = get_required_env()
        client = SupabaseRestClient(supabase_url, service_role_key)
        client.validate_occupations_schema()
        existing_occupation_uris = client.list_esco_occupation_uris()

        relation_result = parse_relations_csv(
            args.relations_csv,
            existing_occupation_uris,
        )
        skill_result = parse_skills_csv(
            args.skills_csv,
            relation_result.needed_skill_uris,
            relation_result.skill_uri_relation_counts,
        )
        imported_skill_uris = {skill.esco_skill_uri for skill in skill_result.skills}
        importable_relations, final_relation_review_rows = (
            filter_relations_to_importable_skills(
                relation_result,
                imported_skill_uris,
            )
        )

        write_skills_review_csv(args.review_output, skill_result.review_rows)
        write_missing_skills_csv(args.missing_skills_output, skill_result.missing_skills)
        write_relations_review_csv(
            args.relations_review_output,
            final_relation_review_rows,
        )

        import_stats: ImportStats | None = None
        if not args.dry_run:
            client.validate_import_schema()
            import_stats = import_esco_skills(
                skill_result.skills,
                importable_relations,
                client,
                force=args.force,
            )

        print_summary(
            occupations_loaded=len(existing_occupation_uris),
            relation_result=relation_result,
            skill_result=skill_result,
            importable_relations=importable_relations,
            import_stats=import_stats,
            skills_review_output=args.review_output,
            missing_skills_output=args.missing_skills_output,
            relations_review_output=args.relations_review_output,
            dry_run=args.dry_run,
            force=args.force,
        )
        return 0
    except (FileNotFoundError, ValueError, SupabaseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
