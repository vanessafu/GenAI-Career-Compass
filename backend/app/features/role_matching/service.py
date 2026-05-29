import logging

import psycopg
from pgvector.psycopg import register_vector

from backend.app.core.config import DATABASE_URL
from backend.app.core import openai_client
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.schemas import RoleMatch, RoleMatchResponse

logger = logging.getLogger("CareerCompass.RoleMatching.Service")

EMBEDDING_MODEL = ""


# ---------------------------------------------------------------------------
# Query text builder
# ---------------------------------------------------------------------------


def build_cv_query_text(cv_data: CVData) -> str:
    """
    Flatten CVData into a single text for embedding-based similarity search.
    Mirrors the structure used in build_embeddings.py so the query lives in
    the same vector space as the indexed occupations.
    """
    parts: list[str] = []

    if cv_data.personal_info.current_role:
        parts.append(f"Current role: {cv_data.personal_info.current_role}")

    if cv_data.profile_summary.summary:
        parts.append(f"Summary: {cv_data.profile_summary.summary}")

    tech_skills = [s.name for s in cv_data.skills_extracted.technical_skills[:15]]
    if tech_skills:
        parts.append(f"Technical skills: {', '.join(tech_skills)}")

    soft_skills = cv_data.skills_extracted.soft_skills[:8]
    if soft_skills:
        parts.append(f"Soft skills: {', '.join(soft_skills)}")

    exp_parts: list[str] = []
    for exp in cv_data.experience[:4]:
        if not exp.role:
            continue
        item = exp.role
        if exp.organization:
            item += f" at {exp.organization}"
        if exp.core_responsibilities:
            item += f" ({'; '.join(exp.core_responsibilities[:2])})"
        exp_parts.append(item)
    if exp_parts:
        parts.append(f"Work experience: {' | '.join(exp_parts)}")

    edu_parts: list[str] = []
    for edu in cv_data.education[:2]:
        if edu.field_of_study:
            label = f"{edu.degree_type} in {edu.field_of_study}" if edu.degree_type else edu.field_of_study
            edu_parts.append(label)
    if edu_parts:
        parts.append(f"Education: {', '.join(edu_parts)}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# pgvector retrieval
# ---------------------------------------------------------------------------


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [lbl.strip() for lbl in value.split(",") if lbl.strip()]


async def retrieve_similar_roles(query_text: str, top_k: int = 5) -> list[RoleMatch]:
    """Embed the query and return the top-k most similar ESCO occupations."""
    query_embedding = await openai_client.embed(query_text, model=EMBEDDING_MODEL)

    with psycopg.connect(DATABASE_URL) as conn:
        register_vector(conn)
        rows = conn.execute(
            """
            SELECT
                uri,
                isco_group,
                isco_label,
                title,
                alt_labels,
                description,
                essential_knowledge,
                essential_skills,
                optional_knowledge,
                optional_skills,
                1 - (embedding <=> %s::vector) AS similarity
            FROM esco_occupations
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (query_embedding, query_embedding, top_k),
        ).fetchall()

    return [
        RoleMatch(
            uri=row[0],
            isco_group=row[1] or None,
            isco_label=row[2] or None,
            title=row[3],
            alt_labels=_split_csv(row[4]),
            description=row[5] or None,
            essential_knowledge=_split_csv(row[6]),
            essential_skills=_split_csv(row[7]),
            optional_knowledge=_split_csv(row[8]),
            optional_skills=_split_csv(row[9]),
            similarity_score=round(float(row[10]), 4),
        )
        for row in rows
    ]


# ---------------------------------------------------------------------------
# LLM generation
# ---------------------------------------------------------------------------


async def generate_role_analysis(cv_data: CVData, matched_roles: list[RoleMatch]) -> str:
    roles_block = "\n".join(
        f"{i + 1}. {r.title} (match: {r.similarity_score:.0%})"
        + (f"\n   {r.description[:250]}" if r.description else "")
        for i, r in enumerate(matched_roles)
    )

    current_role = cv_data.personal_info.current_role or "not specified"
    skills = [s.name for s in cv_data.skills_extracted.technical_skills[:10]]
    # The following can be changed after implementing the prompt engineering feature
    user_prompt = (
        f"User's current role: {current_role}\n"
        f"Key technical skills: {', '.join(skills) or 'not specified'}\n\n"
        f"Top matched roles from the ESCO occupational database:\n{roles_block}\n\n"
        "In 3–4 concise sentences: explain which roles are the strongest fit, "
        "what makes them a good match for this user's background, and which "
        "transition would require the least additional skill development."
    )

    return await openai_client.complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert career advisor. Give practical, specific advice "
                    "grounded in the user's actual skills and experience. Be concise."
                ),
            },
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=350,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def match_roles_for_cv(cv_data: CVData, top_k: int = 5) -> RoleMatchResponse:
    """
    Full RAG pipeline:
      1. Build a query string from the parsed CV.
      2. Embed the query and retrieve top-k ESCO occupations from pgvector.
      3. Pass retrieved roles to the LLM to generate a personalised analysis.
    """
    query_text = build_cv_query_text(cv_data)
    logger.info("CV query text:\n%s", query_text)

    matched_roles = await retrieve_similar_roles(query_text, top_k=top_k)
    logger.info("Retrieved %d role matches.", len(matched_roles))

    analysis = await generate_role_analysis(cv_data, matched_roles)

    return RoleMatchResponse(
        query_text=query_text,
        matched_roles=matched_roles,
        analysis=analysis,
    )
