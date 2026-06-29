"""
Rebuild split career_roles embeddings with bge-base-en-v1.5.

Pipeline:
  career_roles + role_skills + certifications_mapping
  -> deterministic capability/intent texts
  -> encode_documents()
  -> batch UPDATE capability_embedding / intent_embedding and their text fields.

Run:
    python -m backend.scripts.role_embeddings
    python -m backend.scripts.role_embeddings --dry-run
    python -m backend.scripts.role_embeddings --limit 20

Role texts are DOCUMENTS, so we use encode_documents() with no query prefix.
User profile texts remain per-request QUERIES in the matching service.
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values

from backend.app.core.database import db_pool, get_db_connection
from backend.app.features.role_matching.embedder import EMBEDDING_DIM, get_embedder

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CareerCompass.DataPreprocessing")

MAX_DESC_CHARS = 1200
MAX_INTENT_DESC_CHARS = 700
DB_UPDATE_PAGE = 100


def _clean_text(value: Optional[str]) -> str:
    return " ".join((value or "").split())


def _first_non_empty(*values: Optional[str]) -> str:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _truncate(value: Optional[str], max_chars: int) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rsplit(" ", 1)[0] + " ..."


def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


def build_capability_embedding_text(
    *,
    title: Optional[str],
    description: Optional[str],
    normalized_skills: Optional[str],
    raw_skills: Optional[str],
    certifications: Optional[str],
    raw_certifications: Optional[str],
) -> str:
    """Role-side evidence comparable to a user's capability profile."""
    parts = [f"Job title: {_clean_text(title)}"]

    skills = _first_non_empty(normalized_skills, raw_skills)
    if skills:
        parts.append(f"Required skills: {skills}")

    certs = _first_non_empty(certifications, raw_certifications)
    if certs:
        parts.append(f"Certifications: {certs}")

    responsibilities = _truncate(description, MAX_DESC_CHARS)
    if responsibilities:
        parts.append(f"Responsibilities: {responsibilities}")

    return "\n".join(parts).strip()


def build_intent_embedding_text(
    *,
    title: Optional[str],
    description: Optional[str],
    domain_tags: Optional[str],
) -> str:
    """Role-side evidence comparable to a user's identity/interests profile."""
    parts = [f"Career direction: {_clean_text(title)}"]

    domains = _clean_text(domain_tags)
    if domains:
        parts.append(f"Domain tags: {domains}")

    context = _truncate(description, MAX_INTENT_DESC_CHARS)
    if context:
        parts.append(f"Role context: {context}")

    return "\n".join(parts).strip()


def ensure_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS capability_embedding vector({EMBEDDING_DIM});"
        )
        cur.execute(
            f"ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS intent_embedding vector({EMBEDDING_DIM});"
        )
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS capability_embedding_text text;")
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS intent_embedding_text text;")
        cur.execute("ALTER TABLE career_roles DROP COLUMN IF EXISTS embedding;")
        cur.execute("ALTER TABLE career_roles DROP COLUMN IF EXISTS embedding_text;")
        cur.execute("ALTER TABLE certifications DROP COLUMN IF EXISTS embedding;")
    conn.commit()
    _assert_vector_dims(conn)


