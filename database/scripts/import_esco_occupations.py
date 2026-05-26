#!/usr/bin/env python3
"""Import filtered ICT-related ESCO occupations into Supabase.

One-time database population script. Kept for auditability and controlled
reruns while rebuilding the seeded Career Compass database; not app runtime
code. Prefer --dry-run before any write-mode rerun.

Place the raw official ESCO English occupations CSV somewhere local, for example:

    data/raw/esco/occupations_en.csv

The CSV does not need to be manually filtered first. This script detects common
official ESCO header styles, filters ICT-related occupations by ISCO code, and
imports only rows for `esco_occupations`.

Examples:

    python scripts/import_esco_occupations.py --csv data/raw/esco/occupations_en.csv --dry-run
    python scripts/import_esco_occupations.py --csv data/raw/esco/occupations_en.csv
    python scripts/import_esco_occupations.py --csv data/raw/esco/occupations_en.csv --force
    python scripts/import_esco_occupations.py --csv data/raw/esco/occupations_en.csv --include-adjacent-ict

For a real import, set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your local
shell environment or in a local .env file. Never expose the service role key in
frontend/client code.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


DEFAULT_ICT_ISCO_PREFIXES = ("133", "25", "35")
ADJACENT_ICT_ISCO_PREFIXES = ("2152", "2153", "2166", "2356", "2434", "3114", "742")
BATCH_SIZE = 500
DEFAULT_REVIEW_OUTPUT = Path("data/esco_occupations_import_review.csv")


COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "esco_uri": ("Concept URI", "conceptUri"),
    "concept_type": ("Concept type", "conceptType"),
    "isco_code": ("ISCO code", "iscoGroup"),
    "name": ("Concept PT", "preferredLabel", "name"),
    "definition": ("Definition", "definition", "description", "scopeNote"),
}


@dataclass(frozen=True)
class SchemaConfig:
    occupations_table: str = "esco_occupations"
    esco_uri_column: str = "esco_uri"
    isco_code_column: str = "isco_code"
    name_column: str = "name"
    definition_column: str = "definition"


DEFAULT_SCHEMA = SchemaConfig()


@dataclass(frozen=True)
class ColumnMapping:
    esco_uri: str | None
    concept_type: str | None
    isco_code: str | None
    name: str | None
    definition: str | None


@dataclass(frozen=True)
class EscoOccupation:
    esco_uri: str
    isco_code: str
    name: str
    definition: str

    def to_payload(self, schema: SchemaConfig = DEFAULT_SCHEMA) -> dict[str, Any]:
        return {
            schema.esco_uri_column: self.esco_uri,
            schema.isco_code_column: self.isco_code,
            schema.name_column: self.name,
            schema.definition_column: self.definition,
        }


@dataclass(frozen=True)
class ReviewRow:
    source_row_number: int
    esco_uri: str
    concept_type: str | None
    isco_code: str
    name: str
    included: bool
    skip_reason: str


@dataclass
class ParseStats:
    rows_read: int = 0
    rows_skipped_missing_required: int = 0
    rows_skipped_non_occupation: int = 0
    rows_skipped_outside_isco_filter: int = 0
    rows_included: int = 0

    @property
    def rows_skipped(self) -> int:
        return (
            self.rows_skipped_missing_required
            + self.rows_skipped_non_occupation
            + self.rows_skipped_outside_isco_filter
        )


@dataclass(frozen=True)
class ParseResult:
    occupations: list[EscoOccupation]
    review_rows: list[ReviewRow]
    stats: ParseStats
    detected_columns: list[str]
    detected_mapping: ColumnMapping
    allowed_isco_prefixes: tuple[str, ...]
    concept_type_missing: bool


@dataclass
class ImportStats:
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_reused: int = 0


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


def detect_definition_columns(fieldnames: Sequence[str]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for alias in COLUMN_ALIASES["definition"]:
        column = detect_column(fieldnames, (alias,))
        if column is None:
            continue

        normalized = normalize_column_name(column)
        if normalized in seen:
            continue

        seen.add(normalized)
        columns.append(column)
    return columns


def detect_columns(fieldnames: Sequence[str]) -> ColumnMapping:
    definition_columns = detect_definition_columns(fieldnames)
    return ColumnMapping(
        esco_uri=detect_column(fieldnames, COLUMN_ALIASES["esco_uri"]),
        concept_type=detect_column(fieldnames, COLUMN_ALIASES["concept_type"]),
        isco_code=detect_column(fieldnames, COLUMN_ALIASES["isco_code"]),
        name=detect_column(fieldnames, COLUMN_ALIASES["name"]),
        definition=", ".join(definition_columns) if definition_columns else None,
    )


def require_detected_columns(mapping: ColumnMapping) -> None:
    missing = []
    if mapping.esco_uri is None:
        missing.append("Concept URI or conceptUri")
    if mapping.name is None:
        missing.append("Concept PT, preferredLabel, or name")
    if mapping.isco_code is None:
        missing.append("ISCO code or iscoGroup")

    if missing:
        raise ValueError("CSV is missing required column(s): " + ", ".join(missing))


def clean_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        key: "" if value is None else str(value).strip()
        for key, value in row.items()
        if key is not None
    }


def get_optional(row: dict[str, str], column: str | None) -> str:
    if column is None:
        return ""
    return row.get(column, "").strip()


def get_nullable(row: dict[str, str], column: str | None) -> str | None:
    value = get_optional(row, column)
    return value or None


def get_definition(row: dict[str, str], fieldnames: Sequence[str]) -> str:
    for column in detect_definition_columns(fieldnames):
        value = get_optional(row, column)
        if value:
            return value
    return ""


def is_occupation_concept_type(value: str) -> bool:
    normalized = normalize_column_name(value)
    return normalized in {"oc", "occupation"}


def build_allowed_isco_prefixes(include_adjacent_ict: bool) -> tuple[str, ...]:
    if not include_adjacent_ict:
        return DEFAULT_ICT_ISCO_PREFIXES
    return DEFAULT_ICT_ISCO_PREFIXES + ADJACENT_ICT_ISCO_PREFIXES


def is_allowed_isco_code(isco_code: str, allowed_prefixes: Sequence[str]) -> bool:
    return any(isco_code.startswith(prefix) for prefix in allowed_prefixes)


def missing_required_reason(esco_uri: str, name: str, isco_code: str) -> str:
    if not esco_uri:
        return "missing_esco_uri"
    if not name:
        return "missing_name"
    if not isco_code:
        return "missing_isco_code"
    return ""


def parse_occupations_csv(
    csv_path: Path | str,
    include_adjacent_ict: bool = False,
) -> ParseResult:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    if not path.is_file():
        raise ValueError(f"CSV path is not a file: {path}")

    stats = ParseStats()
    occupations: list[EscoOccupation] = []
    review_rows: list[ReviewRow] = []
    allowed_prefixes = build_allowed_isco_prefixes(include_adjacent_ict)

    csv_text = read_csv_text(path)
    with io.StringIO(csv_text, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row.")

        fieldnames = list(reader.fieldnames)
        mapping = detect_columns(fieldnames)
        require_detected_columns(mapping)
        concept_type_missing = mapping.concept_type is None

        for row_index, raw_row in enumerate(reader, start=2):
            stats.rows_read += 1
            row = clean_row(raw_row)

            esco_uri = get_optional(row, mapping.esco_uri)
            concept_type = get_nullable(row, mapping.concept_type)
            isco_code = get_optional(row, mapping.isco_code)
            name = get_optional(row, mapping.name)

            skip_reason = missing_required_reason(esco_uri, name, isco_code)
            if skip_reason:
                stats.rows_skipped_missing_required += 1
                review_rows.append(
                    ReviewRow(
                        source_row_number=row_index,
                        esco_uri=esco_uri,
                        concept_type=concept_type,
                        isco_code=isco_code,
                        name=name,
                        included=False,
                        skip_reason=skip_reason,
                    )
                )
                continue

            if (
                mapping.concept_type is not None
                and not is_occupation_concept_type(concept_type or "")
            ):
                stats.rows_skipped_non_occupation += 1
                review_rows.append(
                    ReviewRow(
                        source_row_number=row_index,
                        esco_uri=esco_uri,
                        concept_type=concept_type,
                        isco_code=isco_code,
                        name=name,
                        included=False,
                        skip_reason="concept_type_not_occupation",
                    )
                )
                continue

            if not is_allowed_isco_code(isco_code, allowed_prefixes):
                stats.rows_skipped_outside_isco_filter += 1
                review_rows.append(
                    ReviewRow(
                        source_row_number=row_index,
                        esco_uri=esco_uri,
                        concept_type=concept_type,
                        isco_code=isco_code,
                        name=name,
                        included=False,
                        skip_reason="isco_code_outside_allowed_prefixes",
                    )
                )
                continue

            occupation = EscoOccupation(
                esco_uri=esco_uri,
                isco_code=isco_code,
                name=name,
                definition=get_definition(row, fieldnames),
            )
            occupations.append(occupation)
            stats.rows_included += 1
            review_rows.append(
                ReviewRow(
                    source_row_number=row_index,
                    esco_uri=esco_uri,
                    concept_type=concept_type,
                    isco_code=isco_code,
                    name=name,
                    included=True,
                    skip_reason="",
                )
            )

    return ParseResult(
        occupations=occupations,
        review_rows=review_rows,
        stats=stats,
        detected_columns=fieldnames,
        detected_mapping=mapping,
        allowed_isco_prefixes=allowed_prefixes,
        concept_type_missing=concept_type_missing,
    )


def write_review_csv(path: Path | str, review_rows: Sequence[ReviewRow]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_row_number",
                "esco_uri",
                "concept_type",
                "isco_code",
                "name",
                "included",
                "skip_reason",
            ],
        )
        writer.writeheader()
        for row in review_rows:
            writer.writerow(
                {
                    "source_row_number": row.source_row_number,
                    "esco_uri": row.esco_uri,
                    "concept_type": row.concept_type or "",
                    "isco_code": row.isco_code,
                    "name": row.name,
                    "included": "true" if row.included else "false",
                    "skip_reason": row.skip_reason,
                }
            )


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

    def validate_schema(self) -> None:
        self._request(
            "GET",
            self.schema.occupations_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.esco_uri_column,
                            self.schema.isco_code_column,
                            self.schema.name_column,
                            self.schema.definition_column,
                        ]
                    ),
                ),
                ("limit", "1"),
            ],
        )

    def find_occupation_by_uri(self, esco_uri: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            self.schema.occupations_table,
            query=[
                (
                    "select",
                    ",".join(
                        [
                            self.schema.esco_uri_column,
                            self.schema.isco_code_column,
                            self.schema.name_column,
                            self.schema.definition_column,
                        ]
                    ),
                ),
                (self.schema.esco_uri_column, f"eq.{esco_uri}"),
                ("limit", "1"),
            ],
        )
        if not rows:
            return None
        return rows[0]

    def insert_occupation(self, occupation: EscoOccupation) -> None:
        self._request(
            "POST",
            self.schema.occupations_table,
            payload=occupation.to_payload(self.schema),
            prefer="return=minimal",
        )

    def update_occupation(self, occupation: EscoOccupation) -> None:
        self._request(
            "PATCH",
            self.schema.occupations_table,
            query=[
                (self.schema.esco_uri_column, f"eq.{occupation.esco_uri}"),
            ],
            payload=occupation.to_payload(self.schema),
            prefer="return=minimal",
        )

    def _request(
        self,
        method: str,
        table: str,
        query: Iterable[tuple[str, str]] | None = None,
        payload: Any | None = None,
        prefer: str | None = None,
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
            "User-Agent": "career-compass-esco-importer/1.0",
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


def import_occupations(
    occupations: Sequence[EscoOccupation],
    client: Any,
    force: bool = False,
) -> ImportStats:
    stats = ImportStats()

    for occupation in occupations:
        existing_row = client.find_occupation_by_uri(occupation.esco_uri)
        if existing_row is None:
            client.insert_occupation(occupation)
            stats.rows_inserted += 1
        elif force:
            client.update_occupation(occupation)
            stats.rows_updated += 1
        else:
            stats.rows_reused += 1

    return stats


def print_summary(
    csv_path: Path,
    parse_result: ParseResult,
    review_output: Path,
    import_stats: ImportStats | None,
    dry_run: bool,
    force: bool,
    include_adjacent_ict: bool,
) -> None:
    print(f"Input CSV path: {csv_path}")
    print("Detected CSV columns: " + ", ".join(parse_result.detected_columns))
    print("Detected column mapping:")
    for field, column in parse_result.detected_mapping.__dict__.items():
        print(f"  {field}: {column or '(not present)'}")

    print(f"Dry run: {'yes' if dry_run else 'no'}")
    print(f"Force updates: {'yes' if force else 'no'}")
    print(
        "Adjacent ICT codes included: "
        f"{'yes' if include_adjacent_ict else 'no'}"
    )
    print("Allowed ISCO prefixes: " + ", ".join(parse_result.allowed_isco_prefixes))
    if parse_result.concept_type_missing:
        print(
            "Concept type column not present; assuming the CSV contains occupations "
            "and applying ISCO filtering."
        )

    print(f"Total rows read: {parse_result.stats.rows_read}")
    print(
        "Rows skipped because required fields were missing: "
        f"{parse_result.stats.rows_skipped_missing_required}"
    )
    print(
        "Rows skipped because concept type was not occupation: "
        f"{parse_result.stats.rows_skipped_non_occupation}"
    )
    print(
        "Rows skipped because ISCO code was outside allowed ICT prefixes: "
        f"{parse_result.stats.rows_skipped_outside_isco_filter}"
    )
    print(f"Rows included: {parse_result.stats.rows_included}")
    print(f"Review CSV: {review_output}")

    if import_stats is None:
        print("Rows inserted: 0")
        print("Rows updated/reused: 0")
        return

    print(f"Rows inserted: {import_stats.rows_inserted}")
    print(f"Rows updated: {import_stats.rows_updated}")
    print(f"Rows reused: {import_stats.rows_reused}")
    print(f"Rows updated/reused: {import_stats.rows_updated + import_stats.rows_reused}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "One-time database population: import filtered ICT-related ESCO "
            "occupations into Supabase."
        ),
    )
    parser.add_argument(
        "--csv",
        type=Path,
        required=True,
        help="Path to the raw official ESCO occupations_en.csv file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse, filter, and write review output without modifying Supabase.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Update existing esco_occupations rows instead of only reusing them.",
    )
    parser.add_argument(
        "--review-output",
        type=Path,
        default=DEFAULT_REVIEW_OUTPUT,
        help=(
            "Path for the review CSV. Defaults to "
            "data/esco_occupations_import_review.csv."
        ),
    )
    parser.add_argument(
        "--include-adjacent-ict",
        action="store_true",
        help=(
            "Also include adjacent ICT ISCO prefixes/codes: "
            + ", ".join(ADJACENT_ICT_ISCO_PREFIXES)
            + "."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    try:
        parse_result = parse_occupations_csv(
            args.csv,
            include_adjacent_ict=args.include_adjacent_ict,
        )
        write_review_csv(args.review_output, parse_result.review_rows)

        import_stats: ImportStats | None = None
        if not args.dry_run:
            supabase_url, service_role_key = get_required_env()
            client = SupabaseRestClient(supabase_url, service_role_key)
            client.validate_schema()
            import_stats = import_occupations(
                parse_result.occupations,
                client,
                force=args.force,
            )

        print_summary(
            csv_path=args.csv,
            parse_result=parse_result,
            review_output=args.review_output,
            import_stats=import_stats,
            dry_run=args.dry_run,
            force=args.force,
            include_adjacent_ict=args.include_adjacent_ict,
        )
        return 0
    except (FileNotFoundError, ValueError, SupabaseError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
