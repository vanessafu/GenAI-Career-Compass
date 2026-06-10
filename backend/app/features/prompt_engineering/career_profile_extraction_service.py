from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.prompt_engineering.profile_projector import build_privacy_stripped_profile_draft
from backend.app.features.prompt_engineering.schemas import (
    CareerProfile,
    CareerProfileResponse,
    PrivacyStrippedProfileDraft,
)


# TODO: Replace this local deterministic taxonomy with a two-stage normalization
# pipeline once the career dataset layer is available:
# 1. Use canonical datasets such as ESCO/O*NET/SFIA or an internal career graph
#    to normalize roles, skills, technical domains, seniority levels, and career
#    direction candidates against stable IDs instead of free-text labels.
# 2. Use an LLM only as a controlled evidence-backed normalizer/disambiguator,
#    constrained by retrieved dataset candidates and the CareerProfile schema.
#    The LLM should refine labels and resolve ambiguity, not invent unsupported
#    roles, domains, competencies, or seniority claims.

TECHNICAL_DOMAIN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Computer Vision": (
        "computer vision",
        "image",
        "camera",
        "opencv",
        "object detection",
        "segmentation",
        "person re-identification",
        "re-identification",
    ),
    "Deep Learning": (
        "deep learning",
        "neural network",
        "pytorch",
        "tensorflow",
        "keras",
        "transformer",
        "cnn",
        "model training",
    ),
    "Machine Learning": (
        "machine learning",
        "ml",
        "classification",
        "regression",
        "clustering",
        "predictive",
    ),
    "Graph ML": (
        "gnn",
        "graph neural network",
        "graph ml",
        "graph machine learning",
    ),
    "3D Vision": (
        "3d",
        "gaussian splatting",
        "point cloud",
        "unreal engine",
        "camera alignment",
        "3d reconstruction",
    ),
    "Robotics": (
        "robotics",
        "robot",
        "ros",
        "slam",
        "path planning",
        "perception",
    ),
    "Data Analytics": (
        "data analysis",
        "analytics",
        "dashboard",
        "tableau",
        "power bi",
        "sql",
        "statistics",
    ),
    "Data Engineering": (
        "etl",
        "pipeline",
        "data warehouse",
        "spark",
        "airflow",
        "dbt",
    ),
    "Backend Engineering": (
        "backend",
        "api",
        "fastapi",
        "django",
        "flask",
        "postgres",
        "database",
    ),
    "Frontend Engineering": (
        "frontend",
        "react",
        "typescript",
        "javascript",
        "html",
        "css",
        "ui",
    ),
    "Cloud and DevOps": (
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "ci/cd",
        "devops",
    ),
    "Cybersecurity": (
        "cybersecurity",
        "security",
        "penetration",
        "vulnerability",
        "siem",
        "incident response",
    ),
    "UX Research": (
        "ux research",
        "user research",
        "usability",
        "interview",
        "survey",
        "figma",
    ),
}

COMPETENCY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Applied Machine Learning": (
        "machine learning",
        "deep learning",
        "model",
        "training",
        "prediction",
    ),
    "Computer Vision Systems": (
        "computer vision",
        "image",
        "camera",
        "object detection",
        "segmentation",
    ),
    "3D Vision and Simulation": (
        "3d",
        "gaussian splatting",
        "unreal engine",
        "simulation",
        "camera alignment",
    ),
    "Graph ML Modeling": (
        "gnn",
        "graph neural network",
        "graph ml",
    ),
    "Backend API Development": (
        "backend",
        "api",
        "fastapi",
        "django",
        "flask",
    ),
    "Data Analysis and Reporting": (
        "data analysis",
        "analytics",
        "dashboard",
        "reporting",
        "statistics",
    ),
    "Research Prototyping": (
        "research",
        "thesis",
        "publication",
        "prototype",
        "experiment",
    ),
    "Automation and Testing": (
        "automation",
        "selenium",
        "testing",
        "test",
        "scraping",
    ),
    "Security Analysis": (
        "security",
        "vulnerability",
        "penetration",
        "incident response",
    ),
    "User Research": (
        "ux research",
        "user research",
        "usability",
        "interview",
        "survey",
    ),
}

ROLE_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Computer Vision Engineer", ("computer vision", "image", "camera", "opencv")),
    ("Machine Learning Engineer", ("machine learning", "ml", "deep learning")),
    ("Graph ML Engineer", ("gnn", "graph neural network", "graph ml")),
    ("Robotics Engineer", ("robotics", "robot", "ros", "slam")),
    ("Data Analyst", ("data analyst", "data analysis", "analytics", "dashboard")),
    ("Data Engineer", ("data engineer", "etl", "pipeline", "data warehouse")),
    ("Backend Engineer", ("backend", "api", "server", "fastapi", "django")),
    ("Frontend Engineer", ("frontend", "react", "typescript", "javascript")),
    ("Full Stack Engineer", ("full stack", "fullstack")),
    ("Cybersecurity Analyst", ("cybersecurity", "security analyst", "security")),
    ("UX Researcher", ("ux researcher", "ux research", "user research")),
)


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


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _is_vague_role(role_lower: str) -> bool:
    vague_terms = (
        "assistant",
        "developer",
        "development",
        "engineer",
        "intern",
        "internship",
        "student",
        "working student",
    )
    return _contains_any(role_lower, vague_terms)


