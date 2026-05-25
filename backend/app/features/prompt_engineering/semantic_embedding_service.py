from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.prompt_engineering.career_profile_extraction_service import build_career_profile_response
from backend.app.features.prompt_engineering.schemas import (
    CareerProfile,
    EmbeddingChunk,
    EmbeddingMetadata,
    PrivacyStrippedProfileDraft,
    SemanticEmbeddingInputResponse,
)


# TODO: This service currently performs deterministic chunk-level grounding with
# local keyword rules and template text. Once the retrieval dataset layer is
# available, enrich chunks with canonical skill/domain/role IDs from sources
# such as ESCO/O*NET/SFIA or an internal career graph. An LLM may then be used
# only as a controlled evidence-backed chunk rewriter/compressor, constrained by
# source evidence and canonical candidates, not as a free-form signal generator.

CHUNK_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Computer Vision": (
        "computer vision",
        "cv applications",
        "image",
        "camera",
        "reidentification",
        "detection",
    ),
    "Deep Learning": (
        "deep learning",
        "neural network",
        "model training",
    ),
    "Graph ML": (
        "gnn",
        "graph neural network",
        "graph ml",
    ),
    "3D Vision": (
        "3d",
        "gaussian splatting",
        "unreal engine",
        "camera alignment",
        "human generation",
    ),
    "Robotics": (
        "robotics",
        "robot",
        "perception",
        "slam",
    ),
    "Backend Engineering": (
        "backend",
        "api",
        "server",
        "database",
        "python developer",
    ),
    "Frontend Engineering": (
        "frontend",
        "web developer",
        "website",
        "wordpress",
        "typescript",
        "javascript",
        "ui",
        "gui",
    ),
    "Cloud and DevOps": (
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "ci/cd",
    ),
    "Cybersecurity": (
        "security",
        "cybersecurity",
        "vulnerability",
        "penetration",
    ),
    "UX Research": (
        "ux research",
        "user research",
        "usability",
        "interview",
        "survey",
    ),
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _dedupe_preserve_order(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = _clean_text(value)
        if cleaned is None:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _join_inline(values: list[str | None]) -> str | None:
    cleaned_values = _dedupe_preserve_order(values)
    if not cleaned_values:
        return None
    return "; ".join(cleaned_values)


def _chunk_domains_for_text(text: str, career_profile: CareerProfile) -> list[str]:
    text_lower = text.casefold()
    matched_domains = [
        domain
        for domain in career_profile.technical_domains
        if any(
            keyword in text_lower
            for keyword in CHUNK_DOMAIN_KEYWORDS.get(domain, (domain.casefold(),))
        )
    ]
    return _dedupe_preserve_order(matched_domains)


def _chunk_skills_for_text(
    text: str,
    draft: PrivacyStrippedProfileDraft,
) -> list[str]:
    text_lower = text.casefold()
    explicit_skills = [
        skill.name
        for skill in draft.technical_skills
        if skill.name.casefold() in text_lower
    ]

    project_technologies = [
        technology
        for project in draft.projects
        for technology in project.technologies
        if technology.casefold() in text_lower
    ]

    inferred_terms = [
        term
        for term in (
            "Python",
            "TypeScript",
            "C++",
            "Unreal Engine 5",
            "Selenium",
            "Qt",
            "WordPress",
            "Gaussian Splatting",
            "GNN",
            "Deep Learning",
            "Computer Vision",
        )
        if term.casefold() in text_lower
    ]

    return _dedupe_preserve_order(explicit_skills + project_technologies + inferred_terms)


def _build_embedding_metadata(
    draft: PrivacyStrippedProfileDraft,
    career_profile: CareerProfile,
) -> EmbeddingMetadata:
    return EmbeddingMetadata(
        current_role=draft.current_role,
        current_seniority_level=career_profile.seniority_estimate
        or draft.current_seniority_level,
        years_of_experience=draft.years_of_experience,
        technical_skills=_dedupe_preserve_order(
            [skill.name for skill in draft.technical_skills]
            + career_profile.technical_domains
            + career_profile.competency_signals
        ),
        soft_skills=_dedupe_preserve_order(draft.soft_skills),
        interests=_dedupe_preserve_order(draft.interests),
        industries=_dedupe_preserve_order(
            [experience.industry for experience in draft.experience]
        ),
    )


def _experience_chunk_text(
    index: int,
    role: str | None,
    duration_months: int | None,
    responsibilities: list[str],
    contextual_skills: list[str],
) -> str:
    parts: list[str] = []
    if role:
        parts.append(f"Experience {index}: candidate worked as {role}")
    else:
        parts.append(f"Experience {index}: candidate completed a work experience")

    if duration_months is not None:
        parts.append(f"for {duration_months} months")

    details = _join_inline(responsibilities + contextual_skills)
    if details:
        parts.append(f"involving {details}")

    return " ".join(parts) + "."


def _project_chunk_text(
    index: int,
    title: str | None,
    description: str | None,
    technologies: list[str],
) -> str:
    parts: list[str] = []
    if title:
        parts.append(f"Project {index}: candidate completed {title}")
    else:
        parts.append(f"Project {index}: candidate completed a technical project")

    if description:
        parts.append(f"focused on {description}")

    technology_text = _join_inline(technologies)
    if technology_text:
        parts.append(f"using {technology_text}")

    return " ".join(parts) + "."


def _build_experience_chunks(
    draft: PrivacyStrippedProfileDraft,
    career_profile: CareerProfile,
) -> list[EmbeddingChunk]:
    chunks: list[EmbeddingChunk] = []
    for index, experience in enumerate(draft.experience, start=1):
        text = _experience_chunk_text(
            index=index,
            role=experience.role,
            duration_months=experience.duration_months,
            responsibilities=experience.core_responsibilities,
            contextual_skills=experience.contextual_skills,
        )
        chunks.append(
            EmbeddingChunk(
                chunk_id=f"experience_{index}",
                chunk_type="experience",
                text=text,
                skills=_chunk_skills_for_text(text, draft),
                domains=_chunk_domains_for_text(text, career_profile),
            )
        )
    return chunks


def _build_project_chunks(
    draft: PrivacyStrippedProfileDraft,
    career_profile: CareerProfile,
) -> list[EmbeddingChunk]:
    chunks: list[EmbeddingChunk] = []
    for index, project in enumerate(draft.projects, start=1):
        text = _project_chunk_text(
            index=index,
            title=project.title,
            description=project.description,
            technologies=project.technologies,
        )
        chunks.append(
            EmbeddingChunk(
                chunk_id=f"project_{index}",
                chunk_type="project",
                text=text,
                skills=_chunk_skills_for_text(text, draft),
                domains=_chunk_domains_for_text(text, career_profile),
            )
        )
    return chunks


def _build_competency_chunk(
    career_profile: CareerProfile,
) -> EmbeddingChunk | None:
    if not career_profile.competency_signals:
        return None

    competency_text = _join_inline(career_profile.competency_signals)
    domain_text = _join_inline(career_profile.technical_domains)
    text = (
        "Candidate shows competency signals in "
        f"{competency_text}."
    )
    if domain_text:
        text += f" These signals relate to {domain_text}."

    return EmbeddingChunk(
        chunk_id="competency_1",
        chunk_type="competency",
        text=text,
        skills=[],
        domains=career_profile.technical_domains,
    )


def _build_career_intent_chunk(
    career_profile: CareerProfile,
) -> EmbeddingChunk | None:
    profile_parts = _dedupe_preserve_order(
        career_profile.career_orientation
        + career_profile.career_domains
        + career_profile.career_direction_candidates
    )
    if not profile_parts:
        return None

    text = (
        "Candidate career trajectory signals include "
        f"{_join_inline(profile_parts)}."
    )
    if career_profile.seniority_estimate:
        text += f" Seniority estimate is {career_profile.seniority_estimate}."

    return EmbeddingChunk(
        chunk_id="career_intent_1",
        chunk_type="career_intent",
        text=text,
        skills=[],
        domains=_dedupe_preserve_order(
            career_profile.career_domains + career_profile.technical_domains
        ),
    )


def build_embedding_chunks(
    draft: PrivacyStrippedProfileDraft,
    career_profile: CareerProfile,
) -> SemanticEmbeddingInputResponse:
    chunks: list[EmbeddingChunk] = []
    chunks.extend(_build_experience_chunks(draft, career_profile))
    chunks.extend(_build_project_chunks(draft, career_profile))

    competency_chunk = _build_competency_chunk(career_profile)
    if competency_chunk is not None:
        chunks.append(competency_chunk)

    career_intent_chunk = _build_career_intent_chunk(career_profile)
    if career_intent_chunk is not None:
        chunks.append(career_intent_chunk)

    return SemanticEmbeddingInputResponse(
        career_profile=career_profile,
        chunks=chunks,
        embedding_metadata=_build_embedding_metadata(draft, career_profile),
    )


def build_embedding_chunks_from_confirmed(
    confirmed_profile: ConfirmedCVData,
) -> SemanticEmbeddingInputResponse:
    career_profile_response = build_career_profile_response(confirmed_profile)
    return build_embedding_chunks(
        draft=career_profile_response.privacy_stripped_profile_draft,
        career_profile=career_profile_response.career_profile,
    )
