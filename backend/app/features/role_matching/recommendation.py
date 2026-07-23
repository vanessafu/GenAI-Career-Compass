from dataclasses import dataclass, field
from typing import Union

from .normalization import SENIORITY_ALIASES, SENIORITY_ORDER, normalize_skill_key
from .schemas import (
    BucketedRoles,
    DEFAULT_WEIGHTS,
    RecommendationBucket,
    RoleMatch,
    RoleMatchSignalBreakdown,
    ScoringWeights,
)

# Seniority modifiers (from the same vocabulary seniority_level_from_title uses
# to *detect* a level) are stripped before comparing job-title tokens, so
# "Senior Data Analyst" and "Data Analyst" read as the same role core - the
# seniority difference is already captured by seniority_fit, and it's exactly
# these level-only variants that were slipping through MMR as "diverse".
_SENIORITY_TITLE_TOKENS = frozenset(SENIORITY_ORDER) | frozenset(
    alias for alias in SENIORITY_ALIASES if " " not in alias
)


# _effective_domain_overlap thresholds: how much skill overlap a candidate needs
# before its domain/interest enthusiasm is allowed to count at full weight.
NEXT_STEP_SKILL_OVERLAP = 0.35
STRETCH_MIN_SKILL_OVERLAP = 0.20

# MMR (Maximal Marginal Relevance) trade-off, applied to every bucket's
# selection: 0.7 relevance / 0.3 diversity - keeps picks mostly about fit,
# but meaningfully discounts near-duplicates of what's already selected.
MMR_LAMBDA = 0.7

_BUCKET_ORDER = (
    RecommendationBucket.READY_NOW,
    RecommendationBucket.NEXT_STEP,
    RecommendationBucket.ASPIRATIONAL,
)


@dataclass
class Candidate:
    role_id: Union[str, int]
    job_title: str
    description: str = ""
    salary: str = ""
    esco_title: str = ""
    esco_uri: str = ""
    required_skills: list[str] = field(default_factory=list)
    domain_tags: list[str] = field(default_factory=list)
    role_certifications: list[str] = field(default_factory=list)
    capability_vector_similarity: float = 0.0
    intent_vector_similarity: float = 0.0
    identity_vector_similarity: float = 0.0
    normalized_skill_overlap: float = 0.0
    interest_domain_overlap: float = 0.0
    skill_overlap: float | None = None
    domain_overlap: float | None = None
    certification_overlap: float = 0.0
    seniority_fit: float = 0.0
    seniority_gap: str = "unknown"
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)
    matched_domains: list[str] = field(default_factory=list)
    matched_certifications: list[str] = field(default_factory=list)
    final_score: float = 0.0
    bucket: RecommendationBucket = RecommendationBucket.ASPIRATIONAL

    def __post_init__(self) -> None:
        self.description = self.description or ""
        if self.skill_overlap is not None:
            self.normalized_skill_overlap = self.skill_overlap
        if self.domain_overlap is not None:
            self.interest_domain_overlap = self.domain_overlap


