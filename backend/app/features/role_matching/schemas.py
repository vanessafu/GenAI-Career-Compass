"""
Role-matching stage schemas. All Pydantic models live here.

Two signals describe the user and they are embedded SEPARATELY:
  - confirmed_profile -> v_cv       (current capabilities: skills, experience, seniority)
  - identity          -> v_interest (direction: identity statement, interests, target dirs)

Scoring:
  match_score    = w_sim_cv * sim_cv + w_skill_coverage * skill_coverage
  interest_score = sim_interest
  final          = (1 - alpha) * match_score + alpha * interest_score
                   + beta_growth * growth_score
"""
from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.features.cv_confirmation.schemas import ConfirmedCVData


# ---------------------------------------------------------------------------
# Enums & recommendation modes
# ---------------------------------------------------------------------------

class RecommendationMode(str, Enum):
    focused = "focused"          # prioritise roles you already fit
    balanced = "balanced"        # default mix
    exploratory = "exploratory"  # prioritise interest + growth


class RecommendationBucket(str, Enum):
    ready_now = "ready_now"        # high match, small gap
    next_step = "next_step"        # high interest, moderate gap
    aspirational = "aspirational"  # high interest, large gap


class ScoringWeights(BaseModel):
    w_sim_cv: float = 0.65
    w_skill_coverage: float = 0.35
    alpha: float = 0.5
    beta_growth: float = 0.2


MODE_WEIGHTS: dict[RecommendationMode, ScoringWeights] = {
    RecommendationMode.focused:     ScoringWeights(alpha=0.25, beta_growth=0.10),
    RecommendationMode.balanced:    ScoringWeights(alpha=0.50, beta_growth=0.20),
    RecommendationMode.exploratory: ScoringWeights(alpha=0.75, beta_growth=0.35),
}


def weights_for(mode: RecommendationMode) -> ScoringWeights:
    return MODE_WEIGHTS[mode]


# ---------------------------------------------------------------------------
# User-facing input models
# ---------------------------------------------------------------------------

class UserIdentity(BaseModel):
    """The interest / direction side of the user (feeds v_interest)."""
    career_identity_statement: str
    career_directions: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class JobRecord(BaseModel):
    """A role row as stored in career_roles (internal representation)."""
    role_id: int
    job_title: str
    job_description: Optional[str] = None
    raw_skills: Optional[str] = None
    domain_tags: Optional[str] = None


# ---------------------------------------------------------------------------
# Skill gap models (shared by role-match scoring and deep gap analysis)
# ---------------------------------------------------------------------------

Severity = Literal["matched", "low", "medium", "high"]


class SkillGap(BaseModel):
    required_skill: str
    user_closest_skill: Optional[str] = None
    transferability: float = 0.0
    severity: Severity = "high"
    source: str = "MIND"


class GapAnalysis(BaseModel):
    """Lightweight skill gap summary attached to each RoleMatch (for scoring)."""
    matched_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    required_count: int = 0
    coverage: float = 0.0


# ---------------------------------------------------------------------------
# Role match result models
# ---------------------------------------------------------------------------

class RoleMatch(BaseModel):
    role_id: int
    job_title: str
    description: Optional[str] = None
    essential_skills: list[str] = Field(default_factory=list)

    sim_cv: float = 0.0
    sim_interest: float = 0.0
    skill_coverage: float = 0.0
    match_score: float = 0.0
    interest_score: float = 0.0
    growth_score: float = 0.0
    final_score: float = 0.0
    bucket: Optional[RecommendationBucket] = None

    gap_analysis: Optional[GapAnalysis] = None


class BucketedRoles(BaseModel):
    ready_now: list[RoleMatch] = Field(default_factory=list)
    next_step: list[RoleMatch] = Field(default_factory=list)
    aspirational: list[RoleMatch] = Field(default_factory=list)


class RoleMatchRequest(BaseModel):
    confirmed_profile: ConfirmedCVData
    identity: UserIdentity
    top_k: int = Field(default=2, ge=1, le=20)
    mode: RecommendationMode = RecommendationMode.balanced


class RoleMatchResponse(BaseModel):
    mode: RecommendationMode
    cv_query_text: str
    interest_query_text: str
    career_directions: list[str] = Field(default_factory=list)
    buckets: BucketedRoles


# ---------------------------------------------------------------------------
# Deep gap analysis models (full multi-dimensional report)
# ---------------------------------------------------------------------------

DimensionStatus = Literal["strong", "partial", "weak"]


class SkillDimension(BaseModel):
    """Skill dimension of a GapReport (richer than GapAnalysis: includes status)."""
    matched_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    coverage: float = 0.0
    status: DimensionStatus = "weak"


class CertificationGap(BaseModel):
    required_certification: str
    normalized_name: str
    user_closest_certification: Optional[str] = None
    similarity: float = 0.0
    status: Literal["held", "related", "missing"] = "missing"


class CertificationDimension(BaseModel):
    held: list[str] = Field(default_factory=list)
    related: list[CertificationGap] = Field(default_factory=list)
    missing: list[CertificationGap] = Field(default_factory=list)
    coverage: float = 0.0
    status: DimensionStatus = "weak"


class SeniorityDimension(BaseModel):
    user_level: Optional[str] = None
    role_level: Optional[str] = None
    user_years: Optional[int] = None
    gap: Literal["under", "match", "over", "unknown"] = "unknown"
    note: Optional[str] = None


class GapActionItem(BaseModel):
    title: str
    dimension: str
    priority: Literal["high", "medium", "low"]
    rationale: str
    suggested_resources: list[str] = Field(default_factory=list)


class GapNarrative(BaseModel):
    summary: str
    prioritized_actions: list[GapActionItem] = Field(default_factory=list)
    estimated_effort: Optional[str] = None


class GapReport(BaseModel):
    role_id: int
    job_title: str
    job_description: Optional[str] = None
    overall_readiness: float = 0.0
    skills: SkillDimension
    certifications: CertificationDimension
    seniority: SeniorityDimension
    grounding_used: list[str] = Field(default_factory=list)
    narrative: Optional[GapNarrative] = None
