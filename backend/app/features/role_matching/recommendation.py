from dataclasses import dataclass, field
from typing import Union

from .schemas import (
    BucketedRoles,
    DEFAULT_WEIGHTS,
    RecommendationBucket,
    RecommendationMode,
    RoleMatch,
    RoleMatchSignalBreakdown,
)


READY_NOW_SKILL_OVERLAP = 0.60
NEXT_STEP_SKILL_OVERLAP = 0.35
STRETCH_MIN_SKILL_OVERLAP = 0.20
STRONG_DOMAIN_OVERLAP = 0.50
MIN_CAPABILITY_FOR_READY_NOW = 0.68
MIN_CAPABILITY_FOR_DOMAIN_STRETCH = 0.50
STRONG_CERTIFICATION_OVERLAP = 0.50

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


def score_candidate(candidate: Candidate) -> float:
    weights = DEFAULT_WEIGHTS
    return (
        weights.capability_vector_similarity * _clamp01(candidate.capability_vector_similarity)
        + weights.intent_vector_similarity * _clamp01(candidate.intent_vector_similarity)
        + weights.normalized_skill_overlap * _clamp01(candidate.normalized_skill_overlap)
        + weights.interest_domain_overlap * _effective_domain_overlap(candidate)
        + weights.certification_overlap * _clamp01(candidate.certification_overlap)
        + weights.seniority_fit * _clamp01(candidate.seniority_fit)
    )


def assign_bucket(candidate: Candidate) -> RecommendationBucket:
    skill_overlap = _clamp01(candidate.normalized_skill_overlap)
    domain_overlap = _clamp01(candidate.interest_domain_overlap)
    cert_overlap = _clamp01(candidate.certification_overlap)
    capability_similarity = _clamp01(candidate.capability_vector_similarity)

    if (
        skill_overlap >= READY_NOW_SKILL_OVERLAP
        and capability_similarity >= MIN_CAPABILITY_FOR_READY_NOW
        and candidate.seniority_gap != "stretch"
    ):
        return RecommendationBucket.READY_NOW

    if candidate.seniority_gap == "stretch" and skill_overlap < NEXT_STEP_SKILL_OVERLAP:
        return RecommendationBucket.ASPIRATIONAL

    if skill_overlap >= NEXT_STEP_SKILL_OVERLAP:
        return RecommendationBucket.NEXT_STEP
    if cert_overlap >= STRONG_CERTIFICATION_OVERLAP and skill_overlap >= STRETCH_MIN_SKILL_OVERLAP:
        return RecommendationBucket.NEXT_STEP
    if (
        skill_overlap >= STRETCH_MIN_SKILL_OVERLAP
        and domain_overlap >= STRONG_DOMAIN_OVERLAP
        and capability_similarity >= MIN_CAPABILITY_FOR_DOMAIN_STRETCH
    ):
        return RecommendationBucket.NEXT_STEP

    return RecommendationBucket.ASPIRATIONAL


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
    remaining = total

    while remaining > 0:
        active_buckets = [
            bucket
            for bucket in _BUCKET_ORDER
            if indexes[bucket] < len(grouped[bucket])
        ]
        if not active_buckets:
            break

        for bucket in active_buckets:
            if remaining <= 0:
                break
            selected[bucket].append(grouped[bucket][indexes[bucket]])
            indexes[bucket] += 1
            remaining -= 1

    return selected


def recommend(
    candidates: list[Candidate],
    top_k: int | None = None,
    mode: RecommendationMode = RecommendationMode.BALANCED,
    per_bucket: int | None = None,
) -> BucketedRoles:
    if top_k is None and per_bucket is None:
        top_k = 6

    for candidate in candidates:
        candidate.final_score = score_candidate(candidate)
        candidate.bucket = assign_bucket(candidate)

    grouped: dict[RecommendationBucket, list[Candidate]] = {
        RecommendationBucket.READY_NOW: [],
        RecommendationBucket.NEXT_STEP: [],
        RecommendationBucket.ASPIRATIONAL: [],
    }
    for candidate in candidates:
        grouped[candidate.bucket].append(candidate)

    for bucket_candidates in grouped.values():
        bucket_candidates.sort(key=lambda item: item.final_score, reverse=True)

    if per_bucket is not None:
        return BucketedRoles(
            ready_now=[
                _to_match(item)
                for item in grouped[RecommendationBucket.READY_NOW][:per_bucket]
            ],
            next_step=[
                _to_match(item)
                for item in grouped[RecommendationBucket.NEXT_STEP][:per_bucket]
            ],
            aspirational=[
                _to_match(item)
                for item in grouped[RecommendationBucket.ASPIRATIONAL][:per_bucket]
            ],
        )

    selected = _balanced_bucket_selection(grouped, total=top_k or 0)

    return BucketedRoles(
        ready_now=[_to_match(item) for item in selected[RecommendationBucket.READY_NOW]],
        next_step=[_to_match(item) for item in selected[RecommendationBucket.NEXT_STEP]],
        aspirational=[_to_match(item) for item in selected[RecommendationBucket.ASPIRATIONAL]],
    )
