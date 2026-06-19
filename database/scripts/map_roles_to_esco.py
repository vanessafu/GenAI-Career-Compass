#!/usr/bin/env python3
"""Map Career Compass roles to one primary ESCO occupation.

One-time database enrichment script. Kept for auditability and controlled reruns
while rebuilding the seeded Career Compass database; not app runtime code.
Prefer --dry-run before any write-mode rerun.

Phase 6 keeps `career_roles` as the user-facing role catalog and uses ESCO only
as a background grounding layer. It builds compact profile text for each Career
Compass role and ESCO occupation, embeds those profiles with OpenAI
`text-embedding-3-small`, scores candidate ESCO matches, and writes one primary
mapping per role to `esco_mappings`.

Examples:

    python scripts/map_roles_to_esco.py --dry-run
    python scripts/map_roles_to_esco.py
    python scripts/map_roles_to_esco.py --force
    python scripts/map_roles_to_esco.py --limit 20
    python scripts/map_roles_to_esco.py --role-id 123
    python scripts/map_roles_to_esco.py --top-k 5
    python scripts/map_roles_to_esco.py --no-openai-cache-refresh

Set SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and OPENAI_API_KEY in your local
environment or a local .env file. Do not expose service role or OpenAI keys in
frontend code.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


BATCH_SIZE = 500
LOOKUP_FILTER_BATCH_SIZE = 100
OPENAI_EMBEDDING_BATCH_SIZE = 64
DEFAULT_MODEL = "text-embedding-3-small"
DEFAULT_REVIEW_OUTPUT = Path("data/esco_role_mapping_review.csv")
DEFAULT_CACHE_DIR = Path("data/embedding_cache")
DEFAULT_MANUAL_OVERRIDES = Path("data/esco_mapping_overrides.csv")

# Calibrated on the Phase 6 Career Compass dataset after cache-warmed dry runs.
# `text-embedding-3-small` profile similarities top out around the high 0.60s
# here, so the original 0.75/0.60 review bands were too high for this corpus.
AUTO_ACCEPTED_MIN_SCORE = 0.55
NEEDS_REVIEW_MIN_SCORE = 0.43
AUTO_ACCEPTED_MIN_MARGIN = 0.05

SEMANTIC_WEIGHT = 0.75
SKILL_OVERLAP_WEIGHT = 0.20
DOMAIN_HINT_WEIGHT = 0.05

MAX_ROLE_SKILLS = 80
MAX_ROLE_CERTIFICATIONS = 30
MAX_DESCRIPTION_CHARS = 1600
MAX_ESCO_ESSENTIAL_SKILLS = 40
MAX_ESCO_OPTIONAL_SKILLS = 20
MAX_ESCO_OTHER_SKILLS = 20


REVIEW_FIELDNAMES = [
    "role_id",
    "job_title",
    "domain_tags",
    "selected_esco_title",
    "selected_esco_uri",
    "selected_isco_code",
    "match_score",
    "semantic_score",
    "skill_overlap_score",
    "domain_hint_score",
    "mapping_status",
    "margin_to_second",
    "top_1_title",
    "top_1_score",
    "top_2_title",
    "top_2_score",
    "top_3_title",
    "top_3_score",
    "manual_override",
    "notes",
]


@dataclass(frozen=True)
class SchemaConfig:
    roles_table: str = "career_roles"
    role_skills_table: str = "role_skills"
    certifications_table: str = "certifications"
    certifications_mapping_table: str = "certifications_mapping"
    occupations_table: str = "esco_occupations"
    esco_skills_table: str = "esco_skills"
    occupation_skills_table: str = "esco_occupation_skills"
    mappings_table: str = "esco_mappings"
    role_id_column: str = "role_id"
    job_title_column: str = "job_title"
    job_description_column: str = "job_description"
    raw_skills_column: str = "raw_skills"
    raw_certifications_column: str = "raw_certifications"
    domain_tags_column: str = "domain_tags"
    certification_id_column: str = "certification_id"
    skill_name_column: str = "skill_name"
    normalized_skill_name_column: str = "normalized_skill_name"
    certification_name_column: str = "certification_name"
    esco_uri_column: str = "esco_uri"
    isco_code_column: str = "isco_code"
    name_column: str = "name"
    definition_column: str = "definition"
    esco_skill_uri_column: str = "esco_skill_uri"
    preferred_label_column: str = "preferred_label"
    relation_type_column: str = "relation_type"
    skill_type_column: str = "skill_type"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass(frozen=True)
class CareerRoleProfile:
    role_id: str
    job_title: str
    job_description: str
    raw_skills: str
    raw_certifications: str
    domain_tags: str
    normalized_skills: list[str] = field(default_factory=list)
    raw_skill_names: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    normalized_skill_esco_uris: dict[str, list[str]] = field(default_factory=dict)

    def normalized_skill_labels(self) -> list[str]:
        return dedupe_nonempty(normalize_skill_label(skill) for skill in self.normalized_skills)


@dataclass(frozen=True)
class EscoSkillLink:
    preferred_label: str
    relation_type: str
    esco_skill_uri: str = ""
    skill_type: str | None = None


@dataclass(frozen=True)
class EscoOccupationProfile:
    esco_uri: str
    isco_code: str | None
    name: str
    definition: str
    skill_links: list[EscoSkillLink] = field(default_factory=list)

    def linked_skill_labels(self) -> list[str]:
        return dedupe_nonempty(
            normalize_skill_label(link.preferred_label)
            for link in self.skill_links
            if link.preferred_label
        )

    def linked_skill_uris(self) -> set[str]:
        return {
            link.esco_skill_uri
            for link in self.skill_links
            if link.esco_skill_uri
        }


@dataclass(frozen=True)
class CandidateScore:
    esco_uri: str
    esco_title: str
    isco_code: str | None
    final_score: float
    semantic_score: float
    skill_overlap_score: float
    domain_hint_score: float
    brief_reason: str


@dataclass(frozen=True)
class ManualOverride:
    role_id: str
    job_title: str
    esco_uri: str
    esco_title: str
    notes: str


@dataclass(frozen=True)
class MappingDecision:
    role: CareerRoleProfile
    selected: CandidateScore
    top_candidates: list[CandidateScore]
    mapping_status: str
    manual_override: bool
    margin_to_second: float | None
    notes: str = ""


@dataclass
class EmbeddingStats:
    loaded_from_cache: int = 0
    generated: int = 0


@dataclass
class WriteStats:
    mappings_upserted: int = 0
    mappings_skipped_existing_non_manual: int = 0


class SupabaseError(RuntimeError):
    """Raised when Supabase returns an error response."""


class OpenAIEmbeddingError(RuntimeError):
    """Raised when OpenAI embeddings cannot be generated."""


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def truncate_text(value: str, max_chars: int = MAX_DESCRIPTION_CHARS) -> str:
    value = collapse_spaces(value)
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 3].rstrip() + "..."


def dedupe_nonempty(values: Iterable[str], limit: int | None = None) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = collapse_spaces(str(raw_value or ""))
        if not value:
            continue
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        items.append(value)
        if limit is not None and len(items) >= limit:
            break
    return items


def split_raw_list(value: str) -> list[str]:
    return dedupe_nonempty(part.strip() for part in (value or "").split(","))


def normalize_skill_label(value: str) -> str:
    return collapse_spaces(value).casefold()


def build_career_role_profile_text(role: CareerRoleProfile) -> str:
    skills = dedupe_nonempty(role.normalized_skills, limit=MAX_ROLE_SKILLS)
    if not skills:
        skills = dedupe_nonempty(role.raw_skill_names, limit=MAX_ROLE_SKILLS)
    if not skills:
        skills = dedupe_nonempty(split_raw_list(role.raw_skills), limit=MAX_ROLE_SKILLS)

    certifications = dedupe_nonempty(
        role.certifications,
        limit=MAX_ROLE_CERTIFICATIONS,
    )
    if not certifications:
        certifications = dedupe_nonempty(
            split_raw_list(role.raw_certifications),
            limit=MAX_ROLE_CERTIFICATIONS,
        )

    lines = [f"Role title: {collapse_spaces(role.job_title)}"]
    description = truncate_text(role.job_description)
    if description:
        lines.append(f"Description: {description}")
    domain_tags = collapse_spaces(role.domain_tags)
    if domain_tags:
        lines.append(f"Domain tags: {domain_tags}")
    if skills:
        lines.append("Skills: " + ", ".join(skills))
    if certifications:
        lines.append("Certifications: " + ", ".join(certifications))
    return "\n".join(lines)


def build_esco_occupation_profile_text(occupation: EscoOccupationProfile) -> str:
    essential: list[str] = []
    optional: list[str] = []
    other: list[str] = []

    for link in occupation.skill_links:
        label = collapse_spaces(link.preferred_label)
        if not label:
            continue
        relation_type = normalize_skill_label(link.relation_type)
        if relation_type == "essential":
            essential.append(label)
        elif relation_type == "optional":
            optional.append(label)
        else:
            other.append(label)

    lines = [f"ESCO occupation: {collapse_spaces(occupation.name)}"]
    definition = truncate_text(occupation.definition)
    if definition:
        lines.append(f"Definition: {definition}")
    essential_labels = dedupe_nonempty(essential, limit=MAX_ESCO_ESSENTIAL_SKILLS)
    optional_labels = dedupe_nonempty(optional, limit=MAX_ESCO_OPTIONAL_SKILLS)
    other_labels = dedupe_nonempty(other, limit=MAX_ESCO_OTHER_SKILLS)
    if essential_labels:
        lines.append("Essential skills: " + ", ".join(essential_labels))
    if optional_labels:
        lines.append("Optional skills: " + ", ".join(optional_labels))
    if other_labels:
        lines.append("Other linked skills: " + ", ".join(other_labels))
    return "\n".join(lines)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left or not right:
        return 0.0
    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def skill_overlap_details(
    role: CareerRoleProfile,
    occupation: EscoOccupationProfile,
) -> tuple[float, int, int]:
    role_skills = role.normalized_skill_labels()
    if not role_skills:
        return 0.0, 0, 0
    esco_skill_labels = set(occupation.linked_skill_labels())
    esco_skill_uris = occupation.linked_skill_uris()
    overlap_count = 0
    for role_skill in role_skills:
        uri_matches = set(role.normalized_skill_esco_uris.get(role_skill, []))
        if role_skill in esco_skill_labels or (uri_matches & esco_skill_uris):
            overlap_count += 1
    return overlap_count / len(role_skills), overlap_count, len(role_skills)


def build_normalized_skill_esco_uri_map(
    normalized_skills: Sequence[str],
    esco_uris_by_canonical_skill: Mapping[str, Sequence[str]],
) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for skill in dedupe_nonempty(
        normalize_skill_label(skill_name) for skill_name in normalized_skills
    ):
        uris = dedupe_nonempty(esco_uris_by_canonical_skill.get(skill, []))
        if uris:
            result[skill] = uris
    return result


def calculate_domain_hint_score(domain_tags: str, esco_profile_text: str) -> float:
    domain_tokens = {
        token
        for token in re.split(r"[,\s]+", normalize_skill_label(domain_tags))
        if token
    }
    esco_text = normalize_skill_label(esco_profile_text)

    if any("security" in token or "cybersecurity" in token for token in domain_tokens):
        if "security" in esco_text:
            return 1.0

    if any(
        token.startswith("data")
        or token in {"ai", "ai_ml", "ml", "machine_learning", "artificial_intelligence"}
        for token in domain_tokens
    ):
        if any(keyword in esco_text for keyword in ("data", "software", "ict")):
            return 0.5

    if domain_tokens & {"devops", "cloud", "infrastructure", "networking", "support"}:
        if any(keyword in esco_text for keyword in ("systems", "system", "network", "ict")):
            return 0.5

    return 0.0


def calculate_final_mapping_score(
    semantic_score: float,
    skill_overlap_score: float,
    domain_hint_score: float,
) -> float:
    return (
        SEMANTIC_WEIGHT * semantic_score
        + SKILL_OVERLAP_WEIGHT * skill_overlap_score
        + DOMAIN_HINT_WEIGHT * domain_hint_score
    )


def margin_to_second_candidate(
    top_score: float,
    second_score: float | None,
) -> float | None:
    if second_score is None:
        return None
    return top_score - second_score


def classify_mapping_status(top_score: float, second_score: float | None) -> str:
    margin = margin_to_second_candidate(top_score, second_score)
    if top_score < NEEDS_REVIEW_MIN_SCORE:
        return "low_confidence"
    if top_score >= AUTO_ACCEPTED_MIN_SCORE and (
        margin is None or margin >= AUTO_ACCEPTED_MIN_MARGIN
    ):
        return "auto_accepted"
    return "needs_review"


def score_candidates(
    role: CareerRoleProfile,
    role_embedding: Sequence[float],
    occupations: Sequence[EscoOccupationProfile],
    occupation_embeddings: Mapping[str, Sequence[float]],
    occupation_profile_texts: Mapping[str, str],
    top_k: int,
) -> list[CandidateScore]:
    candidates: list[CandidateScore] = []
    for occupation in occupations:
        occupation_embedding = occupation_embeddings.get(occupation.esco_uri)
        if occupation_embedding is None:
            continue
        semantic_score = cosine_similarity(role_embedding, occupation_embedding)
        skill_overlap_score, overlap_count, role_skill_count = skill_overlap_details(
            role,
            occupation,
        )
        domain_hint_score = calculate_domain_hint_score(
            role.domain_tags,
            occupation_profile_texts.get(occupation.esco_uri, ""),
        )
        final_score = calculate_final_mapping_score(
            semantic_score,
            skill_overlap_score,
            domain_hint_score,
        )
        candidates.append(
            CandidateScore(
                esco_uri=occupation.esco_uri,
                esco_title=occupation.name,
                isco_code=occupation.isco_code,
                final_score=final_score,
                semantic_score=semantic_score,
                skill_overlap_score=skill_overlap_score,
                domain_hint_score=domain_hint_score,
                brief_reason=(
                    f"Semantic {semantic_score:.3f}; skill overlap "
                    f"{overlap_count}/{role_skill_count}; domain hint "
                    f"{domain_hint_score:.1f}."
                ),
            )
        )

    candidates.sort(key=lambda candidate: candidate.final_score, reverse=True)
    return candidates[:top_k]


def choose_mapping_decision(
    role: CareerRoleProfile,
    top_candidates: Sequence[CandidateScore],
    manual_override: ManualOverride | None,
    occupations_by_uri: Mapping[str, EscoOccupationProfile],
) -> MappingDecision:
    if manual_override is not None:
        occupation = occupations_by_uri.get(manual_override.esco_uri)
        if occupation is None:
            raise ValueError(
                "Manual override references unknown esco_uri: "
                f"{manual_override.esco_uri}"
            )
        selected = next(
            (
                candidate
                for candidate in top_candidates
                if candidate.esco_uri == manual_override.esco_uri
            ),
            None,
        )
        if selected is None:
            selected = CandidateScore(
                esco_uri=occupation.esco_uri,
                esco_title=manual_override.esco_title or occupation.name,
                isco_code=occupation.isco_code,
                final_score=1.0,
                semantic_score=0.0,
                skill_overlap_score=0.0,
                domain_hint_score=0.0,
                brief_reason="Manual override selected.",
            )
        return MappingDecision(
            role=role,
            selected=selected,
            top_candidates=list(top_candidates),
            mapping_status="manual_override",
            manual_override=True,
            margin_to_second=decision_margin(top_candidates),
            notes=manual_override.notes,
        )

    if not top_candidates:
        raise ValueError(f"No ESCO candidates were scored for role_id {role.role_id}.")
    selected = top_candidates[0]
    second_score = top_candidates[1].final_score if len(top_candidates) > 1 else None
    return MappingDecision(
        role=role,
        selected=selected,
        top_candidates=list(top_candidates),
        mapping_status=classify_mapping_status(selected.final_score, second_score),
        manual_override=False,
        margin_to_second=margin_to_second_candidate(selected.final_score, second_score),
        notes="",
    )


def decision_margin(top_candidates: Sequence[CandidateScore]) -> float | None:
    if len(top_candidates) < 2:
        return None
    return top_candidates[0].final_score - top_candidates[1].final_score


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


def get_required_supabase_env() -> tuple[str, str]:
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


def get_openai_api_key() -> str:
    load_dotenv_file(Path(".env"))
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise OpenAIEmbeddingError(
            "Missing OPENAI_API_KEY. Add it to your environment or .env, or run "
            "with --no-openai-cache-refresh when every requested embedding is cached."
        )
    return api_key


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


def format_postgrest_in_filter(values: Iterable[Any]) -> str:
    formatted_values = []
    for value in values:
        text = str(value)
        if re.fullmatch(r"-?\d+", text):
            formatted_values.append(text)
        else:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            formatted_values.append(f'"{escaped}"')
    return "in.(" + ",".join(formatted_values) + ")"


def chunked(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


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

    def validate_read_schema(self) -> None:
        checks = [
            (
                self.schema.roles_table,
                [
                    self.schema.role_id_column,
                    self.schema.job_title_column,
                    self.schema.job_description_column,
                    self.schema.raw_skills_column,
                    self.schema.raw_certifications_column,
                    self.schema.domain_tags_column,
                ],
            ),
            (
                self.schema.role_skills_table,
                [
                    self.schema.role_id_column,
                    self.schema.skill_name_column,
                    self.schema.normalized_skill_name_column,
                ],
            ),
            (
                self.schema.certifications_table,
                [
                    self.schema.certification_id_column,
                    self.schema.certification_name_column,
                ],
            ),
            (
                self.schema.certifications_mapping_table,
                [
                    self.schema.role_id_column,
                    self.schema.certification_id_column,
                ],
            ),
            (
                self.schema.occupations_table,
                [
                    self.schema.esco_uri_column,
                    self.schema.isco_code_column,
                    self.schema.name_column,
                    self.schema.definition_column,
                ],
            ),
            (
                self.schema.esco_skills_table,
                [
                    self.schema.esco_skill_uri_column,
                    self.schema.preferred_label_column,
                ],
            ),
            (
                self.schema.occupation_skills_table,
                [
                    self.schema.esco_uri_column,
                    self.schema.esco_skill_uri_column,
                    self.schema.relation_type_column,
                    self.schema.skill_type_column,
                ],
            ),
        ]
        for table, columns in checks:
            self._request(
                "GET",
                table,
                query=[("select", ",".join(columns)), ("limit", "1")],
            )

    def validate_mapping_write_schema(self) -> None:
        self._request(
            "GET",
            self.schema.mappings_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.esco_uri_column,
                            "esco_title",
                            "match_score",
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )

    def list_career_role_profiles(
        self,
        role_id: str | None = None,
        limit: int | None = None,
    ) -> list[CareerRoleProfile]:
        query = [
            (
                "select",
                ",".join(
                    [
                        self.schema.role_id_column,
                        self.schema.job_title_column,
                        self.schema.job_description_column,
                        self.schema.raw_skills_column,
                        self.schema.raw_certifications_column,
                        self.schema.domain_tags_column,
                    ]
                ),
            ),
            ("order", f"{self.schema.role_id_column}.asc"),
        ]
        if role_id is not None:
            query.append((self.schema.role_id_column, f"eq.{role_id}"))
        if limit is not None:
            query.append(("limit", str(limit)))

        rows = self._request("GET", self.schema.roles_table, query=query) or []
        role_ids = [
            str(row.get(self.schema.role_id_column))
            for row in rows
            if row.get(self.schema.role_id_column) is not None
        ]
        skills_by_role_id = self.list_role_skills_by_role_id(role_ids)
        certifications_by_role_id = self.list_certifications_by_role_id(role_ids)
        esco_uris_by_canonical_skill = self.list_esco_skill_uris_by_canonical_skill()

        return [
            CareerRoleProfile(
                role_id=str(row.get(self.schema.role_id_column)),
                job_title=str(row.get(self.schema.job_title_column) or ""),
                job_description=str(row.get(self.schema.job_description_column) or ""),
                raw_skills=str(row.get(self.schema.raw_skills_column) or ""),
                raw_certifications=str(
                    row.get(self.schema.raw_certifications_column) or ""
                ),
                domain_tags=str(row.get(self.schema.domain_tags_column) or ""),
                normalized_skills=[
                    skill_row["normalized_skill_name"]
                    for skill_row in skills_by_role_id.get(
                        str(row.get(self.schema.role_id_column)),
                        [],
                    )
                    if skill_row["normalized_skill_name"]
                ],
                raw_skill_names=[
                    skill_row["skill_name"]
                    for skill_row in skills_by_role_id.get(
                        str(row.get(self.schema.role_id_column)),
                        [],
                    )
                    if skill_row["skill_name"]
                ],
                certifications=certifications_by_role_id.get(
                    str(row.get(self.schema.role_id_column)),
                    [],
                ),
                normalized_skill_esco_uris=build_normalized_skill_esco_uri_map(
                    [
                        skill_row["normalized_skill_name"]
                        for skill_row in skills_by_role_id.get(
                            str(row.get(self.schema.role_id_column)),
                            [],
                        )
                    ],
                    esco_uris_by_canonical_skill,
                ),
            )
            for row in rows
        ]

    def list_esco_skill_uris_by_canonical_skill(self) -> dict[str, list[str]]:
        rows = self._paged_get(
            "skill_aliases",
            select="canonical_key,esco_skill_uri",
            extra_query=[
                ("esco_skill_uri", "not.is.null"),
                ("order", "canonical_key.asc"),
            ],
        )
        grouped: dict[str, list[str]] = collections.defaultdict(list)
        for row in rows:
            canonical_key = normalize_skill_label(str(row.get("canonical_key") or ""))
            esco_skill_uri = str(row.get("esco_skill_uri") or "").strip()
            if canonical_key and esco_skill_uri:
                grouped[canonical_key].append(esco_skill_uri)
        return {
            canonical_key: dedupe_nonempty(uris)
            for canonical_key, uris in grouped.items()
        }

    def list_role_skills_by_role_id(
        self,
        role_ids: Sequence[str],
    ) -> dict[str, list[dict[str, str]]]:
        grouped: dict[str, list[dict[str, str]]] = collections.defaultdict(list)
        if not role_ids:
            return grouped
        for role_id_chunk in chunked(list(role_ids), LOOKUP_FILTER_BATCH_SIZE):
            rows = self._request(
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
                    (
                        self.schema.role_id_column,
                        format_postgrest_in_filter(role_id_chunk),
                    ),
                    ("order", f"{self.schema.role_id_column}.asc"),
                ],
            )
            for row in rows or []:
                role_id = str(row.get(self.schema.role_id_column))
                grouped[role_id].append(
                    {
                        "skill_name": str(row.get(self.schema.skill_name_column) or ""),
                        "normalized_skill_name": str(
                            row.get(self.schema.normalized_skill_name_column) or ""
                        ),
                    }
                )
        return grouped

    def list_certifications_by_role_id(
        self,
        role_ids: Sequence[str],
    ) -> dict[str, list[str]]:
        certification_ids_by_role_id: dict[str, list[str]] = (
            collections.defaultdict(list)
        )
        certification_ids: set[str] = set()
        if not role_ids:
            return collections.defaultdict(list)

        for role_id_chunk in chunked(list(role_ids), LOOKUP_FILTER_BATCH_SIZE):
            rows = self._request(
                "GET",
                self.schema.certifications_mapping_table,
                query=[
                    (
                        "select",
                        ",".join(
                            [
                                self.schema.role_id_column,
                                self.schema.certification_id_column,
                            ]
                        ),
                    ),
                    (
                        self.schema.role_id_column,
                        format_postgrest_in_filter(role_id_chunk),
                    ),
                    ("order", f"{self.schema.role_id_column}.asc"),
                ],
            )
            for row in rows or []:
                role_id = str(row.get(self.schema.role_id_column))
                certification_id = str(
                    row.get(self.schema.certification_id_column) or ""
                )
                if role_id and certification_id:
                    certification_ids_by_role_id[role_id].append(certification_id)
                    certification_ids.add(certification_id)

        certification_names_by_id: dict[str, str] = {}
        for certification_id_chunk in chunked(
            sorted(certification_ids),
            LOOKUP_FILTER_BATCH_SIZE,
        ):
            certification_id_filter = ",".join(certification_id_chunk)
            rows = self._request(
                "GET",
                self.schema.certifications_table,
                query=[
                    (
                        "select",
                        ",".join(
                            [
                                self.schema.certification_id_column,
                                self.schema.certification_name_column,
                            ]
                        ),
                    ),
                    (
                        self.schema.certification_id_column,
                        f"in.({certification_id_filter})",
                    ),
                ],
            )
            for row in rows or []:
                certification_id = str(
                    row.get(self.schema.certification_id_column) or ""
                )
                certification_name = str(
                    row.get(self.schema.certification_name_column) or ""
                ).strip()
                if certification_id and certification_name:
                    certification_names_by_id[certification_id] = certification_name

        grouped: dict[str, list[str]] = collections.defaultdict(list)
        for role_id, role_certification_ids in certification_ids_by_role_id.items():
            for certification_id in role_certification_ids:
                certification_name = certification_names_by_id.get(certification_id)
                if certification_name:
                    grouped[role_id].append(certification_name)
        return grouped

    def list_esco_occupation_profiles(self) -> tuple[list[EscoOccupationProfile], int]:
        occupation_rows = self._paged_get(
            self.schema.occupations_table,
            select=",".join(
                [
                    self.schema.esco_uri_column,
                    self.schema.isco_code_column,
                    self.schema.name_column,
                    self.schema.definition_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.name_column}.asc")],
        )
        skill_rows = self._paged_get(
            self.schema.esco_skills_table,
            select=",".join(
                [
                    self.schema.esco_skill_uri_column,
                    self.schema.preferred_label_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.esco_skill_uri_column}.asc")],
        )
        labels_by_skill_uri = {
            str(row.get(self.schema.esco_skill_uri_column)): str(
                row.get(self.schema.preferred_label_column) or ""
            )
            for row in skill_rows
            if row.get(self.schema.esco_skill_uri_column)
        }
        relation_rows = self._paged_get(
            self.schema.occupation_skills_table,
            select=",".join(
                [
                    self.schema.esco_uri_column,
                    self.schema.esco_skill_uri_column,
                    self.schema.relation_type_column,
                    self.schema.skill_type_column,
                ]
            ),
            extra_query=[("order", f"{self.schema.esco_uri_column}.asc")],
        )
        links_by_occupation_uri: dict[str, list[EscoSkillLink]] = collections.defaultdict(list)
        for row in relation_rows:
            esco_uri = str(row.get(self.schema.esco_uri_column) or "")
            esco_skill_uri = str(row.get(self.schema.esco_skill_uri_column) or "")
            preferred_label = labels_by_skill_uri.get(esco_skill_uri, "")
            if not esco_uri or not preferred_label:
                continue
            links_by_occupation_uri[esco_uri].append(
                EscoSkillLink(
                    preferred_label=preferred_label,
                    relation_type=str(row.get(self.schema.relation_type_column) or ""),
                    esco_skill_uri=esco_skill_uri,
                    skill_type=(
                        None
                        if row.get(self.schema.skill_type_column) is None
                        else str(row.get(self.schema.skill_type_column))
                    ),
                )
            )

        occupations = [
            EscoOccupationProfile(
                esco_uri=str(row.get(self.schema.esco_uri_column) or ""),
                isco_code=(
                    None
                    if row.get(self.schema.isco_code_column) is None
                    else str(row.get(self.schema.isco_code_column))
                ),
                name=str(row.get(self.schema.name_column) or ""),
                definition=str(row.get(self.schema.definition_column) or ""),
                skill_links=links_by_occupation_uri.get(
                    str(row.get(self.schema.esco_uri_column) or ""),
                    [],
                ),
            )
            for row in occupation_rows
            if row.get(self.schema.esco_uri_column)
        ]
        return occupations, len(relation_rows)

    def list_existing_mappings(self) -> dict[str, dict[str, Any]]:
        rows = self._paged_get(
            self.schema.mappings_table,
            select=",".join(
                [
                    self.schema.role_id_column,
                    self.schema.esco_uri_column,
                ]
            ),
        )
        return {
            str(row.get(self.schema.role_id_column)): row
            for row in rows
            if row.get(self.schema.role_id_column) is not None
        }

    def upsert_mappings(self, rows: Sequence[dict[str, Any]]) -> None:
        if not rows:
            return
        for row_chunk in chunked(list(rows)):
            self._request(
                "POST",
                self.schema.mappings_table,
                query=[("on_conflict", self.schema.role_id_column)],
                payload=list(row_chunk),
                prefer="resolution=merge-duplicates,return=minimal",
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
            "User-Agent": "career-compass-esco-mapper/1.0",
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


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def embedding_cache_key(model: str, profile_text: str) -> str:
    stable_hash = text_hash(profile_text)
    return hashlib.sha256(f"{model}\0{stable_hash}".encode("utf-8")).hexdigest()


def load_cached_embedding(
    cache_dir: Path,
    model: str,
    profile_text: str,
) -> list[float] | None:
    stable_text_hash = text_hash(profile_text)
    path = cache_dir / f"{embedding_cache_key(model, profile_text)}.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("model") != model or payload.get("text_hash") != stable_text_hash:
        return None
    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or not all(
        isinstance(value, (int, float)) for value in embedding
    ):
        return None
    return [float(value) for value in embedding]


def write_cached_embedding(
    cache_dir: Path,
    model: str,
    profile_text: str,
    embedding: Sequence[float],
) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / f"{embedding_cache_key(model, profile_text)}.json"
    payload = {
        "model": model,
        "text_hash": text_hash(profile_text),
        "embedding": list(embedding),
    }
    path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


def get_embeddings_for_profiles(
    profile_texts_by_id: Mapping[str, str],
    model: str,
    cache_dir: Path,
    refresh_openai_cache: bool,
) -> tuple[dict[str, list[float]], EmbeddingStats]:
    stats = EmbeddingStats()
    embeddings_by_id: dict[str, list[float]] = {}
    missing: list[tuple[str, str]] = []

    for profile_id, profile_text in profile_texts_by_id.items():
        cached = load_cached_embedding(cache_dir, model, profile_text)
        if cached is None:
            missing.append((profile_id, profile_text))
        else:
            embeddings_by_id[profile_id] = cached
            stats.loaded_from_cache += 1

    if missing and not refresh_openai_cache:
        raise OpenAIEmbeddingError(
            f"{len(missing)} embedding(s) are missing from cache and "
            "--no-openai-cache-refresh was used."
        )

    if missing:
        api_key = get_openai_api_key()
        for missing_chunk in chunked(missing, OPENAI_EMBEDDING_BATCH_SIZE):
            texts = [profile_text for _, profile_text in missing_chunk]
            chunk_embeddings = request_openai_embeddings(texts, model, api_key)
            if len(chunk_embeddings) != len(missing_chunk):
                raise OpenAIEmbeddingError(
                    "OpenAI returned an unexpected number of embeddings."
                )
            for (profile_id, profile_text), embedding in zip(
                missing_chunk,
                chunk_embeddings,
            ):
                embeddings_by_id[profile_id] = embedding
                write_cached_embedding(cache_dir, model, profile_text, embedding)
                stats.generated += 1

    return embeddings_by_id, stats


def request_openai_embeddings(
    texts: Sequence[str],
    model: str,
    api_key: str,
) -> list[list[float]]:
    body = json.dumps(
        {
            "model": model,
            "input": list(texts),
            "encoding_format": "float",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        "https://api.openai.com/v1/embeddings",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "career-compass-esco-mapper/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise OpenAIEmbeddingError(
            f"OpenAI embeddings request failed with HTTP {error.code}: "
            f"{format_openai_error(error_body)}"
        ) from error
    except urllib.error.URLError as error:
        raise OpenAIEmbeddingError(
            f"Could not reach OpenAI embeddings API: {error.reason}"
        ) from error
    except json.JSONDecodeError as error:
        raise OpenAIEmbeddingError("OpenAI embeddings API returned non-JSON data.") from error

    data = payload.get("data")
    if not isinstance(data, list):
        raise OpenAIEmbeddingError("OpenAI embeddings API response did not include data.")
    ordered = sorted(data, key=lambda item: item.get("index", 0))
    embeddings: list[list[float]] = []
    for item in ordered:
        embedding = item.get("embedding")
        if not isinstance(embedding, list):
            raise OpenAIEmbeddingError("OpenAI embeddings API returned a malformed embedding.")
        embeddings.append([float(value) for value in embedding])
    return embeddings


def format_openai_error(response_body: str) -> str:
    try:
        payload = json.loads(response_body)
    except json.JSONDecodeError:
        return redact_secret_like_values(response_body.strip()[:500])
    error_payload = payload.get("error")
    if isinstance(error_payload, dict):
        message = error_payload.get("message")
        if message:
            return redact_secret_like_values(str(message))
    return redact_secret_like_values(response_body.strip()[:500])


def redact_secret_like_values(value: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_*.-]+", "[redacted]", value)


def load_manual_overrides(path: Path) -> list[ManualOverride]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        required = {"esco_uri"}
        missing = required - set(reader.fieldnames)
        if missing:
            raise ValueError(
                "Manual overrides CSV is missing required column(s): "
                + ", ".join(sorted(missing))
            )
        overrides: list[ManualOverride] = []
        for row in reader:
            role_id = collapse_spaces(row.get("role_id") or "")
            job_title = collapse_spaces(row.get("job_title") or "")
            esco_uri = collapse_spaces(row.get("esco_uri") or "")
            if not esco_uri:
                continue
            if not role_id and not job_title:
                raise ValueError(
                    "Manual override rows must include role_id or job_title."
                )
            overrides.append(
                ManualOverride(
                    role_id=role_id,
                    job_title=job_title,
                    esco_uri=esco_uri,
                    esco_title=collapse_spaces(row.get("esco_title") or ""),
                    notes=collapse_spaces(row.get("notes") or ""),
                )
            )
    return overrides


def validate_manual_overrides(
    overrides: Sequence[ManualOverride],
    occupations_by_uri: Mapping[str, EscoOccupationProfile],
) -> None:
    missing_uris = sorted(
        {
            override.esco_uri
            for override in overrides
            if override.esco_uri not in occupations_by_uri
        }
    )
    if missing_uris:
        raise ValueError(
            "Manual override esco_uri value(s) not found in esco_occupations: "
            + ", ".join(missing_uris)
        )


def manual_override_indexes(
    overrides: Sequence[ManualOverride],
) -> tuple[dict[str, ManualOverride], dict[str, ManualOverride]]:
    by_role_id: dict[str, ManualOverride] = {}
    by_job_title: dict[str, ManualOverride] = {}
    for override in overrides:
        if override.role_id:
            by_role_id[override.role_id] = override
        elif override.job_title:
            by_job_title[override.job_title] = override
    return by_role_id, by_job_title


def find_manual_override(
    role: CareerRoleProfile,
    overrides_by_role_id: Mapping[str, ManualOverride],
    overrides_by_job_title: Mapping[str, ManualOverride],
) -> ManualOverride | None:
    if role.role_id in overrides_by_role_id:
        return overrides_by_role_id[role.role_id]
    return overrides_by_job_title.get(role.job_title)


def mapping_payload(decision: MappingDecision) -> dict[str, Any]:
    selected = decision.selected
    return {
        "role_id": decision.role.role_id,
        "esco_uri": selected.esco_uri,
        "esco_title": selected.esco_title,
        "match_score": round(selected.final_score, 6),
    }


def write_review_csv(path: Path, decisions: Sequence[MappingDecision]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_FIELDNAMES)
        writer.writeheader()
        for decision in decisions:
            top_candidates = list(decision.top_candidates)
            row = {
                "role_id": decision.role.role_id,
                "job_title": decision.role.job_title,
                "domain_tags": decision.role.domain_tags,
                "selected_esco_title": decision.selected.esco_title,
                "selected_esco_uri": decision.selected.esco_uri,
                "selected_isco_code": decision.selected.isco_code or "",
                "match_score": format_score(decision.selected.final_score),
                "semantic_score": format_score(decision.selected.semantic_score),
                "skill_overlap_score": format_score(
                    decision.selected.skill_overlap_score
                ),
                "domain_hint_score": format_score(decision.selected.domain_hint_score),
                "mapping_status": decision.mapping_status,
                "margin_to_second": format_optional_score(decision.margin_to_second),
                "manual_override": "true" if decision.manual_override else "false",
                "notes": decision.notes,
            }
            for index in range(3):
                candidate = top_candidates[index] if index < len(top_candidates) else None
                row[f"top_{index + 1}_title"] = "" if candidate is None else candidate.esco_title
                row[f"top_{index + 1}_score"] = (
                    "" if candidate is None else format_score(candidate.final_score)
                )
            writer.writerow(row)


def format_score(value: float) -> str:
    return f"{value:.6f}"


def format_optional_score(value: float | None) -> str:
    if value is None:
        return ""
    return format_score(value)


def build_mapping_decisions(
    roles: Sequence[CareerRoleProfile],
    occupations: Sequence[EscoOccupationProfile],
    role_embeddings: Mapping[str, Sequence[float]],
    occupation_embeddings: Mapping[str, Sequence[float]],
    occupation_profile_texts: Mapping[str, str],
    overrides: Sequence[ManualOverride],
    top_k: int,
) -> list[MappingDecision]:
    occupations_by_uri = {occupation.esco_uri: occupation for occupation in occupations}
    validate_manual_overrides(overrides, occupations_by_uri)
    overrides_by_role_id, overrides_by_job_title = manual_override_indexes(overrides)
    decisions: list[MappingDecision] = []
    for role in roles:
        role_embedding = role_embeddings.get(role.role_id)
        if role_embedding is None:
            raise OpenAIEmbeddingError(
                f"Missing role embedding for role_id {role.role_id}."
            )
        top_candidates = score_candidates(
            role,
            role_embedding,
            occupations,
            occupation_embeddings,
            occupation_profile_texts,
            top_k,
        )
        override = find_manual_override(
            role,
            overrides_by_role_id,
            overrides_by_job_title,
        )
        decisions.append(
            choose_mapping_decision(
                role,
                top_candidates,
                override,
                occupations_by_uri,
            )
        )
    return decisions


def rows_to_upsert(
    decisions: Sequence[MappingDecision],
    existing_mappings: Mapping[str, dict[str, Any]],
    force: bool = False,
) -> tuple[list[dict[str, Any]], WriteStats]:
    stats = WriteStats()
    rows: list[dict[str, Any]] = []
    for decision in decisions:
        existing = existing_mappings.get(decision.role.role_id)
        if existing and not force and not decision.manual_override:
            stats.mappings_skipped_existing_non_manual += 1
            continue
        rows.append(mapping_payload(decision))
    stats.mappings_upserted = len(rows)
    return rows, stats


def print_summary(
    roles: Sequence[CareerRoleProfile],
    occupations: Sequence[EscoOccupationProfile],
    occupation_skill_links_loaded: int,
    role_embedding_stats: EmbeddingStats,
    esco_embedding_stats: EmbeddingStats,
    decisions: Sequence[MappingDecision],
    write_stats: WriteStats,
    review_output: Path,
    dry_run: bool,
) -> None:
    status_counts = collections.Counter(
        decision.mapping_status for decision in decisions
    )
    print(f"Career roles loaded: {len(roles)}")
    print(f"ESCO occupations loaded: {len(occupations)}")
    print(f"ESCO occupation-skill links loaded: {occupation_skill_links_loaded}")
    print(f"Role embeddings generated: {role_embedding_stats.generated}")
    print(
        "Role embeddings loaded from cache: "
        f"{role_embedding_stats.loaded_from_cache}"
    )
    print(f"ESCO embeddings generated: {esco_embedding_stats.generated}")
    print(
        "ESCO embeddings loaded from cache: "
        f"{esco_embedding_stats.loaded_from_cache}"
    )
    print(f"Mappings inserted/upserted: {write_stats.mappings_upserted}")
    print(
        "Mappings skipped because existing row already exists: "
        f"{write_stats.mappings_skipped_existing_non_manual}"
    )
    print(
        "Manual overrides used: "
        f"{sum(1 for decision in decisions if decision.manual_override)}"
    )
    print("Mapping status counts:")
    if status_counts:
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")
    else:
        print("  (none)")
    print(f"Review CSV path: {review_output}")
    print(f"Dry run: {'yes' if dry_run else 'no'}")
    if dry_run:
        print("Dry run only. No Supabase writes were made.")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database enrichment: map Career Compass roles to "
            "primary ESCO occupations."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read data, score mappings, and write review CSV without writing Supabase.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute existing mappings. Manual overrides still come from the override CSV.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of career roles to process.",
    )
    parser.add_argument(
        "--role-id",
        help="Map one career_roles.role_id value.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
        help="Path for the mapping review CSV.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help="Directory for local embedding cache JSON files.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of ESCO candidates to keep per role.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI embedding model. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--manual-overrides",
        type=Path,
        default=DEFAULT_MANUAL_OVERRIDES,
        help="Optional manual mapping override CSV.",
    )
    parser.add_argument(
        "--no-openai-cache-refresh",
        action="store_true",
        help="Do not call OpenAI; fail if any requested embedding is missing from cache.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be greater than zero.")
    if args.top_k < 1:
        parser.error("--top-k must be greater than zero.")

    try:
        supabase_url, service_role_key = get_required_supabase_env()
        client = SupabaseRestClient(supabase_url, service_role_key)
        client.validate_read_schema()
        if not args.dry_run:
            client.validate_mapping_write_schema()

        roles = client.list_career_role_profiles(
            role_id=args.role_id,
            limit=args.limit,
        )
        occupations, occupation_skill_links_loaded = client.list_esco_occupation_profiles()
        if not roles:
            raise ValueError("No career_roles rows matched the requested filters.")
        if not occupations:
            raise ValueError("No esco_occupations rows are available to score.")

        role_profile_texts = {
            role.role_id: build_career_role_profile_text(role)
            for role in roles
        }
        occupation_profile_texts = {
            occupation.esco_uri: build_esco_occupation_profile_text(occupation)
            for occupation in occupations
        }
        refresh_openai_cache = not args.no_openai_cache_refresh
        role_embeddings, role_embedding_stats = get_embeddings_for_profiles(
            role_profile_texts,
            args.model,
            args.cache_dir,
            refresh_openai_cache,
        )
        occupation_embeddings, esco_embedding_stats = get_embeddings_for_profiles(
            occupation_profile_texts,
            args.model,
            args.cache_dir,
            refresh_openai_cache,
        )
        overrides = load_manual_overrides(args.manual_overrides)
        decisions = build_mapping_decisions(
            roles,
            occupations,
            role_embeddings,
            occupation_embeddings,
            occupation_profile_texts,
            overrides,
            args.top_k,
        )
        write_review_csv(args.review_output, decisions)

        write_stats = WriteStats()
        if not args.dry_run:
            existing_mappings = client.list_existing_mappings()
            rows, write_stats = rows_to_upsert(
                decisions,
                existing_mappings,
                force=args.force,
            )
            client.upsert_mappings(rows)

        print_summary(
            roles=roles,
            occupations=occupations,
            occupation_skill_links_loaded=occupation_skill_links_loaded,
            role_embedding_stats=role_embedding_stats,
            esco_embedding_stats=esco_embedding_stats,
            decisions=decisions,
            write_stats=write_stats,
            review_output=args.review_output,
            dry_run=args.dry_run,
        )
        return 0
    except (FileNotFoundError, ValueError, SupabaseError, OpenAIEmbeddingError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
