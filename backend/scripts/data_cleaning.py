"""
One-off cleanup: remove a fixed list of low-quality/duplicate role_ids and
all their dependent rows from the role_matching tables.

Run:
    python -m backend.scripts.data_cleaning              # dry-run: report row counts only, no writes
    python -m backend.scripts.data_cleaning --execute     # actually delete

Deletes from child tables first (certifications_mapping, esco_mappings,
role_salaries, role_skills), then from career_roles, all inside one
transaction so a failure midway leaves the database untouched.
"""
from __future__ import annotations

import argparse
import logging

from backend.app.core.database import db_pool, get_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CareerCompass.DataCleaning")

ROLE_IDS_TO_DELETE: list[int] = [
    3, 4, 14, 19, 20, 21, 22, 32, 36, 39, 40, 42, 43, 45, 49, 50, 52, 54, 55, 56,
    62, 63, 69, 70, 71, 72, 74, 75, 77, 79, 83, 91, 92, 93, 94, 95, 103, 104, 105,
    106, 107, 108, 109, 110, 112, 114, 116, 119, 127, 130, 132, 135, 139, 140,
    141, 142, 143, 144, 145, 148, 150, 151, 154, 155, 156, 163, 164, 165, 166,
    175, 182, 184, 185, 186, 187, 188, 193, 197, 198, 199, 200, 201, 202, 203,
    204, 205, 206, 207, 208, 209, 210, 211, 212, 213, 214, 215, 216, 217, 218,
    219, 220, 221, 222, 224, 225, 226, 227, 228, 229, 230, 231, 232, 233, 234,
    235, 236, 237, 238, 239, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249,
    250, 251, 252, 253, 254, 255, 256, 257, 258, 259, 260, 261, 262, 263, 264,
    265, 266, 267, 268, 269, 270, 271, 272, 273, 274, 275, 276, 277, 278, 279,
    280, 281, 282, 283, 284, 285, 286, 287, 288, 289, 290, 291, 292, 293, 294,
    295, 296, 297, 298, 299, 300, 301, 302, 303, 304, 305, 306, 307, 308, 309,
    310, 311, 312, 313, 314, 326, 344, 357, 358, 361, 362, 367, 368, 370, 376,
    383, 391, 394, 401, 431, 436, 450, 462,
]

# Child tables (rows keyed by role_id) deleted before the career_roles parent.
CHILD_TABLES = ["certifications_mapping", "esco_mappings", "role_salaries", "role_skills"]
PARENT_TABLE = "career_roles"


def _counts(conn, role_ids: list[int]) -> dict[str, int]:
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in [*CHILD_TABLES, PARENT_TABLE]:
            cur.execute(f"SELECT count(*) FROM {table} WHERE role_id = ANY(%s)", (role_ids,))
            counts[table] = cur.fetchone()[0]
    return counts


def run(role_ids: list[int], *, execute: bool) -> None:
    role_ids = sorted(set(role_ids))
    with get_db_connection() as conn:
        counts = _counts(conn, role_ids)
        for table, count in counts.items():
            logger.info("%s: %d row(s) match the given role_ids.", table, count)

        if not execute:
            logger.info("Dry-run only (pass --execute to delete). No rows were removed.")
            return

        with conn.cursor() as cur:
            for table in CHILD_TABLES:
                cur.execute(f"DELETE FROM {table} WHERE role_id = ANY(%s)", (role_ids,))
                logger.info("Deleted %d row(s) from %s.", cur.rowcount, table)
            cur.execute(f"DELETE FROM {PARENT_TABLE} WHERE role_id = ANY(%s)", (role_ids,))
            logger.info("Deleted %d row(s) from %s.", cur.rowcount, PARENT_TABLE)
        conn.commit()
        logger.info("Done. Removed %d role_id(s) and all dependent rows.", len(role_ids))


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete a fixed list of role_ids and their dependent rows.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the deletion. Without this flag, only row counts are reported.",
    )
    args = parser.parse_args()
    try:
        run(ROLE_IDS_TO_DELETE, execute=args.execute)
    finally:
        if db_pool is not None:
            db_pool.closeall()


if __name__ == "__main__":
    main()