def _append_labeled_text(parts: list[str], label: str, value: str | None) -> None:
    cleaned = _clean_text(value)
    if cleaned:
        parts.append(f"{label}: {cleaned}")


def _evidence_texts(draft: PrivacyStrippedProfileDraft) -> list[str]:
    parts: list[str] = []
    _append_labeled_text(parts, "current role", draft.current_role)
    _append_labeled_text(parts, "summary", draft.summary)

    for experience in draft.experience:
        _append_labeled_text(parts, "experience role", experience.role)
        _append_labeled_text(parts, "experience industry", experience.industry)
        parts.extend(experience.core_responsibilities)
        parts.extend(experience.contextual_skills)

    for education in draft.education:
        _append_labeled_text(parts, "degree", education.degree_type)
        _append_labeled_text(parts, "field", education.field_of_study)

    for project in draft.projects:
        _append_labeled_text(parts, "project", project.title)
        _append_labeled_text(parts, "project description", project.description)
        parts.extend(project.technologies)

    parts.extend(skill.name for skill in draft.technical_skills)
    parts.extend(draft.soft_skills)
    parts.extend(signal.value for signal in draft.career_signals)
    parts.extend(draft.interests)

    return _dedupe_preserve_order(parts)


def _joined_evidence(draft: PrivacyStrippedProfileDraft) -> str:
    return " ".join(_evidence_texts(draft)).casefold()


def _normalize_role_label(role: str, context: str) -> str:
    role_lower = role.casefold()
    searchable_role = f"{role_lower} {context}" if _is_vague_role(role_lower) else role_lower
    is_intern = "intern" in role_lower or "internship" in role_lower

    for normalized_role, keywords in ROLE_KEYWORDS:
        if _contains_any(searchable_role, keywords):
            if is_intern and "Intern" not in normalized_role:
                return f"{normalized_role} Intern"
            return normalized_role

    if "student" in role_lower or "master" in role_lower or "msc" in role_lower:
        return "Student"

    cleaned = _clean_text(role)
    if cleaned is None:
        return "Unknown Role"
    return cleaned.title()


def _extract_normalized_roles(
    draft: PrivacyStrippedProfileDraft,
    evidence_text: str,
) -> list[str]:
    raw_roles = [draft.current_role]
    raw_roles.extend(experience.role for experience in draft.experience)

    normalized = [
        _normalize_role_label(role, evidence_text)
        for role in _dedupe_preserve_order(raw_roles)
    ]

    if not normalized:
        if any(
            field.field_of_study
            and _contains_any(field.field_of_study.casefold(), ("computer science", "ai"))
            for field in draft.education
        ):
            normalized.append("Student")

    return _dedupe_preserve_order(normalized)


def _infer_technical_domains(evidence_text: str) -> list[str]:
    domains = [
        domain
        for domain, keywords in TECHNICAL_DOMAIN_KEYWORDS.items()
        if _contains_any(evidence_text, keywords)
    ]
    return _dedupe_preserve_order(domains)


def _infer_career_domains(
    technical_domains: list[str],
    evidence_text: str,
) -> list[str]:
    domains: list[str] = []

    if any(
        domain in technical_domains
        for domain in (
            "Computer Vision",
            "Deep Learning",
            "Machine Learning",
            "Graph ML",
            "3D Vision",
            "Robotics",
        )
    ):
        domains.append("AI Engineering")

    if any(
        domain in technical_domains
        for domain in (
            "Backend Engineering",
            "Frontend Engineering",
            "Cloud and DevOps",
        )
    ):
        domains.append("Software Engineering")

    if any(
        domain in technical_domains
        for domain in ("Data Analytics", "Data Engineering")
    ):
        domains.append("Data Careers")

    if "Cybersecurity" in technical_domains:
        domains.append("Cybersecurity")

    if "UX Research" in technical_domains:
        domains.append("UX and Product Research")

    research_terms = ("research", "thesis", "publication", "experiment", "prototype")
    if _contains_any(evidence_text, research_terms):
        domains.append("Research Engineering")

    return _dedupe_preserve_order(domains)


def _infer_competency_signals(evidence_text: str) -> list[str]:
    signals = [
        competency
        for competency, keywords in COMPETENCY_KEYWORDS.items()
        if _contains_any(evidence_text, keywords)
    ]
    return _dedupe_preserve_order(signals)


