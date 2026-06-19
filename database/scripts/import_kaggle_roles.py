#!/usr/bin/env python3
"""Import Kaggle IT job roles into Supabase.

One-time database population script. Kept for auditability and controlled
reruns while rebuilding the seeded Career Compass database; not app runtime
code. Prefer --dry-run before any write-mode rerun.

Place the Kaggle CSV anywhere outside frontend/client code and pass its path:

    python scripts/import_kaggle_roles.py --csv IT_Job_Roles_Skills.csv --dry-run
    python scripts/import_kaggle_roles.py --csv IT_Job_Roles_Skills.csv

For a real import, set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your local
shell environment. The service role key belongs only in trusted local/server
environments and must not be exposed in frontend code.

After importing, verify in the Supabase SQL editor:

    select count(*) from career_roles;
    select count(*) from role_skills;
    select count(*) from certifications;
    select count(*) from certifications_mapping;
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Sequence


REQUIRED_COLUMNS = [
    "Job Title",
    "Job Description",
    "Skills",
    "Certifications",
]

BATCH_SIZE = 500

TITLE_WORD_OVERRIDES = {
    ".net": ".NET",
    "ai": "AI",
    "api": "API",
    "apis": "APIs",
    "ar": "AR",
    "aws": "AWS",
    "bi": "BI",
    "c#": "C#",
    "c++": "C++",
    "ccie": "CCIE",
    "ccna": "CCNA",
    "ccnp": "CCNP",
    "ci": "CI",
    "cisa": "CISA",
    "cism": "CISM",
    "cissp": "CISSP",
    "cio": "CIO",
    "ciso": "CISO",
    "crm": "CRM",
    "cto": "CTO",
    "db": "DB",
    "dba": "DBA",
    "devops": "DevOps",
    "elk": "ELK",
    "erp": "ERP",
    "etl": "ETL",
    "gis": "GIS",
    "gcp": "GCP",
    "hpc": "HPC",
    "iaas": "IaaS",
    "ios": "iOS",
    "iot": "IoT",
    "it": "IT",
    "itil": "ITIL",
    "jira": "Jira",
    "jr.": "Jr.",
    "kpi": "KPI",
    "llm": "LLM",
    "ml": "ML",
    "mr": "MR",
    "nlp": "NLP",
    "nosql": "NoSQL",
    "paas": "PaaS",
    "pmp": "PMP",
    "qa": "QA",
    "rpa": "RPA",
    "saas": "SaaS",
    "sap": "SAP",
    "seo": "SEO",
    "sem": "SEM",
    "sql": "SQL",
    "sre": "SRE",
    "sr.": "Sr.",
    "togaf": "TOGAF",
    "ui": "UI",
    "ux": "UX",
    "vr": "VR",
}

LOWERCASE_TITLE_WORDS = {
    "a",
    "an",
    "and",
    "as",
    "at",
    "but",
    "by",
    "for",
    "from",
    "in",
    "nor",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True)
class SchemaConfig:
    roles_table: str = "career_roles"
    role_skills_table: str = "role_skills"
    certifications_table: str = "certifications"
    certifications_mapping_table: str = "certifications_mapping"
    role_id_column: str = "role_id"
    certification_id_column: str = "certification_id"
    job_title_column: str = "job_title"
    job_description_column: str = "job_description"
    raw_skills_column: str = "raw_skills"
    raw_certifications_column: str = "raw_certifications"
    source_row_hash_column: str = "source_row_hash"
    skill_name_column: str = "skill_name"
    normalized_skill_name_column: str = "normalized_skill_name"
    certification_name_column: str = "certification_name"
    normalized_certification_name_column: str = "normalized_certification_name"
    embedding_column: str = "embedding"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass(frozen=True)
class ParsedSkill:
    skill_name: str
    normalized_skill_name: str


@dataclass(frozen=True)
class ParsedCertification:
    certification_name: str
    normalized_certification_name: str


@dataclass(frozen=True)
class ParsedRole:
    job_title: str
    job_description: str
    raw_skills: str
    raw_certifications: str
    source_row_hash: str = ""
    skills: list[ParsedSkill] = field(default_factory=list)
    certifications: list[ParsedCertification] = field(default_factory=list)


@dataclass
class ParseStats:
    rows_read: int = 0
    rows_skipped: int = 0
    duplicate_source_rows: int = 0


@dataclass
class ImportStats:
    roles_inserted: int = 0
    roles_reused_or_updated: int = 0
    skills_inserted: int = 0
    certifications_inserted: int = 0


@dataclass
class ExistingTitleCleanupStats:
    roles_checked: int = 0
    titles_normalized: int = 0


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


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalize_job_title(value: str) -> str:
    title = collapse_spaces(value)
    if not title:
        return ""

    title = re.sub(
        r"\b(sr|jr)\.([A-Za-z])",
        lambda match: f"{match.group(1).capitalize()}. {match.group(2)}",
        title,
        flags=re.IGNORECASE,
    )
    words = collapse_spaces(title).split(" ")
    return " ".join(
        format_title_token(word, index, len(words))
        for index, word in enumerate(words)
    )


def canonical_job_title_key(value: str) -> str:
    return collapse_spaces(normalize_job_title(value)).casefold()


def compute_source_row_hash(role: ParsedRole) -> str:
    return compute_source_row_hash_from_values(
        role.job_title,
        role.job_description,
        role.raw_skills,
        role.raw_certifications,
    )


def compute_source_row_hash_from_values(
    job_title: str,
    job_description: str,
    raw_skills: str,
    raw_certifications: str,
) -> str:
    payload = [
        canonical_job_title_key(job_title),
        collapse_spaces(job_description),
        collapse_spaces(raw_skills),
        collapse_spaces(raw_certifications),
    ]
    encoded_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded_payload).hexdigest()


def role_with_source_row_hash(role: ParsedRole) -> ParsedRole:
    if role.source_row_hash:
        return role
    return replace(role, source_row_hash=compute_source_row_hash(role))


def source_row_hash_for_row(row: dict[str, Any], schema: SchemaConfig) -> str:
    existing_hash = row.get(schema.source_row_hash_column)
    if existing_hash:
        return str(existing_hash)

    return compute_source_row_hash_from_values(
        str(row.get(schema.job_title_column) or ""),
        str(row.get(schema.job_description_column) or ""),
        str(row.get(schema.raw_skills_column) or ""),
        str(row.get(schema.raw_certifications_column) or ""),
    )


def format_title_token(token: str, word_index: int, word_count: int) -> str:
    parts = re.split(r"([/-])", token)
    if len(parts) == 1:
        return format_title_word(token, word_index, word_count)

    return "".join(
        part
        if part in {"/", "-"}
        else format_title_word(part, word_index, word_count)
        for part in parts
    )


def format_title_word(word: str, word_index: int, word_count: int) -> str:
    match = re.match(r"^([^A-Za-z0-9+#.]*)(.*?)([^A-Za-z0-9+#.]*)$", word)
    if not match:
        return word

    prefix, core, suffix = match.groups()
    if not core:
        return word

    normalized_core = core.casefold()
    if normalized_core in TITLE_WORD_OVERRIDES:
        formatted_core = TITLE_WORD_OVERRIDES[normalized_core]
    elif (
        normalized_core in LOWERCASE_TITLE_WORDS
        and word_index != 0
        and word_index != word_count - 1
    ):
        formatted_core = normalized_core
    else:
        formatted_core = core[:1].upper() + core[1:].lower()

    return f"{prefix}{formatted_core}{suffix}"


def normalize_skill_name(value: str) -> str:
    return collapse_spaces(value).lower()


def normalize_certification_name(value: str) -> str:
    normalized = collapse_spaces(value)
    mojibake_dash_variants = (
        "\u00e2\u20ac\u201c",
        "\u00e2\u20ac\u0093",
        "\u00e2\u20ac\u201d",
        "\u00e2\u20ac\u0094",
    )
    for mojibake_dash in mojibake_dash_variants:
        normalized = normalized.replace(mojibake_dash, "-")

    normalized = re.sub(r"[\u2010-\u2015\u2212]", "-", normalized)
    normalized = re.sub(r"\s*-\s*", " - ", normalized)
    normalized = re.sub(r"\s*:\s*", ": ", normalized)
    return collapse_spaces(normalized).casefold()


def split_list(value: str) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()

    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue

        dedupe_key = collapse_spaces(item).lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        items.append(item)

    return items


def split_certifications(value: str) -> list[ParsedCertification]:
    items: list[ParsedCertification] = []
    seen: set[str] = set()

    for raw_item in value.split(","):
        certification_name = raw_item.strip()
        if not certification_name:
            continue

        normalized_certification_name = normalize_certification_name(
            certification_name
        )
        if normalized_certification_name in seen:
            continue

        seen.add(normalized_certification_name)
        items.append(
            ParsedCertification(
                certification_name=certification_name,
                normalized_certification_name=normalized_certification_name,
            )
        )

    return items


def unique_certifications_by_normalized_name(
    roles: Sequence[ParsedRole],
) -> list[ParsedCertification]:
    certifications_by_normalized_name: dict[str, ParsedCertification] = {}
    for role in roles:
        for certification in role.certifications:
            normalized_name = certification.normalized_certification_name
            if normalized_name not in certifications_by_normalized_name:
                certifications_by_normalized_name[normalized_name] = certification
    return list(certifications_by_normalized_name.values())


def chunked(items: Sequence[Any], size: int = BATCH_SIZE) -> Iterable[Sequence[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


def parse_csv(csv_path: Path | str) -> tuple[list[ParsedRole], ParseStats]:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    if not path.is_file():
        raise ValueError(f"CSV path is not a file: {path}")

    stats = ParseStats()
    roles_by_hash: dict[str, ParsedRole] = {}

    csv_text = read_csv_text(path)
    with io.StringIO(csv_text, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row.")

        missing_columns = [
            column for column in REQUIRED_COLUMNS if column not in reader.fieldnames
        ]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"CSV is missing required column(s): {missing}")

        for row in reader:
            stats.rows_read += 1

            raw_job_title = (row.get("Job Title") or "").strip()
            job_description = (row.get("Job Description") or "").strip()
            raw_skills = (row.get("Skills") or "").strip()
            raw_certifications = (row.get("Certifications") or "").strip()

            if not raw_job_title:
                stats.rows_skipped += 1
                continue

            job_title = normalize_job_title(raw_job_title)
            source_row_hash = compute_source_row_hash_from_values(
                job_title,
                job_description,
                raw_skills,
                raw_certifications,
            )
            skill_names = split_list(raw_skills)
            certifications = split_certifications(raw_certifications)
            if source_row_hash in roles_by_hash:
                stats.duplicate_source_rows += 1

            roles_by_hash[source_row_hash] = ParsedRole(
                job_title=job_title,
                job_description=job_description,
                raw_skills=raw_skills,
                raw_certifications=raw_certifications,
                source_row_hash=source_row_hash,
                skills=[
                    ParsedSkill(
                        skill_name=skill_name,
                        normalized_skill_name=normalize_skill_name(skill_name),
                    )
                    for skill_name in skill_names
                ],
                certifications=certifications,
            )

    return list(roles_by_hash.values()), stats


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

    def validate_schema(self) -> None:
        checks = [
            (
                self.schema.roles_table,
                [
                    self.schema.role_id_column,
                    self.schema.job_title_column,
                    self.schema.job_description_column,
                    self.schema.raw_skills_column,
                    self.schema.raw_certifications_column,
                    self.schema.source_row_hash_column,
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
                    self.schema.normalized_certification_name_column,
                    self.schema.embedding_column,
                ],
            ),
            (
                self.schema.certifications_mapping_table,
                [
                    self.schema.role_id_column,
                    self.schema.certification_id_column,
                ],
            ),
        ]

        for table, columns in checks:
            self._request(
                "GET",
                table,
                query=[
                    ("select", ",".join(columns)),
                    ("limit", "1"),
                ],
            )

    def find_role_by_title(self, job_title: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            self.schema.roles_table,
            query=[
                (
                    "select",
                    f"{self.schema.role_id_column},{self.schema.job_title_column}",
                ),
                (self.schema.job_title_column, f"eq.{job_title}"),
                ("limit", "1"),
            ],
        )
        if not rows:
            return None
        return rows[0]

    def list_roles(self) -> list[dict[str, Any]]:
        rows = self._request(
            "GET",
            self.schema.roles_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.role_id_column,
                            self.schema.job_title_column,
                            self.schema.job_description_column,
                            self.schema.raw_skills_column,
                            self.schema.raw_certifications_column,
                            self.schema.source_row_hash_column,
                        ]
                    ),
                ),
            ],
            extra_headers={
                "Range-Unit": "items",
                "Range": "0-9999",
            },
        )
        return rows or []

    def insert_role(self, role: ParsedRole) -> dict[str, Any]:
        rows = self._request(
            "POST",
            self.schema.roles_table,
            payload=self._role_payload(role),
            prefer="return=representation",
        )
        if not rows:
            raise SupabaseError("Supabase inserted a role but returned no row data.")
        return rows[0]

    def insert_roles(self, roles: Sequence[ParsedRole]) -> list[dict[str, Any]]:
        if not roles:
            return []
        rows = self._request(
            "POST",
            self.schema.roles_table,
            payload=[self._role_payload(role) for role in roles],
            prefer="return=representation",
        )
        if len(rows or []) != len(roles):
            raise SupabaseError("Supabase inserted roles but returned an unexpected row count.")
        return rows

    def update_role(self, role_id: Any, role: ParsedRole) -> None:
        self._request(
            "PATCH",
            self.schema.roles_table,
            query=[
                (self.schema.role_id_column, f"eq.{role_id}"),
            ],
            payload=self._role_payload(role),
            prefer="return=minimal",
        )

    def update_role_title(self, role_id: Any, job_title: str) -> None:
        self._request(
            "PATCH",
            self.schema.roles_table,
            query=[
                (self.schema.role_id_column, f"eq.{role_id}"),
            ],
            payload={
                self.schema.job_title_column: job_title,
            },
            prefer="return=minimal",
        )

    def delete_role_skills(self, role_id: Any) -> None:
        self.delete_role_skills_for_roles([role_id])

    def delete_role_skills_for_roles(self, role_ids: Sequence[Any]) -> None:
        for role_id_chunk in chunked(list(role_ids)):
            if not role_id_chunk:
                continue
            role_id_filter = ",".join(str(role_id) for role_id in role_id_chunk)
            self._request(
                "DELETE",
                self.schema.role_skills_table,
                query=[
                    (self.schema.role_id_column, f"in.({role_id_filter})"),
                ],
                prefer="return=minimal",
            )

    def delete_certification_mappings(self, role_id: Any) -> None:
        self.delete_certification_mappings_for_roles([role_id])

    def delete_certification_mappings_for_roles(
        self,
        role_ids: Sequence[Any],
    ) -> None:
        for role_id_chunk in chunked(list(role_ids)):
            if not role_id_chunk:
                continue
            role_id_filter = ",".join(str(role_id) for role_id in role_id_chunk)
            self._request(
                "DELETE",
                self.schema.certifications_mapping_table,
                query=[
                    (self.schema.role_id_column, f"in.({role_id_filter})"),
                ],
                prefer="return=minimal",
            )

    def delete_role_skills_one_at_a_time(self, role_id: Any) -> None:
        self._request(
            "DELETE",
            self.schema.role_skills_table,
            query=[
                (self.schema.role_id_column, f"eq.{role_id}"),
            ],
            prefer="return=minimal",
        )

    def delete_certification_mappings_one_at_a_time(self, role_id: Any) -> None:
        self._request(
            "DELETE",
            self.schema.certifications_mapping_table,
            query=[
                (self.schema.role_id_column, f"eq.{role_id}"),
            ],
            prefer="return=minimal",
        )

    def insert_role_skills(self, rows: Sequence[dict[str, Any]]) -> None:
        if not rows:
            return
        for row_chunk in chunked(list(rows)):
            self._request(
                "POST",
                self.schema.role_skills_table,
                payload=list(row_chunk),
                prefer="return=minimal",
            )

    def upsert_certifications(
        self,
        certifications: Sequence[ParsedCertification],
    ) -> dict[str, Any]:
        if not certifications:
            return {}

        ids_by_normalized_name: dict[str, Any] = {}
        for certification_chunk in chunked(list(certifications)):
            rows = [
                {
                    self.schema.certification_name_column: (
                        certification.certification_name
                    ),
                    self.schema.normalized_certification_name_column: (
                        certification.normalized_certification_name
                    ),
                }
                for certification in certification_chunk
            ]
            response_rows = self._request(
                "POST",
                self.schema.certifications_table,
                query=[
                    (
                        "on_conflict",
                        self.schema.normalized_certification_name_column,
                    ),
                ],
                payload=rows,
                prefer="resolution=merge-duplicates,return=representation",
            )
            for row in response_rows or []:
                normalized_name = str(
                    row.get(self.schema.normalized_certification_name_column)
                    or ""
                )
                certification_id = row.get(self.schema.certification_id_column)
                if normalized_name and certification_id is not None:
                    ids_by_normalized_name[normalized_name] = certification_id

        missing_names = {
            certification.normalized_certification_name
            for certification in certifications
            if certification.normalized_certification_name
            not in ids_by_normalized_name
        }
        if missing_names:
            raise SupabaseError(
                "Supabase upserted certifications but did not return IDs for: "
                + ", ".join(sorted(missing_names))
            )
        return ids_by_normalized_name

    def insert_certification_mappings(self, rows: Sequence[dict[str, Any]]) -> None:
        if not rows:
            return
        for row_chunk in chunked(list(rows)):
            self._request(
                "POST",
                self.schema.certifications_mapping_table,
                payload=list(row_chunk),
                prefer="return=minimal",
            )

    def _role_payload(self, role: ParsedRole) -> dict[str, Any]:
        return {
            self.schema.job_title_column: role.job_title,
            self.schema.job_description_column: role.job_description,
            self.schema.raw_skills_column: role.raw_skills,
            self.schema.raw_certifications_column: role.raw_certifications,
            self.schema.source_row_hash_column: role.source_row_hash
            or compute_source_row_hash(role),
        }

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
            "User-Agent": "career-compass-importer/1.0",
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


def import_roles(roles: Sequence[ParsedRole], client: Any) -> ImportStats:
    stats = ImportStats()
    schema = getattr(client, "schema", DEFAULT_SCHEMA)
    roles = [role_with_source_row_hash(role) for role in roles]
    existing_by_hash: dict[str, dict[str, Any]] = {}
    for row in sorted(
        client.list_roles(),
        key=lambda role_row: role_row.get(schema.role_id_column) or 0,
    ):
        source_row_hash = source_row_hash_for_row(row, schema)
        if not source_row_hash:
            continue
        existing_by_hash.setdefault(source_row_hash, row)

    missing_roles = [
        role
        for role in roles
        if role.source_row_hash not in existing_by_hash
    ]
    inserted_rows = client.insert_roles(missing_roles)
    for role, inserted_row in zip(missing_roles, inserted_rows):
        existing_by_hash[role.source_row_hash] = inserted_row
        stats.roles_inserted += 1

    missing_role_hashes = {
        missing_role.source_row_hash
        for missing_role in missing_roles
    }
    role_ids_by_hash: dict[str, Any] = {}
    for role in roles:
        existing_row = existing_by_hash[role.source_row_hash]
        role_id = existing_row[schema.role_id_column]
        role_ids_by_hash[role.source_row_hash] = role_id

        if role.source_row_hash not in missing_role_hashes:
            stats.roles_reused_or_updated += 1
            if role_payload_differs(existing_row, role, schema):
                client.update_role(role_id, role)

    role_ids = list(role_ids_by_hash.values())
    client.delete_role_skills_for_roles(role_ids)
    client.delete_certification_mappings_for_roles(role_ids)

    skill_rows = [
        {
            schema.role_id_column: role_ids_by_hash[role.source_row_hash],
            schema.skill_name_column: skill.skill_name,
            schema.normalized_skill_name_column: skill.normalized_skill_name,
        }
        for role in roles
        for skill in role.skills
    ]
    certification_ids_by_normalized_name = client.upsert_certifications(
        unique_certifications_by_normalized_name(roles)
    )
    certification_mapping_rows = [
        {
            schema.role_id_column: role_ids_by_hash[role.source_row_hash],
            schema.certification_id_column: certification_ids_by_normalized_name[
                certification.normalized_certification_name
            ],
        }
        for role in roles
        for certification in role.certifications
    ]

    client.insert_role_skills(skill_rows)
    client.insert_certification_mappings(certification_mapping_rows)
    stats.skills_inserted += len(skill_rows)
    stats.certifications_inserted += len(certification_mapping_rows)

    return stats


def role_payload_differs(
    existing_row: dict[str, Any],
    role: ParsedRole,
    schema: SchemaConfig,
) -> bool:
    expected = {
        schema.job_title_column: role.job_title,
        schema.job_description_column: role.job_description,
        schema.raw_skills_column: role.raw_skills,
        schema.raw_certifications_column: role.raw_certifications,
        schema.source_row_hash_column: role.source_row_hash
        or compute_source_row_hash(role),
    }
    for column, value in expected.items():
        if (existing_row.get(column) or "") != value:
            return True
    return False


def normalize_existing_role_titles(client: Any) -> ExistingTitleCleanupStats:
    stats = ExistingTitleCleanupStats()
    schema = getattr(client, "schema", DEFAULT_SCHEMA)

    for row in client.list_roles():
        role_id = row.get(schema.role_id_column)
        old_title = row.get(schema.job_title_column)
        if role_id is None or not old_title:
            continue

        stats.roles_checked += 1
        normalized_title = normalize_job_title(str(old_title))
        if normalized_title != old_title:
            client.update_role_title(role_id, normalized_title)
            stats.titles_normalized += 1

    return stats


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
        joined = ", ".join(missing)
        raise ValueError(f"Missing required environment variable(s): {joined}")
    if service_role_key.startswith("sb_publishable_"):
        raise ValueError(
            "SUPABASE_SERVICE_ROLE_KEY must be a secret key "
            "(sb_secret_...) or legacy service_role JWT, not a publishable key."
        )

    return supabase_url, service_role_key


def print_dry_run_preview(roles: Sequence[ParsedRole], sample_limit: int = 5) -> None:
    print("Dry run only. No database writes will be made.")
    print(f"Roles that would be imported: {len(roles)}")
    print(f"Skills that would be inserted: {sum(len(role.skills) for role in roles)}")
    print(
        "Certifications that would be inserted: "
        f"{sum(len(role.certifications) for role in roles)}"
    )

    if not roles:
        return

    print(f"Sample roles, first {min(sample_limit, len(roles))}:")
    for role in roles[:sample_limit]:
        print(
            f"- {role.job_title}: "
            f"{len(role.skills)} skill(s), "
            f"{len(role.certifications)} certification(s)"
        )


def print_summary(parse_stats: ParseStats, import_stats: ImportStats | None) -> None:
    print(f"CSV rows read: {parse_stats.rows_read}")
    print(f"Rows skipped: {parse_stats.rows_skipped}")
    print(f"Duplicate source rows collapsed: {parse_stats.duplicate_source_rows}")

    if import_stats is None:
        return

    print(f"Roles inserted: {import_stats.roles_inserted}")
    print(f"Roles updated/reused: {import_stats.roles_reused_or_updated}")
    print(f"Skills inserted: {import_stats.skills_inserted}")
    print(f"Certifications inserted: {import_stats.certifications_inserted}")


def print_title_cleanup_summary(stats: ExistingTitleCleanupStats) -> None:
    print(f"Existing roles checked: {stats.roles_checked}")
    print(f"Existing role titles normalized: {stats.titles_normalized}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database population: import Kaggle IT job roles into "
            "Supabase career tables."
        ),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Path to the Kaggle CSV with Job Title, Job Description, Skills, Certifications.",
    )
    parser.add_argument(
        "--normalize-existing-titles",
        action="store_true",
        help="Normalize existing career_roles.job_title values without reimporting.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and summarize the CSV without modifying Supabase.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if not args.csv and not args.normalize_existing_titles:
        parser.error("--csv is required unless --normalize-existing-titles is used.")
    if args.dry_run and not args.csv:
        parser.error("--dry-run requires --csv.")

    try:
        roles: list[ParsedRole] | None = None
        parse_stats: ParseStats | None = None
        if args.csv:
            roles, parse_stats = parse_csv(args.csv)

        if args.dry_run:
            assert roles is not None
            assert parse_stats is not None
            print_summary(parse_stats, None)
            print_dry_run_preview(roles)
            return 0

        supabase_url, service_role_key = get_required_env()
        client = SupabaseRestClient(supabase_url, service_role_key)
        client.validate_schema()

        if args.normalize_existing_titles:
            cleanup_stats = normalize_existing_role_titles(client)
            print_title_cleanup_summary(cleanup_stats)
            if roles is None:
                return 0

        assert roles is not None
        assert parse_stats is not None
        import_stats = import_roles(roles, client)
        print_summary(parse_stats, import_stats)
        return 0
    except (FileNotFoundError, ValueError, SupabaseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