def _assert_vector_dims(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.attname, a.atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = 'career_roles'
              AND a.attname IN ('capability_embedding', 'intent_embedding')
              AND NOT a.attisdropped;
            """
        )
        dims = dict(cur.fetchall())

    for column in ("capability_embedding", "intent_embedding"):
        if column not in dims:
            raise RuntimeError(f"career_roles.{column} missing after ensure_schema().")
        dim = dims[column]
        if dim not in (EMBEDDING_DIM, -1):
            raise RuntimeError(
                f"career_roles.{column} is vector({dim}) but the model outputs {EMBEDDING_DIM}. "
                f"Fix it first: ALTER TABLE career_roles ALTER COLUMN {column} TYPE vector({EMBEDDING_DIM});"
            )


def fetch_roles(conn: psycopg2.extensions.connection, limit: Optional[int] = None) -> list[tuple]:
    sql = """
        WITH normalized_role_skills AS (
            SELECT
                role_id,
                string_agg(DISTINCT normalized_skill_name, ', ' ORDER BY normalized_skill_name) AS normalized_skills
            FROM role_skills
            WHERE normalized_skill_name IS NOT NULL
              AND btrim(normalized_skill_name) <> ''
            GROUP BY role_id
        ),
        mapped_certifications AS (
            SELECT
                cm.role_id,
                string_agg(
                    DISTINCT COALESCE(c.certification_name, c.normalized_certification_name),
                    ', '
                    ORDER BY COALESCE(c.certification_name, c.normalized_certification_name)
                ) AS certifications
            FROM certifications_mapping cm
            JOIN certifications c ON c.certification_id = cm.certification_id
            WHERE COALESCE(c.certification_name, c.normalized_certification_name) IS NOT NULL
              AND btrim(COALESCE(c.certification_name, c.normalized_certification_name)) <> ''
            GROUP BY cm.role_id
        )
        SELECT
            c.role_id,
            c.job_title,
            c.job_description,
            nrs.normalized_skills,
            c.raw_skills,
            mc.certifications,
            c.raw_certifications,
            c.domain_tags
        FROM career_roles c
        LEFT JOIN normalized_role_skills nrs ON nrs.role_id = c.role_id
        LEFT JOIN mapped_certifications mc ON mc.role_id = c.role_id
        ORDER BY c.role_id
    """
    params: tuple = ()
    if limit:
        sql += " LIMIT %s"
        params = (limit,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def store_role_embeddings(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    if not rows:
        return
    sql = """
        UPDATE career_roles AS c
        SET capability_embedding = v.capability_embedding::vector,
            intent_embedding = v.intent_embedding::vector,
            capability_embedding_text = v.capability_embedding_text,
            intent_embedding_text = v.intent_embedding_text
        FROM (VALUES %s) AS v(
            role_id,
            capability_embedding,
            intent_embedding,
            capability_embedding_text,
            intent_embedding_text
        )
        WHERE c.role_id = v.role_id::bigint
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template="(%s, %s, %s, %s, %s)", page_size=DB_UPDATE_PAGE)
    conn.commit()


def rebuild(limit: Optional[int] = None, dry_run: bool = False) -> None:
    with get_db_connection() as conn:
        if not dry_run:
            ensure_schema(conn)

        roles = fetch_roles(conn, limit)
        logger.info("Fetched %d roles.", len(roles))

        ids: list[int] = []
        capability_texts: list[str] = []
        intent_texts: list[str] = []
        for (
            role_id,
            title,
            desc,
            normalized_skills,
            raw_skills,
            certifications,
            raw_certifications,
            domain_tags,
        ) in roles:
            ids.append(role_id)
            capability_texts.append(
                build_capability_embedding_text(
                    title=title,
                    description=desc,
                    normalized_skills=normalized_skills,
                    raw_skills=raw_skills,
                    certifications=certifications,
                    raw_certifications=raw_certifications,
                )
            )
            intent_texts.append(
                build_intent_embedding_text(
                    title=title,
                    description=desc,
                    domain_tags=domain_tags,
                )
            )

        if dry_run:
            for i in range(min(3, len(ids))):
                logger.info(
                    "role_id=%s\n[Capability]\n%s\n\n[Intent]\n%s\n----------",
                    ids[i],
                    capability_texts[i],
                    intent_texts[i],
                )
            logger.info("Dry run: %d roles would be embedded. No writes performed.", len(ids))
            return

        logger.info("Encoding %d capability role documents (no query prefix) ...", len(capability_texts))
        capability_vectors = get_embedder().encode_documents(capability_texts)
        logger.info("Encoding %d intent role documents (no query prefix) ...", len(intent_texts))
        intent_vectors = get_embedder().encode_documents(intent_texts)

        rows = [
            (rid, _vec_literal(cap_vec), _vec_literal(intent_vec), cap_text, intent_text)
            for rid, cap_vec, intent_vec, cap_text, intent_text in zip(
                ids,
                capability_vectors,
                intent_vectors,
                capability_texts,
                intent_texts,
            )
        ]
        store_role_embeddings(conn, rows)
        logger.info("Done. Wrote split embeddings + text fields for %d roles.", len(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild split career_roles embeddings with bge-base-en-v1.5.")
    parser.add_argument("--dry-run", action="store_true", help="Print sample split embedding texts and exit; no writes.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N roles.")
    args = parser.parse_args()
    try:
        rebuild(limit=args.limit, dry_run=args.dry_run)
    finally:
        if db_pool is not None:
            db_pool.closeall()


if __name__ == "__main__":
    main()
