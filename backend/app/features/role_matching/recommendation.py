from dataclasses import dataclass, field, replace
from typing import Union

from .normalization import normalize_skill_key
from .schemas import (
    BUCKET_WEIGHTS,
    BucketedRoles,
    RecommendationBucket,
    RoleMatch,
    RoleMatchSignalBreakdown,
    ScoringWeights,
)

# Only true level modifiers are stripped for title deduplication. Role-defining
# words such as architect, manager, director, lead, head, and chief stay.
_TITLE_LEVEL_MODIFIERS = frozenset(
    {"jr", "junior", "mid", "principal", "senior", "snr", "sr", "staff"}
)


# _effective_domain_overlap thresholds: how much skill overlap a candidate needs
# before its domain/interest enthusiasm is allowed to count at full weight.
NEXT_STEP_SKILL_OVERLAP = 0.35
STRETCH_MIN_SKILL_OVERLAP = 0.20


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


def _title_key(candidate: Candidate) -> str:
    tokens = normalize_skill_key(candidate.job_title).split()
    if tokens[:2] == ["entry", "level"]:
        tokens = tokens[2:]
    core = sorted(token for token in tokens if token not in _TITLE_LEVEL_MODIFIERS)
    return " ".join(core) or f"role:{candidate.role_id}"


def _lens_eligible(
    candidate: Candidate,
    bucket: RecommendationBucket,
    lens_score: float,
) -> bool:
    if candidate.seniority_gap != "stretch":
        return True
    if bucket == RecommendationBucket.READY_NOW:
        return False
    if bucket == RecommendationBucket.NEXT_STEP:
        return (
            _clamp01(candidate.seniority_fit) >= 0.55
            and _clamp01(candidate.normalized_skill_overlap) >= STRETCH_MIN_SKILL_OVERLAP
            and lens_score >= 0.50
        )
    return True


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


def _balanced_lens_selection(
    candidates: list[Candidate], total: int
) -> dict[RecommendationBucket, list[Candidate]]:
    selected: dict[RecommendationBucket, list[Candidate]] = {
        RecommendationBucket.READY_NOW: [],
        RecommendationBucket.NEXT_STEP: [],
        RecommendationBucket.ASPIRATIONAL: [],
    }
    if total <= 0:
        return selected

    unique_by_id: dict[str, Candidate] = {}
    for candidate in candidates:
        unique_by_id.setdefault(str(candidate.role_id), candidate)

    groups: dict[str, list[Candidate]] = {}
    for candidate in unique_by_id.values():
        groups.setdefault(_title_key(candidate), []).append(candidate)

    total = min(total, len(groups))
    if total <= 0:
        return selected

    # state -> (sum of assigned lens scores, assigned candidate copies)
    states = {(0, 0, 0): (0.0, ())}
    for title in sorted(groups):
        options: list[tuple[int, Candidate]] = []
        for index, bucket in enumerate(_BUCKET_ORDER):
            scored = [
                (candidate, score_candidate(candidate, BUCKET_WEIGHTS[bucket]))
                for candidate in groups[title]
            ]
            eligible = [
                item for item in scored if _lens_eligible(item[0], bucket, item[1])
            ]
            if not eligible:
                continue
            best, lens_score = max(
                eligible,
                key=lambda item: (item[1], str(item[0].role_id)),
            )
            options.append(
                (
                    index,
                    replace(best, bucket=bucket, final_score=lens_score),
                )
            )

        next_states = dict(states)
        for state, (combined_score, assignment) in states.items():
            if sum(state) >= total:
                continue
            for index, candidate in options:
                new_state = tuple(
                    count + int(position == index)
                    for position, count in enumerate(state)
                )
                new_score = combined_score + candidate.final_score
                previous = next_states.get(new_state)
                if previous is None or new_score > previous[0]:
                    next_states[new_state] = (new_score, assignment + (candidate,))
        states = next_states

    full = [(state, value) for state, value in states.items() if sum(state) == total]
    if not full:
        raise RuntimeError("Unable to allocate the requested role results")
    _, (_, assignment) = max(
        full,
        key=lambda item: (
            -(max(item[0]) - min(item[0])),
            item[1][0],
        ),
    )
    for candidate in assignment:
        selected[candidate.bucket].append(candidate)
    for roles in selected.values():
        roles.sort(
            key=lambda candidate: (candidate.final_score, str(candidate.role_id)), reverse=True
        )
    return selected


def recommend(candidates: list[Candidate], top_k: int = 9) -> BucketedRoles:
    selected = _balanced_lens_selection(candidates, total=max(0, top_k))

    return BucketedRoles(
        ready_now=[_to_match(item) for item in selected[RecommendationBucket.READY_NOW]],
        next_step=[_to_match(item) for item in selected[RecommendationBucket.NEXT_STEP]],
        aspirational=[_to_match(item) for item in selected[RecommendationBucket.ASPIRATIONAL]],
    )