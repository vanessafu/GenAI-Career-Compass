#!/usr/bin/env python3
"""Normalize imported role skill aliases for Phase 5.

One-time database enrichment script. Kept for auditability and controlled reruns
while rebuilding the seeded Career Compass database; not app runtime code.
Prefer --dry-run before any write-mode rerun.

Phase 5 updates only `role_skills.normalized_skill_name` and maintains the
deterministic `skill_aliases` lookup table. It does not score roles, generate
roadmaps, create embeddings, or map Kaggle roles to ESCO occupations.

Examples:

    python scripts/normalize_role_skills.py --dry-run
    python scripts/normalize_role_skills.py
    python scripts/normalize_role_skills.py --force
    python scripts/normalize_role_skills.py --no-esco-linking

For dry runs and real updates, set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in
your local shell environment or in a local .env file. Never expose the service
role key in frontend/client code.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


BATCH_SIZE = 500
DEFAULT_SEED_ALIASES_PATH = Path("data/skill_aliases.seed.csv")
DEFAULT_REVIEW_OUTPUT = Path("data/skill_normalization_review.csv")
DEFAULT_DUPLICATES_OUTPUT = Path("data/skill_normalization_duplicates.csv")

SEED_ALIAS_FIELDNAMES = [
    "alias_key",
    "alias_display",
    "canonical_key",
    "canonical_display",
    "source",
    "confidence",
    "notes",
]

REVIEW_FIELDNAMES = [
    "raw_skill_name",
    "raw_skill_count",
    "old_normalized_skill_name",
    "new_normalized_skill_name",
    "canonical_display",
    "source",
    "confidence",
    "esco_skill_uri",
    "esco_match_status",
    "generic_skill_candidate",
    "notes",
]

DUPLICATE_FIELDNAMES = [
    "role_id",
    "job_title",
    "canonical_key",
    "raw_skill_names_that_collapsed",
]


DEFAULT_SEED_ALIAS_ROWS: tuple[dict[str, str], ...] = (
    {
        "alias_key": "js",
        "alias_display": "JS",
        "canonical_key": "javascript",
        "canonical_display": "JavaScript",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "java script",
        "alias_display": "Java Script",
        "canonical_key": "javascript",
        "canonical_display": "JavaScript",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling.",
    },
    {
        "alias_key": "javascript programming",
        "alias_display": "JavaScript Programming",
        "canonical_key": "javascript",
        "canonical_display": "JavaScript",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Programming suffix does not change skill.",
    },
    {
        "alias_key": "ts",
        "alias_display": "TS",
        "canonical_key": "typescript",
        "canonical_display": "TypeScript",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "typescript programming",
        "alias_display": "TypeScript Programming",
        "canonical_key": "typescript",
        "canonical_display": "TypeScript",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Programming suffix does not change skill.",
    },
    {
        "alias_key": "react.js",
        "alias_display": "React.js",
        "canonical_key": "react",
        "canonical_display": "React",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Library spelling alias.",
    },
    {
        "alias_key": "reactjs",
        "alias_display": "ReactJS",
        "canonical_key": "react",
        "canonical_display": "React",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined spelling alias.",
    },
    {
        "alias_key": "react js",
        "alias_display": "React JS",
        "canonical_key": "react",
        "canonical_display": "React",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling alias.",
    },
    {
        "alias_key": "node",
        "alias_display": "Node",
        "canonical_key": "node.js",
        "canonical_display": "Node.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Runtime shorthand.",
    },
    {
        "alias_key": "nodejs",
        "alias_display": "NodeJS",
        "canonical_key": "node.js",
        "canonical_display": "Node.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined spelling alias.",
    },
    {
        "alias_key": "node js",
        "alias_display": "Node JS",
        "canonical_key": "node.js",
        "canonical_display": "Node.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling alias.",
    },
    {
        "alias_key": "vue",
        "alias_display": "Vue",
        "canonical_key": "vue.js",
        "canonical_display": "Vue.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Framework shorthand.",
    },
    {
        "alias_key": "vuejs",
        "alias_display": "VueJS",
        "canonical_key": "vue.js",
        "canonical_display": "Vue.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined spelling alias.",
    },
    {
        "alias_key": "vue js",
        "alias_display": "Vue JS",
        "canonical_key": "vue.js",
        "canonical_display": "Vue.js",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling alias.",
    },
    {
        "alias_key": "c sharp",
        "alias_display": "C Sharp",
        "canonical_key": "c#",
        "canonical_display": "C#",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Language name alias.",
    },
    {
        "alias_key": "csharp",
        "alias_display": "CSharp",
        "canonical_key": "c#",
        "canonical_display": "C#",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined spelling alias.",
    },
    {
        "alias_key": "cpp",
        "alias_display": "CPP",
        "canonical_key": "c++",
        "canonical_display": "C++",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common C++ abbreviation.",
    },
    {
        "alias_key": "dotnet",
        "alias_display": "Dotnet",
        "canonical_key": ".net",
        "canonical_display": ".NET",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined platform spelling.",
    },
    {
        "alias_key": ".net core",
        "alias_display": ".NET Core",
        "canonical_key": ".net",
        "canonical_display": ".NET",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Phase 5 keeps framework family only.",
    },
    {
        "alias_key": "net core",
        "alias_display": "NET Core",
        "canonical_key": ".net",
        "canonical_display": ".NET",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Missing leading-dot spelling.",
    },
    {
        "alias_key": "golang",
        "alias_display": "Golang",
        "canonical_key": "go",
        "canonical_display": "Go",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Language alias.",
    },
    {
        "alias_key": "postgres",
        "alias_display": "Postgres",
        "canonical_key": "postgresql",
        "canonical_display": "PostgreSQL",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Database shorthand.",
    },
    {
        "alias_key": "mongo db",
        "alias_display": "Mongo DB",
        "canonical_key": "mongodb",
        "canonical_display": "MongoDB",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling alias.",
    },
    {
        "alias_key": "amazon web services",
        "alias_display": "Amazon Web Services",
        "canonical_key": "aws",
        "canonical_display": "AWS",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor full-name alias.",
    },
    {
        "alias_key": "amazon aws",
        "alias_display": "Amazon AWS",
        "canonical_key": "aws",
        "canonical_display": "AWS",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor alias.",
    },
    {
        "alias_key": "google cloud platform",
        "alias_display": "Google Cloud Platform",
        "canonical_key": "google cloud",
        "canonical_display": "Google Cloud",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor platform alias.",
    },
    {
        "alias_key": "gcp",
        "alias_display": "GCP",
        "canonical_key": "google cloud",
        "canonical_display": "Google Cloud",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor abbreviation.",
    },
    {
        "alias_key": "microsoft azure",
        "alias_display": "Microsoft Azure",
        "canonical_key": "azure",
        "canonical_display": "Azure",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor full-name alias.",
    },
    {
        "alias_key": "k8s",
        "alias_display": "K8s",
        "canonical_key": "kubernetes",
        "canonical_display": "Kubernetes",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "ci cd",
        "alias_display": "CI CD",
        "canonical_key": "ci/cd",
        "canonical_display": "CI/CD",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Slashless CI/CD spelling.",
    },
    {
        "alias_key": "cicd",
        "alias_display": "CICD",
        "canonical_key": "ci/cd",
        "canonical_display": "CI/CD",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined CI/CD spelling.",
    },
    {
        "alias_key": "ci/cd pipelines",
        "alias_display": "CI/CD Pipelines",
        "canonical_key": "ci/cd",
        "canonical_display": "CI/CD",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Pipeline suffix does not change skill family.",
    },
    {
        "alias_key": "continuous integration continuous deployment",
        "alias_display": "Continuous Integration Continuous Deployment",
        "canonical_key": "ci/cd",
        "canonical_display": "CI/CD",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Expanded CI/CD phrase.",
    },
    {
        "alias_key": "iac",
        "alias_display": "IaC",
        "canonical_key": "infrastructure as code",
        "canonical_display": "Infrastructure as Code",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "infrastructure-as-code",
        "alias_display": "Infrastructure-as-Code",
        "canonical_key": "infrastructure as code",
        "canonical_display": "Infrastructure as Code",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Hyphenated spelling.",
    },
    {
        "alias_key": "powerbi",
        "alias_display": "PowerBI",
        "canonical_key": "power bi",
        "canonical_display": "Power BI",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Joined product spelling.",
    },
    {
        "alias_key": "microsoft power bi",
        "alias_display": "Microsoft Power BI",
        "canonical_key": "power bi",
        "canonical_display": "Power BI",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Vendor-prefixed product alias.",
    },
    {
        "alias_key": "nlp",
        "alias_display": "NLP",
        "canonical_key": "natural language processing",
        "canonical_display": "Natural Language Processing",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "ml",
        "alias_display": "ML",
        "canonical_key": "machine learning",
        "canonical_display": "Machine Learning",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "ai",
        "alias_display": "AI",
        "canonical_key": "artificial intelligence",
        "canonical_display": "Artificial Intelligence",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "cyber security",
        "alias_display": "Cyber Security",
        "canonical_key": "cybersecurity",
        "canonical_display": "Cybersecurity",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Spaced spelling alias.",
    },
    {
        "alias_key": "infosec",
        "alias_display": "InfoSec",
        "canonical_key": "information security",
        "canonical_display": "Information Security",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Common abbreviation.",
    },
    {
        "alias_key": "tcp ip",
        "alias_display": "TCP IP",
        "canonical_key": "tcp/ip",
        "canonical_display": "TCP/IP",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Slashless TCP/IP spelling.",
    },
    {
        "alias_key": "ux ui",
        "alias_display": "UX UI",
        "canonical_key": "ux/ui",
        "canonical_display": "UX/UI",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Slashless UX/UI spelling.",
    },
    {
        "alias_key": "ui ux",
        "alias_display": "UI UX",
        "canonical_key": "ux/ui",
        "canonical_display": "UX/UI",
        "source": "phase5_seed",
        "confidence": "high",
        "notes": "Normalizes word order for slashless UX/UI spelling.",
    },
)


DISPLAY_OVERRIDES = {
    ".net": ".NET",
    "ai": "AI",
    "api": "API",
    "aws": "AWS",
    "bi": "BI",
    "c#": "C#",
    "c++": "C++",
    "ci/cd": "CI/CD",
    "css": "CSS",
    "gcp": "GCP",
    "html": "HTML",
    "html/css": "HTML/CSS",
    "iaas": "IaaS",
    "iac": "IaC",
    "ios": "iOS",
    "iot": "IoT",
    "it": "IT",
    "js": "JS",
    "k8s": "K8s",
    "ml": "ML",
    "mongodb": "MongoDB",
    "nlp": "NLP",
    "node.js": "Node.js",
    "nosql": "NoSQL",
    "postgresql": "PostgreSQL",
    "power bi": "Power BI",
    "qa": "QA",
    "sql": "SQL",
    "tcp/ip": "TCP/IP",
    "ts": "TS",
    "ui": "UI",
    "ui/ux": "UI/UX",
    "ux": "UX",
    "ux/ui": "UX/UI",
    "vue.js": "Vue.js",
}

GENERIC_SKILL_KEYS = {
    "analytical thinking",
    "collaboration",
    "communication",
    "critical thinking",
    "leadership",
    "problem solving",
    "project management",
    "stakeholder management",
    "teamwork",
}


def bidirectional_pairs(pairs: Iterable[tuple[str, str]]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for left, right in pairs:
        result.add((left, right))
        result.add((right, left))
    return result


DO_NOT_MERGE_ALIAS_PAIRS = bidirectional_pairs(
    [
        ("java", "javascript"),
        ("react", "react native"),
        ("angular", "angularjs"),
        ("sql", "mysql"),
        ("sql", "postgresql"),
        ("sql", "sql server"),
        ("git", "github"),
        ("git", "github actions"),
        ("docker", "kubernetes"),
        ("aws", "cloud platforms"),
        ("linux", "unix"),
        ("excel", "power bi"),
        ("c", "c++"),
        ("c", "c#"),
        ("c++", "c#"),
        ("product management", "project management"),
        ("machine learning", "artificial intelligence"),
        ("data analytics", "data engineering"),
    ]
)

QUOTE_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201a": "'",
        "\u201b": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u201e": '"',
        "\u201f": '"',
        "\u00a0": " ",
    }
)

SURROUNDING_PUNCTUATION = set("\"'` ,;:!?()[]{}<>")
CLOSING_PUNCTUATION_PAIRS = {
    ")": "(",
    "]": "[",
    "}": "{",
    ">": "<",
}


@dataclass(frozen=True)
class SchemaConfig:
    roles_table: str = "career_roles"
    role_skills_table: str = "role_skills"
    skill_aliases_table: str = "skill_aliases"
    esco_skills_table: str = "esco_skills"
    role_id_column: str = "role_id"
    job_title_column: str = "job_title"
    skill_name_column: str = "skill_name"
    normalized_skill_name_column: str = "normalized_skill_name"
    role_skill_id_column: str = "id"
    alias_key_column: str = "alias_key"
    esco_skill_uri_column: str = "esco_skill_uri"
    preferred_label_column: str = "preferred_label"
    alt_labels_column: str = "alt_labels"
    hidden_labels_column: str = "hidden_labels"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass(frozen=True)
class RoleSkillRow:
    row_id: str | None
    role_id: str
    skill_name: str
    normalized_skill_name: str

    @property
    def identity_key(self) -> tuple[str, str, str, str]:
        if self.row_id is not None:
            return ("id", self.row_id, "", "")
        return (
            "role_skill",
            self.role_id,
            self.skill_name,
            self.normalized_skill_name,
        )


@dataclass(frozen=True)
class SkillAlias:
    alias_key: str
    alias_display: str
    canonical_key: str
    canonical_display: str
    source: str
    confidence: str
    notes: str = ""
    esco_skill_uri: str | None = None

    def with_esco_skill_uri(self, esco_skill_uri: str | None) -> "SkillAlias":
        return replace(self, esco_skill_uri=esco_skill_uri)

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "alias_key": self.alias_key,
            "alias_display": self.alias_display,
            "canonical_key": self.canonical_key,
            "canonical_display": self.canonical_display,
            "esco_skill_uri": self.esco_skill_uri,
        }
        return payload


@dataclass(frozen=True)
class EscoLabelLookup:
    label_uris_by_key: dict[str, set[str]]

    def uris_for_key(self, key: str) -> set[str]:
        return self.label_uris_by_key.get(key, set())


@dataclass(frozen=True)
class NormalizationResult:
    raw_skill_name: str
    alias_key: str
    canonical_key: str
    canonical_display: str
    source: str
    confidence: str
    esco_skill_uri: str | None
    esco_match_status: str
    generic_skill_candidate: bool
    notes: str = ""


@dataclass(frozen=True)
class DuplicateCollapseRow:
    role_id: str
    job_title: str
    canonical_key: str
    raw_skill_names_that_collapsed: list[str]


@dataclass(frozen=True)
class ReviewRow:
    raw_skill_name: str
    raw_skill_count: int
    old_normalized_skill_name: str
    new_normalized_skill_name: str
    canonical_display: str
    source: str
    confidence: str
    esco_skill_uri: str | None
    esco_match_status: str
    generic_skill_candidate: bool
    notes: str


@dataclass
class AliasWriteStats:
    aliases_inserted: int = 0
    aliases_updated: int = 0
    aliases_reused: int = 0


@dataclass
class RoleSkillUpdateStats:
    role_skills_updated: int = 0
    role_skills_unchanged: int = 0


class SupabaseError(RuntimeError):
    """Raised when Supabase returns an error response."""


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_alias_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "")
    normalized = normalized.translate(QUOTE_TRANSLATION)
    normalized = re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)
    normalized = re.sub(r"\s*/\s*", "/", normalized)
    normalized = collapse_spaces(normalized)
    normalized = strip_surrounding_punctuation(normalized)
    return collapse_spaces(normalized).casefold()


def strip_surrounding_punctuation(value: str) -> str:
    stripped = value
    while stripped and stripped[0] in SURROUNDING_PUNCTUATION:
        stripped = stripped[1:].lstrip()
    while stripped and stripped[-1] in SURROUNDING_PUNCTUATION:
        opener = CLOSING_PUNCTUATION_PAIRS.get(stripped[-1])
        if opener and opener in stripped[:-1]:
            break
        stripped = stripped[:-1].rstrip()
    while stripped.endswith(".") and stripped.casefold() != ".net":
        stripped = stripped[:-1].rstrip()
    return stripped


def display_from_key(key: str, raw_display: str | None = None) -> str:
    if key in DISPLAY_OVERRIDES:
        return DISPLAY_OVERRIDES[key]
    if raw_display:
        display = collapse_spaces(strip_surrounding_punctuation(raw_display))
        if display:
            return display
    return " ".join(part.capitalize() for part in key.split(" "))


def validate_alias_safety(alias_key: str, canonical_key: str) -> None:
    if alias_key == canonical_key:
        return
    if (alias_key, canonical_key) in DO_NOT_MERGE_ALIAS_PAIRS:
        raise ValueError(
            "Unsafe alias mapping violates Phase 5 do-not-merge rule: "
            f"{alias_key!r} -> {canonical_key!r}"
        )


def skill_alias_from_mapping(row: Mapping[str, Any]) -> SkillAlias:
    alias_key = normalize_alias_key(
        str(row.get("alias_key") or row.get("alias_display") or "")
    )
    canonical_key = normalize_alias_key(
        str(row.get("canonical_key") or row.get("canonical_display") or "")
    )
    if not alias_key:
        raise ValueError("Seed alias row is missing alias_key.")
    if not canonical_key:
        raise ValueError(f"Seed alias {alias_key!r} is missing canonical_key.")

    validate_alias_safety(alias_key, canonical_key)
    alias_display = collapse_spaces(str(row.get("alias_display") or "")) or (
        display_from_key(alias_key)
    )
    canonical_display = collapse_spaces(str(row.get("canonical_display") or "")) or (
        display_from_key(canonical_key)
    )
    source = collapse_spaces(str(row.get("source") or "")) or "phase5_seed"
    confidence = collapse_spaces(str(row.get("confidence") or "")) or "high"
    notes = collapse_spaces(str(row.get("notes") or ""))
    esco_skill_uri = collapse_spaces(str(row.get("esco_skill_uri") or "")) or None
    return SkillAlias(
        alias_key=alias_key,
        alias_display=alias_display,
        canonical_key=canonical_key,
        canonical_display=canonical_display,
        source=source,
        confidence=confidence,
        notes=notes,
        esco_skill_uri=esco_skill_uri,
    )


def alias_map_from_seed_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, SkillAlias]:
    aliases: dict[str, SkillAlias] = {}
    for row in rows:
        alias = skill_alias_from_mapping(row)
        aliases[alias.alias_key] = alias
    return aliases


def write_default_seed_aliases(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SEED_ALIAS_FIELDNAMES)
        writer.writeheader()
        writer.writerows(DEFAULT_SEED_ALIAS_ROWS)


def load_seed_aliases(path: Path) -> dict[str, SkillAlias]:
    if not path.exists():
        if path == DEFAULT_SEED_ALIASES_PATH:
            write_default_seed_aliases(path)
        else:
            raise FileNotFoundError(f"Seed aliases file not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("Seed aliases CSV is empty or missing a header row.")
        missing = [
            fieldname
            for fieldname in SEED_ALIAS_FIELDNAMES
            if fieldname not in reader.fieldnames
        ]
        if missing:
            raise ValueError(
                "Seed aliases CSV is missing required column(s): "
                + ", ".join(missing)
            )
        return alias_map_from_seed_rows(list(reader))


def split_esco_label_field(value: Any) -> list[str]:
    if value is None:
        return []
    labels: list[str] = []
    for line in str(value).splitlines():
        label = collapse_spaces(line)
        if label:
            labels.append(label)
    if not labels and collapse_spaces(str(value)):
        labels.append(collapse_spaces(str(value)))
    return labels


def build_esco_label_lookup(rows: Sequence[Mapping[str, Any]]) -> EscoLabelLookup:
    label_uris_by_key: dict[str, set[str]] = collections.defaultdict(set)
    for row in rows:
        esco_skill_uri = collapse_spaces(str(row.get("esco_skill_uri") or ""))
        if not esco_skill_uri:
            continue
        label_values = []
        label_values.extend(split_esco_label_field(row.get("preferred_label")))
        label_values.extend(split_esco_label_field(row.get("alt_labels")))
        label_values.extend(split_esco_label_field(row.get("hidden_labels")))
        for label in label_values:
            label_key = normalize_alias_key(label)
            if label_key:
                label_uris_by_key[label_key].add(esco_skill_uri)
    return EscoLabelLookup(dict(label_uris_by_key))


def normalize_skill(
    raw_skill_name: str,
    alias_map: Mapping[str, SkillAlias],
    esco_lookup: EscoLabelLookup | None,
    esco_linking: bool,
) -> NormalizationResult:
    alias_key = normalize_alias_key(raw_skill_name)
    alias = alias_map.get(alias_key)
    if alias is None:
        canonical_key = alias_key
        canonical_display = display_from_key(canonical_key, raw_skill_name)
        source = "base_normalization"
        confidence = "medium"
        notes = "Conservative lowercase/spacing normalization only."
    else:
        canonical_key = alias.canonical_key
        canonical_display = alias.canonical_display
        source = alias.source
        confidence = alias.confidence
        notes = alias.notes

    esco_skill_uri = None
    esco_match_status = "not_checked"
    if esco_linking and esco_lookup is not None:
        matching_uris = esco_lookup.uris_for_key(canonical_key)
        if len(matching_uris) == 1:
            esco_skill_uri = next(iter(matching_uris))
            esco_match_status = "matched"
        elif len(matching_uris) > 1:
            esco_match_status = "ambiguous"
            ambiguity_note = (
                "ESCO exact label is ambiguous across "
                f"{len(matching_uris)} skills."
            )
            notes = append_note(notes, ambiguity_note)
        else:
            esco_match_status = "not_found"

    return NormalizationResult(
        raw_skill_name=raw_skill_name,
        alias_key=alias_key,
        canonical_key=canonical_key,
        canonical_display=canonical_display,
        source=source,
        confidence=confidence,
        esco_skill_uri=esco_skill_uri,
        esco_match_status=esco_match_status,
        generic_skill_candidate=canonical_key in GENERIC_SKILL_KEYS,
        notes=notes,
    )


def append_note(existing: str, note: str) -> str:
    if not existing:
        return note
    if note in existing:
        return existing
    return f"{existing} {note}"


def find_duplicate_collapses(
    role_skills: Sequence[RoleSkillRow],
    normalized_by_identity: Mapping[tuple[str, str, str, str], NormalizationResult],
    job_titles_by_role_id: Mapping[str, str],
) -> list[DuplicateCollapseRow]:
    raw_names_by_role_and_key: dict[tuple[str, str], list[str]] = collections.defaultdict(list)
    seen_raw_names_by_role_and_key: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for row in role_skills:
        result = normalized_by_identity[row.identity_key]
        group_key = (row.role_id, result.canonical_key)
        if row.skill_name in seen_raw_names_by_role_and_key[group_key]:
            continue
        raw_names_by_role_and_key[group_key].append(row.skill_name)
        seen_raw_names_by_role_and_key[group_key].add(row.skill_name)

    duplicates: list[DuplicateCollapseRow] = []
    for (role_id, canonical_key), raw_skill_names in sorted(
        raw_names_by_role_and_key.items()
    ):
        if len(raw_skill_names) < 2:
            continue
        duplicates.append(
            DuplicateCollapseRow(
                role_id=role_id,
                job_title=job_titles_by_role_id.get(role_id, ""),
                canonical_key=canonical_key,
                raw_skill_names_that_collapsed=raw_skill_names,
            )
        )
    return duplicates


def build_review_rows(
    role_skills: Sequence[RoleSkillRow],
    normalized_by_identity: Mapping[tuple[str, str, str, str], NormalizationResult],
) -> list[ReviewRow]:
    rows_by_raw_skill: dict[str, list[RoleSkillRow]] = collections.defaultdict(list)
    for row in role_skills:
        rows_by_raw_skill[row.skill_name].append(row)

    review_rows: list[ReviewRow] = []
    for raw_skill_name, rows in sorted(
        rows_by_raw_skill.items(),
        key=lambda item: normalize_alias_key(item[0]),
    ):
        first_result = normalized_by_identity[rows[0].identity_key]
        old_normalized_values = sorted(
            {row.normalized_skill_name for row in rows if row.normalized_skill_name}
        )
        review_rows.append(
            ReviewRow(
                raw_skill_name=raw_skill_name,
                raw_skill_count=len(rows),
                old_normalized_skill_name="; ".join(old_normalized_values),
                new_normalized_skill_name=first_result.canonical_key,
                canonical_display=first_result.canonical_display,
                source=first_result.source,
                confidence=first_result.confidence,
                esco_skill_uri=first_result.esco_skill_uri,
                esco_match_status=first_result.esco_match_status,
                generic_skill_candidate=first_result.generic_skill_candidate,
                notes=first_result.notes,
            )
        )
    return review_rows


def write_review_csv(path: Path, rows: Sequence[ReviewRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "raw_skill_name": row.raw_skill_name,
                    "raw_skill_count": row.raw_skill_count,
                    "old_normalized_skill_name": row.old_normalized_skill_name,
                    "new_normalized_skill_name": row.new_normalized_skill_name,
                    "canonical_display": row.canonical_display,
                    "source": row.source,
                    "confidence": row.confidence,
                    "esco_skill_uri": row.esco_skill_uri or "",
                    "esco_match_status": row.esco_match_status,
                    "generic_skill_candidate": format_bool(
                        row.generic_skill_candidate
                    ),
                    "notes": row.notes,
                }
            )


def write_duplicates_csv(path: Path, rows: Sequence[DuplicateCollapseRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DUPLICATE_FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "role_id": row.role_id,
                    "job_title": row.job_title,
                    "canonical_key": row.canonical_key,
                    "raw_skill_names_that_collapsed": "; ".join(
                        row.raw_skill_names_that_collapsed
                    ),
                }
            )


def format_bool(value: bool) -> str:
    return "true" if value else "false"


def merge_alias_maps(
    seed_aliases: Mapping[str, SkillAlias],
    existing_aliases: Mapping[str, SkillAlias],
    force: bool,
) -> dict[str, SkillAlias]:
    if force:
        merged = dict(existing_aliases)
        merged.update(seed_aliases)
        return merged
    merged = dict(seed_aliases)
    merged.update(existing_aliases)
    return merged


def build_generated_aliases(
    review_rows: Sequence[ReviewRow],
) -> dict[str, SkillAlias]:
    generated: dict[str, SkillAlias] = {}
    for row in review_rows:
        alias_key = normalize_alias_key(row.raw_skill_name)
        if not alias_key:
            continue
        validate_alias_safety(alias_key, row.new_normalized_skill_name)
        generated[alias_key] = SkillAlias(
            alias_key=alias_key,
            alias_display=display_from_key(alias_key, row.raw_skill_name),
            canonical_key=row.new_normalized_skill_name,
            canonical_display=row.canonical_display,
            esco_skill_uri=row.esco_skill_uri,
            source=row.source,
            confidence=row.confidence,
            notes=row.notes,
        )
    return generated


def attach_esco_links_to_aliases(
    aliases: Mapping[str, SkillAlias],
    esco_lookup: EscoLabelLookup | None,
    esco_linking: bool,
) -> dict[str, SkillAlias]:
    linked: dict[str, SkillAlias] = {}
    for alias_key, alias in aliases.items():
        esco_skill_uri = alias.esco_skill_uri
        if esco_linking and esco_lookup is not None:
            matching_uris = esco_lookup.uris_for_key(alias.canonical_key)
            if len(matching_uris) == 1:
                esco_skill_uri = next(iter(matching_uris))
            elif len(matching_uris) > 1:
                esco_skill_uri = None
        linked[alias_key] = alias.with_esco_skill_uri(esco_skill_uri)
    return linked


def alias_rows_to_write(
    seed_aliases: Mapping[str, SkillAlias],
    generated_aliases: Mapping[str, SkillAlias],
    existing_aliases: Mapping[str, SkillAlias],
    esco_lookup: EscoLabelLookup | None,
    esco_linking: bool,
    force: bool,
) -> tuple[list[SkillAlias], AliasWriteStats]:
    desired = dict(generated_aliases)
    desired.update(seed_aliases)
    desired = attach_esco_links_to_aliases(desired, esco_lookup, esco_linking)

    rows: list[SkillAlias] = []
    stats = AliasWriteStats()
    for alias_key, alias in sorted(desired.items()):
        exists = alias_key in existing_aliases
        if exists and not force:
            stats.aliases_reused += 1
            continue
        rows.append(alias)
        if exists:
            stats.aliases_updated += 1
        else:
            stats.aliases_inserted += 1
    return rows, stats


def role_skill_updates_to_write(
    role_skills: Sequence[RoleSkillRow],
    normalized_by_identity: Mapping[tuple[str, str, str, str], NormalizationResult],
) -> list[tuple[RoleSkillRow, NormalizationResult]]:
    updates: list[tuple[RoleSkillRow, NormalizationResult]] = []
    update_filters = collections.Counter(
        (
            row.row_id or "",
            row.role_id,
            row.skill_name,
            row.normalized_skill_name,
        )
        for row in role_skills
    )
    unsafe_filters = [key for key, count in update_filters.items() if count > 1]
    if unsafe_filters:
        raise ValueError(
            "role_skills contains duplicate update filters; refusing broad update."
        )

    for row in role_skills:
        result = normalized_by_identity[row.identity_key]
        if row.normalized_skill_name != result.canonical_key:
            updates.append((row, result))
    return updates


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
        self._role_skill_id_available: bool | None = None

    def validate_schema(self) -> None:
        self._request(
            "GET",
            self.schema.role_skills_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.skill_name_column,
                            self.schema.normalized_skill_name_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )
        self._request(
            "GET",
            self.schema.roles_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.job_title_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )
        self._request(
            "GET",
            self.schema.skill_aliases_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            "alias_key",
                            "alias_display",
                            "canonical_key",
                            "canonical_display",
                            "esco_skill_uri",
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )

    def role_skill_id_available(self) -> bool:
        if self._role_skill_id_available is not None:
            return self._role_skill_id_available
        try:
            self._request(
                "GET",
                self.schema.role_skills_table,
                query=[("select", self.schema.role_skill_id_column), ("limit", "1")],
            )
        except SupabaseError:
            self._role_skill_id_available = False
        else:
            self._role_skill_id_available = True
        return self._role_skill_id_available

    def list_role_skills(self) -> list[RoleSkillRow]:
        columns = [
            self.schema.role_id_column,
            self.schema.skill_name_column,
            self.schema.normalized_skill_name_column,
        ]
        if self.role_skill_id_available():
            columns.insert(0, self.schema.role_skill_id_column)

        rows = self._paged_get(
            self.schema.role_skills_table,
            select=",".join(columns),
            extra_query=[("order", f"{self.schema.role_id_column}.asc")],
        )
        return [
            RoleSkillRow(
                row_id=string_or_none(row.get(self.schema.role_skill_id_column)),
                role_id=str(row.get(self.schema.role_id_column)),
                skill_name=str(row.get(self.schema.skill_name_column) or ""),
                normalized_skill_name=str(
                    row.get(self.schema.normalized_skill_name_column) or ""
                ),
            )
            for row in rows
        ]

    def list_job_titles_by_role_id(self) -> dict[str, str]:
        rows = self._paged_get(
            self.schema.roles_table,
            select=",".join(
                [self.schema.role_id_column, self.schema.job_title_column]
            ),
            extra_query=[("order", f"{self.schema.role_id_column}.asc")],
        )
        return {
            str(row.get(self.schema.role_id_column)): str(
                row.get(self.schema.job_title_column) or ""
            )
            for row in rows
            if row.get(self.schema.role_id_column) is not None
        }

    def list_esco_skills(self) -> list[dict[str, Any]]:
        return self._paged_get(
            self.schema.esco_skills_table,
            select=",".join(
                [
                    self.schema.esco_skill_uri_column,
                    self.schema.preferred_label_column,
                    self.schema.alt_labels_column,
                    self.schema.hidden_labels_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.esco_skill_uri_column}.asc")],
        )

    def list_skill_aliases(self) -> dict[str, SkillAlias]:
        rows = self._paged_get(
            self.schema.skill_aliases_table,
            select=",".join(
                [
                    "alias_key",
                    "alias_display",
                    "canonical_key",
                    "canonical_display",
                    "esco_skill_uri",
                ]
            ),
            extra_query=[("order", "alias_key.asc")],
        )
        aliases: dict[str, SkillAlias] = {}
        for row in rows:
            alias = skill_alias_from_mapping(row)
            aliases[alias.alias_key] = alias
        return aliases

    def upsert_skill_aliases(
        self,
        aliases: Sequence[SkillAlias],
        force: bool,
    ) -> None:
        if not aliases:
            return
        resolution = "merge-duplicates" if force else "ignore-duplicates"
        for alias_chunk in chunked(list(aliases)):
            self._request(
                "POST",
                self.schema.skill_aliases_table,
                query=[("on_conflict", "alias_key")],
                payload=[alias.to_payload() for alias in alias_chunk],
                prefer=f"resolution={resolution},return=minimal",
            )

    def update_role_skills(
        self,
        updates: Sequence[tuple[RoleSkillRow, NormalizationResult]],
    ) -> RoleSkillUpdateStats:
        stats = RoleSkillUpdateStats()
        for row, result in updates:
            if row.row_id is not None:
                query = [
                    (self.schema.role_skill_id_column, f"eq.{row.row_id}"),
                ]
            else:
                query = [
                    (self.schema.role_id_column, f"eq.{row.role_id}"),
                    (self.schema.skill_name_column, f"eq.{row.skill_name}"),
                    (
                        self.schema.normalized_skill_name_column,
                        f"eq.{row.normalized_skill_name}",
                    ),
                ]
            self._request(
                "PATCH",
                self.schema.role_skills_table,
                query=query,
                payload={
                    self.schema.normalized_skill_name_column: result.canonical_key,
                },
                prefer="return=minimal",
            )
            stats.role_skills_updated += 1
        return stats

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
            "User-Agent": "career-compass-skill-normalizer/1.0",
        }
        if not self.service_role_key.startswith(("sb_secret_", "sb_publishable_")):
            headers["Authorization"] = f"Bearer {self.service_role_key}"
        return headers


def string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def chunked(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


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


def print_summary(
    role_skills: Sequence[RoleSkillRow],
    review_rows: Sequence[ReviewRow],
    seed_aliases: Mapping[str, SkillAlias],
    existing_aliases: Mapping[str, SkillAlias],
    alias_stats: AliasWriteStats,
    role_skill_updates: Sequence[tuple[RoleSkillRow, NormalizationResult]],
    esco_lookup: EscoLabelLookup | None,
    esco_linking: bool,
    duplicate_rows: Sequence[DuplicateCollapseRow],
    review_output: Path,
    duplicates_output: Path,
    dry_run: bool,
    force: bool,
) -> None:
    esco_exact_matches = sum(
        1 for row in review_rows if row.esco_match_status == "matched"
    )
    esco_ambiguous_matches = sum(
        1 for row in review_rows if row.esco_match_status == "ambiguous"
    )
    generic_candidates = sum(1 for row in review_rows if row.generic_skill_candidate)
    role_skill_unchanged = len(role_skills) - len(role_skill_updates)
    esco_label_keys = 0 if esco_lookup is None else len(esco_lookup.label_uris_by_key)

    print(f"Dry run: {'yes' if dry_run else 'no'}")
    print(f"Force alias updates: {'yes' if force else 'no'}")
    print(f"Total role_skills rows read: {len(role_skills)}")
    print(f"Unique raw skills found: {len(review_rows)}")
    print(f"Aliases loaded from seed file: {len(seed_aliases)}")
    print(f"Existing skill_aliases reused from Supabase: {len(existing_aliases)}")
    alias_insert_label = "Aliases that would be inserted" if dry_run else "Aliases inserted"
    alias_update_label = "Aliases that would be updated" if dry_run else "Aliases updated"
    print(f"{alias_insert_label}: {alias_stats.aliases_inserted}")
    print(f"{alias_update_label}: {alias_stats.aliases_updated}")
    print(f"Aliases reused: {alias_stats.aliases_reused}")
    print(f"role_skills unchanged: {role_skill_unchanged}")
    if dry_run:
        print(f"role_skills that would be updated: {len(role_skill_updates)}")
    else:
        print(f"role_skills updated: {len(role_skill_updates)}")
    if esco_linking:
        print(f"ESCO exact label keys loaded: {esco_label_keys}")
        print(f"ESCO exact matches found: {esco_exact_matches}")
        print(f"ESCO ambiguous matches: {esco_ambiguous_matches}")
    else:
        print("ESCO exact linking disabled by --no-esco-linking.")
        print("ESCO exact matches found: 0")
        print("ESCO ambiguous matches: 0")
    print(f"Generic skill candidates: {generic_candidates}")
    print(f"Duplicate normalized skills per role: {len(duplicate_rows)}")
    print(f"Review CSV: {review_output}")
    print(f"Duplicate report CSV: {duplicates_output}")
    if dry_run:
        print("Dry run only. No Supabase writes were made.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database enrichment: normalize "
            "role_skills.normalized_skill_name for Phase 5."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read data and write review CSVs without writing to Supabase.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Refresh existing skill_aliases rows from seed/generated aliases.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
        help="Path for the normalization review CSV.",
    )
    parser.add_argument(
        "--duplicates-output",
        type=Path,
        default=DEFAULT_DUPLICATES_OUTPUT,
        help="Path for the same-role duplicate collapse report CSV.",
    )
    parser.add_argument(
        "--seed-aliases",
        type=Path,
        default=DEFAULT_SEED_ALIASES_PATH,
        help="Path to the deterministic seed alias CSV.",
    )
    parser.add_argument(
        "--no-esco-linking",
        action="store_true",
        help="Skip exact ESCO skill label lookup and skill_aliases.esco_skill_uri links.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        seed_aliases = load_seed_aliases(args.seed_aliases)
        supabase_url, service_role_key = get_required_env()
        client = SupabaseRestClient(supabase_url, service_role_key)
        client.validate_schema()

        role_skills = client.list_role_skills()
        job_titles_by_role_id = client.list_job_titles_by_role_id()
        existing_aliases = client.list_skill_aliases()
        alias_map = merge_alias_maps(
            seed_aliases,
            existing_aliases,
            force=args.force,
        )

        esco_linking = not args.no_esco_linking
        esco_lookup = None
        if esco_linking:
            esco_lookup = build_esco_label_lookup(client.list_esco_skills())

        normalized_by_identity = {
            row.identity_key: normalize_skill(
                row.skill_name,
                alias_map,
                esco_lookup=esco_lookup,
                esco_linking=esco_linking,
            )
            for row in role_skills
        }
        review_rows = build_review_rows(role_skills, normalized_by_identity)
        duplicate_rows = find_duplicate_collapses(
            role_skills,
            normalized_by_identity,
            job_titles_by_role_id,
        )
        generated_aliases = build_generated_aliases(review_rows)
        aliases_to_write, alias_stats = alias_rows_to_write(
            seed_aliases,
            generated_aliases,
            existing_aliases,
            esco_lookup=esco_lookup,
            esco_linking=esco_linking,
            force=args.force,
        )
        role_skill_updates = role_skill_updates_to_write(
            role_skills,
            normalized_by_identity,
        )

        write_review_csv(args.review_output, review_rows)
        write_duplicates_csv(args.duplicates_output, duplicate_rows)

        if not args.dry_run:
            client.upsert_skill_aliases(aliases_to_write, force=args.force)
            client.update_role_skills(role_skill_updates)

        print_summary(
            role_skills=role_skills,
            review_rows=review_rows,
            seed_aliases=seed_aliases,
            existing_aliases=existing_aliases,
            alias_stats=alias_stats,
            role_skill_updates=role_skill_updates,
            esco_lookup=esco_lookup,
            esco_linking=esco_linking,
            duplicate_rows=duplicate_rows,
            review_output=args.review_output,
            duplicates_output=args.duplicates_output,
            dry_run=args.dry_run,
            force=args.force,
        )
        return 0
    except (FileNotFoundError, ValueError, SupabaseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
