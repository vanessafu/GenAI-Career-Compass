"""
Rebuild career_roles embeddings with bge-base-en-v1.5.

Pipeline:  read career_roles (+ role_skills) -> build a deterministic
canonical_text -> encode_documents() -> batch UPDATE into pgvector.

Run:
    python backend/scripts/role_embeddings.py          # full rebuild
    python backend/scripts/role_embeddings.py --dry-run  # print sample texts, no writes
    python backend/scripts/role_embeddings.py --limit 20 # test on 20 roles
    python backend/scripts/role_embeddings.py --only-certification # embed certifications for further gap analysis

NOTE: role descriptions are DOCUMENTS, so we use encode_documents() (no query
prefix). After this runs, the 493 role vectors live in bge's space; do NOT mix
them with any leftover careerbert vectors.
"""
from __future__ import annotations

import argparse
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

from backend.app.core.database import db_pool, get_db_connection
from backend.app.features.role_matching.embedder import get_embedder, EMBEDDING_DIM

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CareerCompass.DataPreprocessing")

# Soft cap on the description so the 512-token model doesn't truncate skills away
# (title + skills are placed first; description is the lowest-signal, longest field).
MAX_DESC_CHARS = 1200
DB_UPDATE_PAGE = 100  # rows per execute_values batch


#schema management
def ensure_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM});")
        cur.execute("ALTER TABLE career_roles ADD COLUMN IF NOT EXISTS embedding_text text;")
    conn.commit()
    _assert_vector_dim(conn)


def ensure_cert_schema(conn: psycopg2.extensions.connection) -> None:
    with conn.cursor() as cur:
        cur.execute(f"ALTER TABLE role_certifications ADD COLUMN IF NOT EXISTS embedding vector({EMBEDDING_DIM});")
    conn.commit()


def _assert_vector_dim(conn: psycopg2.extensions.connection) -> None:
    """Guard against an existing embedding column with the wrong dimension (e.g. 1536)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT a.atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname = 'career_roles'
              AND a.attname = 'embedding'
              AND NOT a.attisdropped;
            """
        )
        row = cur.fetchone()
    if not row:
        raise RuntimeError("embedding column missing after ensure_schema().")
    dim = row[0]  # pgvector stores the dimension in atttypmod; -1 means unspecified
    if dim not in (EMBEDDING_DIM, -1):
        raise RuntimeError(
            f"career_roles.embedding is vector({dim}) but the model outputs {EMBEDDING_DIM}. "
            f"Fix it first:  ALTER TABLE career_roles ALTER COLUMN embedding TYPE vector({EMBEDDING_DIM});"
        )


# load roles from the database, joining skills from role_skills. 
def fetch_roles(conn: psycopg2.extensions.connection, limit: Optional[int] = None) -> list[tuple]:
    """
    array_agg(DISTINCT ...) dedups at the SQL level.
    """
    sql = """
        SELECT
            c.role_id,
            c.job_title,
            c.job_description,
            c.raw_skills,
            c.domain_tags
            c.certification_tags
        FROM career_roles c
        GROUP BY c.role_id, c.job_title, c.job_description, c.raw_skills, c.domain_tags
        ORDER BY c.role_id
    """
    params: tuple = ()
    if limit:
        sql += " LIMIT %s"
        params = (limit,)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()

def build_canonical_text(
    title: Optional[str],
    description: Optional[str],
    skills: Optional[str],
    domain_tags: Optional[str],
) -> str:
    """Deterministic text fed to the embedder. Title + skills go first so they
    survive the model's 512-token truncation; the long description goes last."""
    parts = [f"Job title: {(title or '').strip()}"]
    parts.append("Key skills: " +skills)
    parts.append("Domain: " +domain_tags)
    desc = (description or "").strip()
    if len(desc) > MAX_DESC_CHARS:
        desc = desc[:MAX_DESC_CHARS].rsplit(" ", 1)[0] + " …"
    if desc:
        parts.append("Description: " + desc)
    return "\n".join(parts)