def _clamp01(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _effective_domain_overlap(candidate: Candidate) -> float:
    """Keep domain enthusiasm helpful without letting it dominate thin skills."""
    skill_overlap = _clamp01(candidate.normalized_skill_overlap)
    domain_overlap = _clamp01(candidate.interest_domain_overlap)
    if skill_overlap >= NEXT_STEP_SKILL_OVERLAP:
        return domain_overlap
    if skill_overlap >= STRETCH_MIN_SKILL_OVERLAP:
        return min(domain_overlap, 0.50)
    return min(domain_overlap, 0.25)


def score_candidate(candidate: Candidate, weights: ScoringWeights) -> float:
    weighted_score = (
        weights.capability_vector_similarity * _clamp01(candidate.capability_vector_similarity)
        + weights.intent_vector_similarity * _clamp01(candidate.intent_vector_similarity)
        + weights.identity_vector_similarity * _clamp01(candidate.identity_vector_similarity)
        + weights.normalized_skill_overlap * _clamp01(candidate.normalized_skill_overlap)
        + weights.interest_domain_overlap * _effective_domain_overlap(candidate)
        + weights.seniority_fit * _clamp01(candidate.seniority_fit)
    )
    weight_total = sum(
        (
            weights.capability_vector_similarity,
            weights.intent_vector_similarity,
            weights.identity_vector_similarity,
            weights.normalized_skill_overlap,
            weights.interest_domain_overlap,
            weights.seniority_fit,
        )
    )
    return weighted_score / weight_total if weight_total > 0 else 0.0


def assign_bucket(candidate: Candidate) -> RecommendationBucket:
    """Assign an honest readiness bucket from current capability evidence."""
    final_score = candidate.final_score
    skill_overlap = _clamp01(candidate.normalized_skill_overlap)
    capability = _clamp01(candidate.capability_vector_similarity)
    identity = _clamp01(candidate.identity_vector_similarity)
    direction_signal = max(
        _clamp01(candidate.intent_vector_similarity),
        identity,
        _effective_domain_overlap(candidate),
    )

    if candidate.seniority_gap == "stretch":
        bucket = (
            RecommendationBucket.NEXT_STEP
            if candidate.seniority_fit >= 0.55
            and final_score >= 0.50
            and skill_overlap >= 0.20
            else RecommendationBucket.ASPIRATIONAL
        )
        return bucket

    high_semantic_ready = (
        capability >= 0.70
        and identity >= 0.57
        and _clamp01(candidate.interest_domain_overlap) >= 0.50
    )
    if (
        (final_score >= 0.58 and skill_overlap >= 0.45)
        or (
            candidate.seniority_gap == "match"
            and skill_overlap >= 0.25
            and final_score >= 0.50
        )
        or (high_semantic_ready and final_score >= 0.48)
    ):
        return RecommendationBucket.READY_NOW

    if (
        final_score >= 0.48
        and capability >= 0.50
        and skill_overlap >= 0.20
        and direction_signal >= 0.52
    ):
        return RecommendationBucket.NEXT_STEP

    return RecommendationBucket.ASPIRATIONAL

def _title_tokens(candidate: Candidate) -> set[str]:
    tokens = normalize_skill_key(candidate.job_title).split()
    return {token for token in tokens if token not in _SENIORITY_TITLE_TOKENS}


def _jaccard(sa: set[str], sb: set[str]) -> float:
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _role_similarity(a: Candidate, b: Candidate) -> float:
    """Redundancy signal for MMR: the higher of (1) Jaccard over required_skills
    + domain_tags (already normalize_skill_key'd upstream) and (2) Jaccard over
    job-title tokens (seniority words stripped). Two postings with near-identical
    titles but differently-listed skills - the common case for duplicate/near-
    duplicate job ads - are exactly what (1) alone was missing, so the max of
    the two keeps either signal from masking the other."""

    def skill_domain_tokens(candidate: Candidate) -> set[str]:
        return {s.casefold() for s in (*candidate.required_skills, *candidate.domain_tags)}

    skill_sim = _jaccard(skill_domain_tokens(a), skill_domain_tokens(b))
    title_sim = _jaccard(_title_tokens(a), _title_tokens(b))
    return max(skill_sim, title_sim)


def _mmr_select(
    candidates: list[Candidate], k: int, lambda_: float = MMR_LAMBDA
) -> list[Candidate]:
    """Maximal Marginal Relevance: iteratively pick the candidate maximizing
    lambda_ * relevance - (1 - lambda_) * max_similarity_to_already_selected.
    Relevance = final_score, the same number used for display everywhere
    else. Front-loads a relevance/diversity trade-off, so callers should treat
    the returned order as final display order, not re-sort it."""
    if k <= 0 or not candidates:
        return []
    pool = sorted(candidates, key=lambda c: c.final_score, reverse=True)
    selected = [pool.pop(0)]
    while pool and len(selected) < k:

        def mmr_key(candidate: Candidate) -> float:
            redundancy = max(_role_similarity(candidate, s) for s in selected)
            return lambda_ * candidate.final_score - (1 - lambda_) * redundancy

        pool.sort(key=mmr_key, reverse=True)
        selected.append(pool.pop(0))
    return selected


def _to_match(candidate: Candidate) -> RoleMatch:
    return RoleMatch(
        role_id=candidate.role_id,
        job_title=candidate.job_title,
        description=candidate.description or "",
        final_score=round(candidate.final_score, 4),
        salary=candidate.salary or "",
        esco_title=candidate.esco_title or "",
        esco_uri=candidate.esco_uri or "",
        bucket=candidate.bucket,
        matched_skills=candidate.matched_skills,
        missing_skills=candidate.missing_skills,
        matched_domains=candidate.matched_domains,
        matched_certifications=candidate.matched_certifications,
        signal_breakdown=RoleMatchSignalBreakdown(
            capability_vector_similarity=round(_clamp01(candidate.capability_vector_similarity), 4),
            intent_vector_similarity=round(_clamp01(candidate.intent_vector_similarity), 4),
            identity_vector_similarity=round(_clamp01(candidate.identity_vector_similarity), 4),
            normalized_skill_overlap=round(_clamp01(candidate.normalized_skill_overlap), 4),
            interest_domain_overlap=round(_clamp01(candidate.interest_domain_overlap), 4),
            certification_overlap=round(_clamp01(candidate.certification_overlap), 4),
            seniority_fit=round(_clamp01(candidate.seniority_fit), 4),
            seniority_gap=candidate.seniority_gap,
        ),
    )


def _balanced_bucket_selection(
    grouped: dict[RecommendationBucket, list[Candidate]],
    total: int,
) -> dict[RecommendationBucket, list[Candidate]]:
    selected: dict[RecommendationBucket, list[Candidate]] = {
        RecommendationBucket.READY_NOW: [],
        RecommendationBucket.NEXT_STEP: [],
        RecommendationBucket.ASPIRATIONAL: [],
    }
    if total <= 0:
        return selected

    indexes = {bucket: 0 for bucket in _BUCKET_ORDER}
    seen_role_ids: set[str] = set()
    seen_titles: set[str] = set()
    remaining = total

    while remaining > 0:
        progressed = False
        for bucket in _BUCKET_ORDER:
            while indexes[bucket] < len(grouped[bucket]):
                candidate = grouped[bucket][indexes[bucket]]
                indexes[bucket] += 1
                role_id = str(candidate.role_id)
                title = normalize_skill_key(candidate.job_title)
                if role_id in seen_role_ids or (title and title in seen_titles):
                    continue

                selected[bucket].append(candidate)
                seen_role_ids.add(role_id)
                if title:
                    seen_titles.add(title)
                remaining -= 1
                progressed = True
                break

            if remaining <= 0:
                break
        if not progressed:
            break

    return selected

def recommend(candidates: list[Candidate], top_k: int = 9) -> BucketedRoles:
    top_k = max(0, top_k)
    for candidate in candidates:
        candidate.final_score = score_candidate(candidate, DEFAULT_WEIGHTS)
        candidate.bucket = assign_bucket(candidate)

    grouped: dict[RecommendationBucket, list[Candidate]] = {
        bucket: [] for bucket in _BUCKET_ORDER
    }
    for candidate in candidates:
        grouped[candidate.bucket].append(candidate)
    for bucket, bucket_candidates in grouped.items():
        bucket_candidates.sort(key=lambda item: item.final_score, reverse=True)
        grouped[bucket] = _mmr_select(bucket_candidates, min(top_k, len(bucket_candidates)))

    selected = _balanced_bucket_selection(grouped, total=top_k)

    return BucketedRoles(
        ready_now=[_to_match(item) for item in selected[RecommendationBucket.READY_NOW]],
        next_step=[_to_match(item) for item in selected[RecommendationBucket.NEXT_STEP]],
        aspirational=[_to_match(item) for item in selected[RecommendationBucket.ASPIRATIONAL]],
    )