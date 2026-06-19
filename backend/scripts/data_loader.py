"""
Job dataset ETL pipeline.

Target schema: jobtitle | description | essential_skills
Steps:
  1. Load CSV (swap in any source with the same schema via --source)
  2. Map raw columns → JobRecord (flexible column detection)
  3. Normalise essential_skills via NormalizationEngine
  4. Build embedding text in CareerBERT-aligned format
  5. Batch-embed with lwolfrum2/careerbert-jg
  6. Upsert into PostgreSQL job_postings table

"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from typing import Optional

import pandas as pd
import psycopg
from pgvector.psycopg import register_vector

from backend.app.core.config import DATABASE_URL
from backend.app.features.role_matching.embedder import get_embedder
from backend.app.features.role_matching.normalization_layer import (
    get_normalization_engine,
)
from backend.app.features.role_matching.schemas import JobRecord

logger = logging.getLogger("CareerCompass.DataLoader")

DATASET_DEFAULT = "hf://datasets/azrai99/job-dataset/jobstreet_all_job_dataset.csv"

# DB schema

_DDL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS job_postings (
    job_id           TEXT PRIMARY KEY,
    jobtitle         TEXT NOT NULL,
    description      TEXT,
    essential_skills TEXT[],
    raw_text         TEXT NOT NULL,
    embedding        vector(768)
);

CREATE INDEX IF NOT EXISTS job_postings_ivfflat_idx
    ON job_postings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
"""


# Column detection  (handles varied column naming across datasets)

COL_TITLE = ["jobtitle", "job_title", "title", "position", "job_name", "role"]
COL_DESC = ["description", "job_description", "details", "summary", "content"]
COL_SKILLS = [
    "essential_skills", "skills", "required_skills", "skill_requirements",
    "key_skills", "qualifications",
]


def _init_db(conn: psycopg.Connection) -> None:
    conn.execute(_DDL)
    conn.commit()


# Loading

def load_dataframe(source: str = DATASET_DEFAULT) -> pd.DataFrame:
    logger.info("Loading dataset from %s", source)
    df = pd.read_csv(source)
    logger.info("Loaded %d rows, columns: %s", len(df), list(df.columns))
    return df


def _find_col(df: pd.DataFrame, candidates: list[str]) -> Optional[str]:
    lower_map = {c.lower().replace(" ", "_"): c for c in df.columns}
    for name in candidates:
        if name in lower_map:
            return lower_map[name]
    return None


def _extract_skills(value) -> list[str]:
    if pd.isna(value) or not str(value).strip():
        return []
    s = str(value).strip()
    # JSON-ish list: ["Python", "SQL"] or ['Python', 'SQL']
    if s.startswith("["):
        try:
            items = json.loads(s.replace("'", '"'))
            return [str(i).strip() for i in items if str(i).strip()]
        except (json.JSONDecodeError, ValueError):
            pass
    sep = ";" if ";" in s else ","
    return [x.strip() for x in s.split(sep) if x.strip()]


# Embedding text builder  (mirrors CV format for semantic alignment)

def _build_job_text(jobtitle: str, description: Optional[str], skills: list[str]) -> str:
    """
    Format aligned with the CV embedding text so cosine distances are meaningful.
      [Title]: {jobtitle}
      [Skills]: {skill1}, {skill2}, ...
      [Description]: {first 400 chars}
    """
    parts = [f"[Title]: {jobtitle}"]
    if skills:
        parts.append(f"[Skills]: {', '.join(skills[:20])}")
    if description:
        parts.append(f"[Description]: {description[:400].strip()}")
    return "\n".join(parts)



# Row → JobRecord

def build_job_records(df: pd.DataFrame) -> list[JobRecord]:
    engine = get_normalization_engine()

    title_col = _find_col(df, COL_TITLE)
    desc_col = _find_col(df, COL_DESC)
    skill_col = _find_col(df, COL_SKILLS)

    if title_col is None:
        raise ValueError(
            f"No job-title column found. Detected columns: {list(df.columns)}"
        )

    records: list[JobRecord] = []
    for _, row in df.iterrows():
        jobtitle = str(row[title_col]).strip()
        if not jobtitle or jobtitle.lower() == "nan":
            continue

        description: Optional[str] = None
        if desc_col:
            raw_desc = row.get(desc_col, "")
            if not pd.isna(raw_desc) and str(raw_desc).strip():
                description = str(raw_desc).strip()

        raw_skills = _extract_skills(row.get(skill_col, "") if skill_col else "")
        essential_skills = engine.normalize_list(raw_skills)

        embedding_text = _build_job_text(jobtitle, description, essential_skills)
        job_id = hashlib.md5(embedding_text[:256].encode()).hexdigest()[:16]

        records.append(JobRecord(
            job_id=job_id,
            jobtitle=jobtitle,
            description=description,
            essential_skills=essential_skills,
            raw_text=embedding_text,
        ))

    logger.info("Built %d job records.", len(records))
    return records


# DB upsert

def upsert_batch(
    records: list[JobRecord],
    embeddings: list[list[float]],
    conn: psycopg.Connection,
) -> int:
    register_vector(conn)
    with conn.transaction():
        for record, emb in zip(records, embeddings):
            conn.execute(
                """
                INSERT INTO job_postings
                    (job_id, jobtitle, description, essential_skills, raw_text, embedding)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id) DO UPDATE
                    SET jobtitle         = EXCLUDED.jobtitle,
                        description      = EXCLUDED.description,
                        essential_skills = EXCLUDED.essential_skills,
                        raw_text         = EXCLUDED.raw_text,
                        embedding        = EXCLUDED.embedding
                """,
                (
                    record.job_id, record.jobtitle, record.description,
                    record.essential_skills, record.raw_text, emb,
                ),
            )
    return len(records)



def run_pipeline(source: str = DATASET_DEFAULT, batch_size: int = 256) -> None:
    """Load → normalise → embed → store."""
    df = load_dataframe(source)
    records = build_job_records(df)

    embedder = get_embedder()
    total = len(records)
    logger.info("Embedding %d records (batch_size=%d)…", total, batch_size)

    with psycopg.connect(DATABASE_URL) as conn:
        _init_db(conn)
        inserted = 0
        for i in range(0, total, batch_size):
            batch = records[i: i + batch_size]
            texts = [r.raw_text for r in batch]
            embeddings = embedder.encode_batch(texts, batch_size=batch_size)
            inserted += upsert_batch(batch, embeddings, conn)
            logger.info(
                "  Batch %d/%d — %d records upserted.",
                i // batch_size + 1,
                (total + batch_size - 1) // batch_size,
                len(batch),
            )

    # Invalidate BM25 cache after table reload
    from backend.app.features.role_matching.service import invalidate_bm25_cache
    invalidate_bm25_cache()

    logger.info("Pipeline complete. Total upserted: %d", inserted)


# CLI

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s  %(message)s",
    )
    parser = argparse.ArgumentParser(description="Load job dataset into PostgreSQL.")
    parser.add_argument("--source", default=DATASET_DEFAULT, help="CSV path or HF URL")
    parser.add_argument("--batch", type=int, default=256, help="Embedding batch size")
    args = parser.parse_args()
    try:
        run_pipeline(source=args.source, batch_size=args.batch)
    except Exception as exc:
        logger.error("Pipeline failed: %s", exc)
        sys.exit(1)