# build certification embeddings
def build_certification_embedding(
    conn: psycopg2.extensions.connection,
) -> list[tuple]:
    """Returns list of (id, vec_literal) ready for batch UPDATE into role_certifications."""
    sql = """
        SELECT role_id, normalized_certification_name
        FROM role_certifications
    """
    rows_out: list[tuple] = []
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
        embedder = get_embedder()
        for cert_id, raw_cert in rows:
            text = "Certification: " + (raw_cert or "").strip()
            vec = embedder.encode_query(text)
            rows_out.append((cert_id, _vec_literal(vec)))
    return rows_out


def store_cert_embeddings(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    """Batch UPDATE role_certifications.embedding (no embedding_text stored)."""
    if not rows:
        return
    sql = """
        UPDATE role_certifications AS rc
        SET embedding = v.embedding::vector
        FROM (VALUES %s) AS v(id, embedding)
        WHERE rc.role_id = v.id::bigint
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template="(%s, %s)", page_size=DB_UPDATE_PAGE)
    conn.commit()


# write embeddings back to the database in batches
def _vec_literal(vec: list[float]) -> str:
    return "[" + ",".join(map(str, vec)) + "]"


def store_role_embeddings(conn: psycopg2.extensions.connection, rows: list[tuple]) -> None:
    """Batch UPDATE existing rows by role_id (career_roles already holds every role)."""
    if not rows:
        return
    sql = """
        UPDATE career_roles AS c
        SET embedding = v.embedding::vector,
            embedding_text = v.embedding_text
        FROM (VALUES %s) AS v(role_id, embedding, embedding_text)
        WHERE c.role_id = v.role_id::bigint
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows, template="(%s, %s, %s)", page_size=DB_UPDATE_PAGE)
    conn.commit()


# orchestration 
def rebuild(limit: Optional[int] = None, dry_run: bool = False, only_certification: bool = False) -> None:
    with get_db_connection() as conn:
        if not dry_run:
            ensure_schema(conn)
        
        if only_certification:
            logger.info("Building certification embeddings only...")
            ensure_cert_schema(conn)
            cert_rows = build_certification_embedding(conn)
            store_cert_embeddings(conn, cert_rows)
            logger.info("Stored %d certification embeddings into role_certifications.", len(cert_rows))
            return
        roles = fetch_roles(conn, limit)
        logger.info("Fetched %d roles.", len(roles))

        ids: list[int] = []
        texts: list[str] = []
        for role_id, title, desc, raw_skills, domain_tags in roles:
            ids.append(role_id)
            texts.append(build_canonical_text(title, desc, raw_skills, domain_tags))

        if dry_run:
            for i in range(min(3, len(texts))):
                logger.info("role_id=%s\n%s\n----------", ids[i], texts[i])
            logger.info("Dry run: %d roles would be embedded. No writes performed.", len(texts))
            return

        logger.info("Encoding %d role documents (no query prefix) ...", len(texts))
        vectors = get_embedder().encode_documents(texts)

        rows = [(rid, _vec_literal(vec), text) for rid, vec, text in zip(ids, vectors, texts)]
        store_role_embeddings(conn, rows)
        logger.info("Done. Wrote embeddings + embedding_text for %d roles.", len(rows))


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild career_roles embeddings with bge-base-en-v1.5.")
    parser.add_argument("--dry-run", action="store_true", help="Print sample canonical_text and exit; no embedding, no writes.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N roles (testing).")
    parser.add_argument("--only-certification", action="store_true", help="Only embed certifications for further gap analysis.")
    args = parser.parse_args()
    try:
        rebuild(limit=args.limit, dry_run=args.dry_run, only_certification=args.only_certification)
    finally:
        if db_pool is not None:
            db_pool.closeall()


if __name__ == "__main__":
    main()