def _infer_career_orientation(
    career_domains: list[str],
    technical_domains: list[str],
    evidence_text: str,
) -> list[str]:
    orientations: list[str] = []

    if "Research Engineering" in career_domains:
        orientations.append("research engineering")

    if "AI Engineering" in career_domains:
        orientations.append("AI/ML engineering")

    if "Software Engineering" in career_domains:
        orientations.append("software product engineering")

    if "Data Careers" in career_domains:
        orientations.append("data analytics and insights")

    if "Cybersecurity" in technical_domains:
        orientations.append("cybersecurity")

    if "UX Research" in technical_domains:
        orientations.append("UX research")

    if _contains_any(evidence_text, ("stakeholder", "business", "client", "consulting")):
        orientations.append("business-facing technology work")

    return _dedupe_preserve_order(orientations)


def _estimate_seniority(
    draft: PrivacyStrippedProfileDraft,
    evidence_text: str,
) -> tuple[str | None, list[str]]:
    evidence: list[str] = []
    level = _clean_text(draft.current_seniority_level)
    years = draft.years_of_experience

    if level:
        evidence.append(f"CV profile summary states seniority as {level}.")

    if years is not None:
        evidence.append(f"CV profile summary states {years} years of experience.")

    has_internship = _contains_any(evidence_text, ("intern", "internship"))
    has_student_signal = _contains_any(
        evidence_text,
        ("student", "msc", "master", "bachelor", "thesis", "university"),
    )

    if has_internship:
        evidence.append("Experience includes internship-level role evidence.")

    if has_student_signal:
        evidence.append("Education or project evidence indicates a student profile.")

    if level:
        return level, _dedupe_preserve_order(evidence)

    if has_student_signal and (years is None or years <= 2):
        return "student / early-career", _dedupe_preserve_order(evidence)

    if has_internship and (years is None or years <= 2):
        return "intern / early-career", _dedupe_preserve_order(evidence)

    if years is None:
        return None, _dedupe_preserve_order(evidence)

    if years >= 7:
        return "senior", _dedupe_preserve_order(evidence)
    if years >= 3:
        return "mid-level", _dedupe_preserve_order(evidence)
    if years >= 1:
        return "junior", _dedupe_preserve_order(evidence)
    return "entry-level", _dedupe_preserve_order(evidence)


def _infer_career_direction_candidates(
    career_domains: list[str],
    technical_domains: list[str],
    career_orientation: list[str],
) -> list[str]:
    candidates: list[str] = []

    if "Computer Vision" in technical_domains:
        candidates.append("Computer Vision Engineer")

    if "3D Vision" in technical_domains:
        candidates.append("3D Vision / Simulation Engineer")

    if "Graph ML" in technical_domains:
        candidates.append("Graph Machine Learning Engineer")

    if "Robotics" in technical_domains:
        candidates.append("Robotics Perception Engineer")

    if "AI/ML engineering" in career_orientation:
        candidates.append("Machine Learning Engineer")

    if "research engineering" in career_orientation:
        candidates.append("Research Engineer")

    if "Software Engineering" in career_domains:
        candidates.append("Software Engineer")

    if "Data Careers" in career_domains:
        candidates.append("Data Analyst")

    if "Cybersecurity" in career_domains:
        candidates.append("Cybersecurity Analyst")

    if "UX and Product Research" in career_domains:
        candidates.append("UX Researcher")

    return _dedupe_preserve_order(candidates)


def extract_career_profile(draft: PrivacyStrippedProfileDraft) -> CareerProfile:
    """Build a deterministic structured career profile from a privacy-safe draft."""
    evidence_text = _joined_evidence(draft)
    normalized_roles = _extract_normalized_roles(draft, evidence_text)
    technical_domains = _infer_technical_domains(evidence_text)
    career_domains = _infer_career_domains(technical_domains, evidence_text)
    competency_signals = _infer_competency_signals(evidence_text)
    career_orientation = _infer_career_orientation(
        career_domains=career_domains,
        technical_domains=technical_domains,
        evidence_text=evidence_text,
    )
    seniority_estimate, seniority_evidence = _estimate_seniority(draft, evidence_text)
    career_direction_candidates = _infer_career_direction_candidates(
        career_domains=career_domains,
        technical_domains=technical_domains,
        career_orientation=career_orientation,
    )

    return CareerProfile(
        normalized_roles=normalized_roles,
        career_domains=career_domains,
        technical_domains=technical_domains,
        competency_signals=competency_signals,
        career_orientation=career_orientation,
        seniority_estimate=seniority_estimate,
        seniority_evidence=seniority_evidence,
        career_direction_candidates=career_direction_candidates,
    )


def build_career_profile_response(
    confirmed_profile: ConfirmedCVData,
) -> CareerProfileResponse:
    draft = build_privacy_stripped_profile_draft(confirmed_profile)
    return CareerProfileResponse(
        privacy_stripped_profile_draft=draft,
        career_profile=extract_career_profile(draft),
    )
