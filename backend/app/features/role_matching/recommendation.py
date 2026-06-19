"""
Recommendation logic (pure functions, no I/O).

Pipeline:  score -> bucket -> diversify (MMR) -> RoleMatch.

Scoring (domain_tags already live inside the role embedding, so sim_interest
captures domain alignment; there is no separate domain term):
    match_score    = w_sim_cv * sim_cv + w_skill_coverage * skill_coverage
    interest_score = sim_interest
    growth_score   = sim_interest * reachability(coverage)   # peaks at a moderate gap
    final_score    = (1 - alpha) * match_score + alpha * interest_score
                     + beta_growth * growth_score

Buckets:
    ready_now    : coverage high, you already fit it          -> ranked by match_score
    next_step    : interest high, gap moderate (reachable)    -> ranked by growth_score
    aspirational : interest high, gap large                   -> ranked by interest_score
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from backend.app.features.role_matching.schemas import (
    BucketedRoles,
    GapAnalysis,
    RecommendationBucket,
    RecommendationMode,
    RoleMatch,
    ScoringWeights,
    weights_for,
)

# --- thresholds---------------------------------------
READY_COVERAGE = 0.70     # coverage >= this -> small gap -> ready_now
MID_COVERAGE = 0.35       # MID..READY -> moderate gap -> next_step ; below -> aspirational
MIN_RELEVANCE = 0.30      # floor on sim_cv before a role can count as "ready"
MIN_INTEREST = 0.30       # floor on sim_interest before surfacing next_step/aspirational
GROWTH_PEAK = 0.50        # coverage at which "reachable stretch" is maximal
MMR_LAMBDA = 0.70         # MMR: relevance vs diversity (1.0 = pure relevance)


@dataclass
class Candidate:
    """One role + its raw signals + (filled later) its scores."""
    role_id: int
    job_title: str
    description: Optional[str]
    essential_skills: list[str]
    domain_tags: Optional[str]
    embedding: np.ndarray           # unit-length role vector (for MMR)
    sim_cv: float
    sim_interest: float
    skill_coverage: float
    gap_analysis: GapAnalysis
    match_score: float = 0.0
    interest_score: float = 0.0
    growth_score: float = 0.0
    final_score: float = 0.0
    bucket: Optional[RecommendationBucket] = None


def _reachability(coverage: float, peak: float = GROWTH_PEAK) -> float:
    """Triangular: 1.0 at `peak`, 0.0 at coverage 0 and at 2*peak. A role is a good
    growth target when it stretches the user but stays within reach."""
    return max(0.0, 1.0 - abs(coverage - peak) / peak)


def score_candidates(cands: list[Candidate], w: ScoringWeights) -> None:
    for c in cands:
        c.match_score = w.w_sim_cv * c.sim_cv + w.w_skill_coverage * c.skill_coverage
        c.interest_score = c.sim_interest
        c.growth_score = c.sim_interest * _reachability(c.skill_coverage)
        base = (1.0 - w.alpha) * c.match_score + w.alpha * c.interest_score
        c.final_score = base + w.beta_growth * c.growth_score


def assign_bucket(c: Candidate) -> Optional[RecommendationBucket]:
    # Ready now: skills already fit AND the role is actually relevant to the CV
    if c.skill_coverage >= READY_COVERAGE and c.sim_cv >= MIN_RELEVANCE:
        return RecommendationBucket.ready_now
    # Everything else must be something the user actually wants
    if c.sim_interest < MIN_INTEREST:
        return None  # not ready and not wanted -> drop
    if c.skill_coverage >= MID_COVERAGE:
        return RecommendationBucket.next_step
    return RecommendationBucket.aspirational


def _mmr(cands: list[Candidate], k: int, relevance_attr: str, lam: float = MMR_LAMBDA) -> list[Candidate]:
    """Maximal Marginal Relevance: pick high-scoring roles that are not near-duplicates
    of ones already picked (cosine over role embeddings). Spreads results across the
    user's interest space instead of ten near-identical DevOps roles."""
    pool = list(cands)
    selected: list[Candidate] = []
    while pool and len(selected) < k:
        if not selected:
            best = max(pool, key=lambda c: getattr(c, relevance_attr))
        else:
            def mmr_score(c: Candidate) -> float:
                rel = getattr(c, relevance_attr)
                redundancy = max(float(np.dot(c.embedding, s.embedding)) for s in selected)
                return lam * rel - (1.0 - lam) * redundancy
            best = max(pool, key=mmr_score)
        selected.append(best)
        pool.remove(best)
    return selected


def _to_match(c: Candidate) -> RoleMatch:
    r = lambda x: round(float(x), 4)  # noqa: E731
    return RoleMatch(
        role_id=c.role_id,
        job_title=c.job_title,
        description=c.description,
        essential_skills=c.essential_skills,
        sim_cv=r(c.sim_cv),
        sim_interest=r(c.sim_interest),
        skill_coverage=r(c.skill_coverage),
        match_score=r(c.match_score),
        interest_score=r(c.interest_score),
        growth_score=r(c.growth_score),
        final_score=r(c.final_score),
        bucket=c.bucket,
        gap_analysis=c.gap_analysis,
    )


def recommend(cands: list[Candidate], mode: RecommendationMode, per_bucket: int = 5) -> BucketedRoles:
    """Score, bucket, diversify. `per_bucket` caps each tier (the request's top_k)."""
    score_candidates(cands, weights_for(mode))

    grouped: dict[RecommendationBucket, list[Candidate]] = {
        RecommendationBucket.ready_now: [],
        RecommendationBucket.next_step: [],
        RecommendationBucket.aspirational: [],
    }
    for c in cands:
        b = assign_bucket(c)
        if b is not None:
            c.bucket = b
            grouped[b].append(c)

    # Each bucket is ranked by its own meaningful metric, then MMR-diversified.
    ready = _mmr(grouped[RecommendationBucket.ready_now], per_bucket, "match_score")
    nxt = _mmr(grouped[RecommendationBucket.next_step], per_bucket, "growth_score")
    asp = _mmr(grouped[RecommendationBucket.aspirational], per_bucket, "interest_score")

    return BucketedRoles(
        ready_now=[_to_match(c) for c in ready],
        next_step=[_to_match(c) for c in nxt],
        aspirational=[_to_match(c) for c in asp],
    )