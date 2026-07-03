from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.role_matching.normalization import clean_alias_map, normalize_skill_key

FULL_CREDIT = 1.0
TOKEN_CREDIT = 0.75
CONTEXT_CREDIT = 0.6

# Skill importance weighting (0-1 scores from career_roles.sort_skills).
# Tiers mirror the Gemini ranking prompt in backend/scripts/role_embeddings.py.
ESSENTIAL_WEIGHT = 0.75
IMPORTANT_WEIGHT = 0.40
DEFAULT_SKILL_WEIGHT = 0.5  # used when a required skill has no known importance score
_IMPORTANCE_RANK = {"essential": 0, "important": 1, "nice_to_have": 2, "": 3}


def skill_importance_tier(weight: float | None) -> str:
    if weight is None:
        return ""
    if weight >= ESSENTIAL_WEIGHT:
        return "essential"
    if weight >= IMPORTANT_WEIGHT:
        return "important"
    return "nice_to_have"


@dataclass(frozen=True)
class SkillEvidence:
    explicit_terms: list[str] = field(default_factory=list)
    context_terms: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SkillAlignment:
    coverage: float
    matched_skills: list[str]
    missing_skills: list[str]
    skill_gaps: list[dict[str, Any]]
    domain_scores: dict[str, float] = field(default_factory=dict)
    domain_skills: dict[str, list[str]] = field(default_factory=dict)


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9+#]+", "", value.casefold())


