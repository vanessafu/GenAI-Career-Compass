from dataclasses import dataclass, field
from typing import Union

from .schemas import (
    BUCKET_WEIGHTS,
    BucketedRoles,
    DEFAULT_WEIGHTS,
    RecommendationBucket,
    RoleMatch,
    RoleMatchSignalBreakdown,
    ScoringWeights,
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
    bucket_score: float = 0.0

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
    return (
        weights.capability_vector_similarity * _clamp01(candidate.capability_vector_similarity)
        + weights.intent_vector_similarity * _clamp01(candidate.intent_vector_similarity)
        + weights.identity_vector_similarity * _clamp01(candidate.identity_vector_similarity)
        + weights.normalized_skill_overlap * _clamp01(candidate.normalized_skill_overlap)
        + weights.interest_domain_overlap * _effective_domain_overlap(candidate)
        + weights.seniority_fit * _clamp01(candidate.seniority_fit)
    )


def _ranked_buckets(candidate: Candidate) -> list[tuple[RecommendationBucket, float]]:
    """Score the candidate under all three bucket weight profiles in parallel,
    ranked best first. The first entry is the candidate's natural (argmax)
    bucket; the rest are fallbacks for when a preferred bucket is already full."""
    bucket_scores = {
        bucket: score_candidate(candidate, weights) for bucket, weights in BUCKET_WEIGHTS.items()
    }
    return sorted(bucket_scores.items(), key=lambda item: item[1], reverse=True)


def assign_bucket(candidate: Candidate) -> tuple[RecommendationBucket, float]:
    """The candidate's single best-scoring bucket (mutually exclusive argmax)."""
    return _ranked_buckets(candidate)[0]


def _role_similarity(a: Candidate, b: Candidate) -> float:
    """Jaccard over each candidate's required_skills + domain_tags (both
    already normalize_skill_key'd upstream) - the redundancy signal for MMR."""

    def tokens(candidate: Candidate) -> set[str]:
        return {s.casefold() for s in (*candidate.required_skills, *candidate.domain_tags)}

    sa, sb = tokens(a), tokens(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


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


def _backfill_underfilled_buckets(
    grouped: dict[RecommendationBucket, list[Candidate]],
    quota: int,
) -> dict[RecommendationBucket, list[Candidate]]:
    """Each bucket first keeps up to `quota` of its own natural (argmax)
    candidates, chosen via MMR (relevance + diversity) so a bucket doesn't
    fill up with near-duplicate roles. Any bucket left short is topped up
    from the genuine overflow of the other buckets - candidates who lost
    the cut in their own best bucket - ranked by how well they'd fit the
    short bucket specifically. This never displaces a candidate who already
    earned a spot in their own best-fit bucket; it only reuses real
    leftovers to avoid an empty section."""
    if quota <= 0:
        return {bucket: [] for bucket in _BUCKET_ORDER}

    kept: dict[RecommendationBucket, list[Candidate]] = {}
    overflow: list[Candidate] = []
    for bucket in _BUCKET_ORDER:
        bucket_candidates = grouped[bucket]
        kept[bucket] = _mmr_select(bucket_candidates, quota)
        kept_ids = {id(c) for c in kept[bucket]}
        overflow.extend(c for c in bucket_candidates if id(c) not in kept_ids)

    for bucket in _BUCKET_ORDER:
        shortfall = quota - len(kept[bucket])
        if shortfall <= 0 or not overflow:
            continue
        weights = BUCKET_WEIGHTS[bucket]
        overflow.sort(key=lambda candidate: score_candidate(candidate, weights), reverse=True)
        fill, overflow = overflow[:shortfall], overflow[shortfall:]
        for candidate in fill:
            candidate.bucket = bucket
            candidate.bucket_score = score_candidate(candidate, weights)
        # Preserve the MMR order already decided for `kept`; only the
        # appended fill (rare: the bucket's natural pool undershot quota)
        # gets sorted by final_score, so a resort never undoes MMR's
        # relevance/diversity trade-off for the roles it actually picked.
        fill.sort(key=lambda item: item.final_score, reverse=True)
        kept[bucket] = kept[bucket] + fill

    return kept


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
    per_bucket: int | None = None,
) -> BucketedRoles:
    if top_k is None and per_bucket is None:
        top_k = 9

    for candidate in candidates:
        candidate.bucket, candidate.bucket_score = assign_bucket(candidate)
        candidate.final_score = score_candidate(candidate, DEFAULT_WEIGHTS)

    grouped: dict[RecommendationBucket, list[Candidate]] = {bucket: [] for bucket in _BUCKET_ORDER}
    for candidate in candidates:
        grouped[candidate.bucket].append(candidate)
    for bucket_candidates in grouped.values():
        bucket_candidates.sort(key=lambda item: item.final_score, reverse=True)

    quota = per_bucket if per_bucket is not None else top_k
    grouped = _backfill_underfilled_buckets(grouped, quota or 0)

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