def _dedupe(values: Iterable[str | None]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = " ".join(str(value or "").split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _canon(value: str, alias_map: dict[str, str]) -> str:
    key = normalize_skill_key(value)
    return alias_map.get(key, key)


def _text_parts(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _cv_data(profile: ConfirmedCVData | CVData) -> CVData:
    return profile.confirmed_cv_data if isinstance(profile, ConfirmedCVData) else profile


def build_skill_evidence_from_confirmed_profile(profile: ConfirmedCVData | CVData) -> SkillEvidence:
    cv = _cv_data(profile)
    explicit: list[str] = []
    context: list[str] = []

    context.extend(
        [
            cv.personal_info.current_role,
            cv.profile_summary.summary,
            cv.profile_summary.current_seniority_level,
            *cv.interests,
        ]
    )

    for skill in cv.skills_extracted.technical_skills:
        explicit.append(skill.name)
    explicit.extend(cv.skills_extracted.soft_skills)

    for exp in cv.experience:
        context.extend([exp.role, exp.industry, *exp.core_responsibilities])
        explicit.extend(exp.contextual_skills)

    for education in cv.education:
        context.extend(
            [
                education.degree_type,
                education.field_of_study,
                education.institution,
                education.thesis_title,
                *education.courses,
            ]
        )

    for project in cv.projects:
        context.extend([project.title, project.description, project.role, *project.outcomes])
        explicit.extend(project.technologies)

    for thesis in cv.thesis:
        context.extend([thesis.title, thesis.degree_type, thesis.institution, thesis.description])
        explicit.extend(thesis.technologies)

    return SkillEvidence(explicit_terms=_dedupe(explicit), context_terms=_dedupe(context))


def build_skill_evidence_from_user_profile(profile: Any) -> SkillEvidence:
    explicit: list[str] = []
    context: list[str] = []

    identity = getattr(profile, "career_identity", None)
    context.extend([getattr(identity, "title", None), getattr(identity, "summary", None)])
    context.extend(_text_parts(getattr(profile, "interests", None)))
    explicit.extend(_text_parts(getattr(profile, "skills", None)))

    for exp in getattr(profile, "experience", None) or []:
        context.extend([getattr(exp, "role", None), getattr(exp, "summary", None)])
        explicit.extend(_text_parts(getattr(exp, "skills", None)))

    for education in getattr(profile, "education", None) or []:
        context.extend([getattr(education, "degree", None), getattr(education, "institution", None)])

    for project in getattr(profile, "projects", None) or []:
        context.extend([getattr(project, "title", None), getattr(project, "summary", None)])
        explicit.extend(_text_parts(getattr(project, "technologies", None)))

    for certification in getattr(profile, "certifications", None) or []:
        context.extend([getattr(certification, "name", None), getattr(certification, "issuer", None)])

    return SkillEvidence(explicit_terms=_dedupe(explicit), context_terms=_dedupe(context))


def _variant_match(required: str, candidate: str) -> bool:
    if required == candidate:
        return True

    required_compact = _compact(required)
    candidate_compact = _compact(candidate)
    if required_compact and required_compact == candidate_compact:
        return True

    if required_compact and re.fullmatch(re.escape(required_compact) + r"\d+", candidate_compact):
        return True
    if candidate_compact and re.fullmatch(re.escape(candidate_compact) + r"\d+", required_compact):
        return True

    return False


def _token_score(required: str, candidate: str) -> float:
    req_tokens = {_singular_token(token) for token in required.split()}
    cand_tokens = {_singular_token(token) for token in candidate.split()}
    if not req_tokens or not cand_tokens:
        return 0.0
    if req_tokens <= cand_tokens or cand_tokens <= req_tokens:
        return TOKEN_CREDIT
    overlap = req_tokens & cand_tokens
    if overlap and len(overlap) / len(req_tokens) >= 0.5:
        return TOKEN_CREDIT
    return 0.0


def _singular_token(token: str) -> str:
    if len(token) > 3 and token.endswith("s"):
        return token[:-1]
    return token


def _best_score(required: str, candidates: Iterable[str], alias_map: dict[str, str]) -> tuple[float, str | None]:
    best_score = 0.0
    best_candidate: str | None = None
    for candidate in candidates:
        canonical = _canon(candidate, alias_map)
        if _variant_match(required, canonical):
            return FULL_CREDIT, canonical
        score = _token_score(required, canonical)
        if score > best_score:
            best_score = score
            best_candidate = canonical
    return best_score, best_candidate


def _context_score(required: str, context_terms: Iterable[str], alias_map: dict[str, str]) -> tuple[float, str | None]:
    required_compact = _compact(required)
    for term in context_terms:
        normalized = _canon(term, alias_map)
        if _variant_match(required, normalized) or _token_score(required, normalized) > 0:
            return CONTEXT_CREDIT, normalized
        text = " " + normalize_skill_key(term) + " "
        if f" {required} " in text or (required_compact and required_compact in _compact(term)):
            return CONTEXT_CREDIT, normalize_skill_key(term)
    return 0.0, None


def _severity(score: float) -> str:
    if score >= FULL_CREDIT:
        return "matched"
    if score >= TOKEN_CREDIT:
        return "low"
    if score > 0:
        return "medium"
    return "high"


def align_skills(
    required_skills: Iterable[str],
    evidence: SkillEvidence,
    alias_map: dict[str, str] | None = None,
    skill_weights: dict[str, float] | None = None,
    skill_domains: dict[str, str] | None = None,
) -> SkillAlignment:
    """skill_weights maps canonical skill keys to a 0-1 importance score, and
    skill_domains maps them to an industry-category label (e.g. "Backend") -
    both sourced from career_roles.sort_skills. When skill_weights is given,
    coverage is importance-weighted and each skill_gap gets an `importance`
    tier instead of every skill counting equally; skill_domains (if given)
    attaches a `domain` to each gap for domain-level grouping downstream."""
    aliases = clean_alias_map(alias_map or {})
    required = _dedupe(_canon(skill, aliases) for skill in required_skills)
    if not required:
        return SkillAlignment(coverage=0.0, matched_skills=[], missing_skills=[], skill_gaps=[])

    weights = {_canon(skill, aliases): weight for skill, weight in (skill_weights or {}).items()}
    domains = {_canon(skill, aliases): domain for skill, domain in (skill_domains or {}).items()}

    explicit = _dedupe(_canon(skill, aliases) for skill in evidence.explicit_terms)
    matched: list[str] = []
    missing: list[str] = []
    gaps: list[dict[str, Any]] = []
    weighted_score_sum = 0.0
    weight_sum = 0.0
    domain_totals: dict[str, float] = {}
    domain_counts: dict[str, int] = {}
    domain_skills: dict[str, list[str]] = {}

    for required_skill in required:
        score, closest = _best_score(required_skill, explicit, aliases)
        if score == 0:
            score, closest = _context_score(required_skill, evidence.context_terms, aliases)

        weight = weights.get(required_skill, DEFAULT_SKILL_WEIGHT if weights else 1.0)
        weighted_score_sum += score * weight
        weight_sum += weight

        # Group by the domain label exactly as given (no canonicalization) so
        # display text matches what the LLM produced; skills without a domain
        # (role never reprocessed with the hierarchy prompt) fall back to
        # being their own pseudo-domain, same as career_path's top-gap grouping.
        domain = domains.get(required_skill) or required_skill
        domain_totals[domain] = domain_totals.get(domain, 0.0) + score
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
        domain_skills.setdefault(domain, []).append(required_skill)

        if score >= TOKEN_CREDIT:
            matched.append(required_skill)
        if score == 0:
            missing.append(required_skill)
        if score < FULL_CREDIT:
            gaps.append(
                {
                    "required_skill": required_skill,
                    "user_closest_skill": closest,
                    "transferability": score,
                    "severity": _severity(score),
                    "importance": skill_importance_tier(weights.get(required_skill)),
                    "domain": domains.get(required_skill, ""),
                }
            )

    gaps.sort(key=lambda gap: (_IMPORTANCE_RANK.get(gap["importance"], 3), gap["transferability"]))

    domain_scores = {
        domain: round(total / domain_counts[domain], 4) for domain, total in domain_totals.items()
    }

    return SkillAlignment(
        coverage=weighted_score_sum / weight_sum if weight_sum else 0.0,
        matched_skills=matched,
        missing_skills=missing,
        skill_gaps=gaps,
        domain_scores=domain_scores,
        domain_skills=domain_skills,
    )
