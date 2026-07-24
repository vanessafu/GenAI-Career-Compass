from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.core.validation import LongText, MAX_ITEMS, ShortText


class RecommendationBucket(str, Enum):
    READY_NOW = "ready_now"
    NEXT_STEP = "next_step"
    ASPIRATIONAL = "aspirational"


DimensionStatus = Literal["strong", "partial", "weak"]


class ScoringWeights(BaseModel):
    capability_vector_similarity: float = 0.20
    intent_vector_similarity: float = 0.10
    identity_vector_similarity: float = 0.30
    normalized_skill_overlap: float = 0.23
    interest_domain_overlap: float = 0.10
    seniority_fit: float = 0.07


# Each bucket is a distinct ranking lens. Every profile sums to 1.0 so its
# score is an honest weighted average in the 0..1 range.
BUCKET_WEIGHTS: dict[RecommendationBucket, ScoringWeights] = {
    RecommendationBucket.READY_NOW: ScoringWeights(
        capability_vector_similarity=0.25,
        intent_vector_similarity=0.08,
        identity_vector_similarity=0.33,
        normalized_skill_overlap=0.20,
        interest_domain_overlap=0.07,
        seniority_fit=0.07,
    ),
    RecommendationBucket.NEXT_STEP: ScoringWeights(
        capability_vector_similarity=0.13,
        intent_vector_similarity=0.25,
        identity_vector_similarity=0.28,
        normalized_skill_overlap=0.13,
        interest_domain_overlap=0.14,
        seniority_fit=0.07,
    ),
    RecommendationBucket.ASPIRATIONAL: ScoringWeights(
        capability_vector_similarity=0.10,
        intent_vector_similarity=0.40,
        identity_vector_similarity=0.20,
        normalized_skill_overlap=0.10,
        interest_domain_overlap=0.15,
        seniority_fit=0.05,
    ),
}


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _display_matching_score(final_score: float) -> int:
    return int(round(_clamp01(final_score) * 100))

def _has_text(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def _has_any_text(values: list[str]) -> bool:
    return any(_has_text(value) for value in values)


class CareerIdentity(BaseModel):
    title: Optional[ShortText] = None
    summary: Optional[LongText] = None

    @property
    def has_signal(self) -> bool:
        return _has_text(self.title) or _has_text(self.summary)


class UserEducation(BaseModel):
    degree: Optional[ShortText] = None
    institution: Optional[ShortText] = None
    start_year: Optional[ShortText] = None
    end_year: Optional[ShortText] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text(
            [self.degree or "", self.institution or "", self.start_year or "", self.end_year or ""]
        )


class UserExperience(BaseModel):
    role: Optional[ShortText] = None
    organization: Optional[ShortText] = None
    start_date: Optional[ShortText] = None
    end_date: Optional[ShortText] = None
    summary: Optional[LongText] = None
    skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)

    @property
    def has_signal(self) -> bool:
        return _has_any_text(
            [
                self.role or "",
                self.organization or "",
                self.start_date or "",
                self.end_date or "",
                self.summary or "",
                *self.skills,
            ]
        )


class UserCertification(BaseModel):
    name: Optional[ShortText] = None
    issuer: Optional[ShortText] = None
    year: Optional[ShortText] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text([self.name or "", self.issuer or "", self.year or ""])


class UserProject(BaseModel):
    title: Optional[ShortText] = None
    summary: Optional[LongText] = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    year: Optional[ShortText] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text([self.title or "", self.summary or "", self.year or "", *self.technologies])


class UserCareerProfile(BaseModel):
    career_identity: CareerIdentity = Field(default_factory=CareerIdentity)
    education: list[UserEducation] = Field(default_factory=list, max_length=MAX_ITEMS)
    experience: list[UserExperience] = Field(default_factory=list, max_length=MAX_ITEMS)
    skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    interests: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    certifications: list[UserCertification] = Field(default_factory=list, max_length=MAX_ITEMS)
    projects: list[UserProject] = Field(default_factory=list, max_length=MAX_ITEMS)
    potential_direction: LongText = ""

    @model_validator(mode="after")
    def require_capability_and_intent(self) -> "UserCareerProfile":
        has_capability = (
            any(item.has_signal for item in self.experience)
            or any(item.has_signal for item in self.education)
            or _has_any_text(self.skills)
            or any(item.has_signal for item in self.certifications)
            or any(item.has_signal for item in self.projects)
        )
        has_intent = (
            self.career_identity.has_signal
            or _has_any_text(self.interests)
            or _has_text(self.potential_direction)
        )

        if not has_capability and not has_intent:
            raise ValueError("Profile must include at least one capability signal and one intent signal.")
        if not has_capability:
            raise ValueError(
                "Profile must include at least one capability signal from experience, education, "
                "skills, certifications, or projects."
            )
        if not has_intent:
            raise ValueError("Profile must include at least one intent signal from career identity or interests.")
        return self

class RoleMatchSignalBreakdown(BaseModel):
    capability_vector_similarity: float = 0.0
    intent_vector_similarity: float = 0.0
    identity_vector_similarity: float = 0.0
    normalized_skill_overlap: float = 0.0
    interest_domain_overlap: float = 0.0
    certification_overlap: float = 0.0
    seniority_fit: float = 0.0
    seniority_gap: str = "unknown"


class RoleMatch(BaseModel):
    role_id: str | int
    job_title: str
    description: str = ""
    final_score: float
    salary: str = ""
    esco_title: str = ""
    esco_uri: str = ""
    bucket: RecommendationBucket
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matched_domains: list[str] = Field(default_factory=list)
    matched_certifications: list[str] = Field(default_factory=list)
    signal_breakdown: RoleMatchSignalBreakdown


class BucketedRoles(BaseModel):
    ready_now: list[RoleMatch] = Field(default_factory=list)
    next_step: list[RoleMatch] = Field(default_factory=list)
    aspirational: list[RoleMatch] = Field(default_factory=list)


class CareerResultV1(BaseModel):
    role_id: str | int
    bucket: str
    title: str
    matching_score: int = Field(
        ge=0,
        le=100,
        description="Percentage score under the role's assigned recommendation lens.",
    )
    salary: str = ""
    description: str = ""
    esco_title: str = ""
    esco_uri: str = ""
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    matched_domains: list[str] = Field(default_factory=list)
    matched_certifications: list[str] = Field(default_factory=list)

    @classmethod
    def from_role_match(cls, role: RoleMatch) -> "CareerResultV1":
        return cls(
            role_id=role.role_id,
            bucket=role.bucket.value,
            title=role.job_title,
            matching_score=_display_matching_score(role.final_score),
            salary=role.salary,
            description=role.description,
            esco_title=role.esco_title,
            esco_uri=role.esco_uri,
            matched_skills=role.matched_skills,
            missing_skills=role.missing_skills,
            matched_domains=role.matched_domains,
            matched_certifications=role.matched_certifications,
        )


class CareerResultsV1(BaseModel):
    results: list[CareerResultV1] = Field(default_factory=list)

    @classmethod
    def from_bucketed_roles(cls, buckets: BucketedRoles) -> "CareerResultsV1":
        roles = [*buckets.ready_now, *buckets.next_step, *buckets.aspirational]
        return cls(results=[CareerResultV1.from_role_match(role) for role in roles])


class RoleSummaryItem(BaseModel):
    role_id: str
    summary: str = ""


class RoleSummaryBatch(BaseModel):
    summaries: list[RoleSummaryItem] = Field(default_factory=list)


class RoleMatchDebug(BaseModel):
    capability_text: str
    intent_text: str
    normalized_user_skills: list[str] = Field(default_factory=list)
    mapped_domains: list[str] = Field(default_factory=list)


class RoleMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: UserCareerProfile
    top_k: int = Field(default=9, ge=1, le=9)


class RoleMatchResponse(BaseModel):
    buckets: BucketedRoles
    debug: Optional[RoleMatchDebug] = None


class SkillGap(BaseModel):
    skill: str = ""
    importance: str = ""
    domain: str = ""
    suggestion: str = ""
    required_skill: str = ""
    # Properly-cased display text for required_skill (e.g. "UI/UX Design" where
    # required_skill is the normalized matching key "ui ux design") - display
    # only, never used for matching. Falls back to required_skill when no
    # original casing is available.
    display: str = ""
    user_closest_skill: Optional[str] = None
    transferability: float = 0.0
    severity: str = "medium"
    source: str = ""


class ActionableSkillGap(BaseModel):
    skill: str = ""
    display: str = ""
    domain: str = ""
    priority_label: Literal["critical", "high", "medium", "low"] = "medium"
    estimated_effort: Literal["quick_win", "moderate", "substantial"] = "moderate"
    bridge_skill: Optional[str] = None
    why_it_matters: str = ""
    suggested_action: str = ""
    proof_to_build: str = ""
    resume_hint: str = ""


class ActionableSkillGapPolish(BaseModel):
    skill: str = Field(
        default="",
        description="Must exactly match one supplied top_actionable_skill_gaps[].skill value.",
    )
    why_it_matters: str = ""
    suggested_action: str = ""
    proof_to_build: str = ""
    resume_hint: str = ""


class SkillDimension(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    optional_missing_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    domain_coverage: dict[str, float] = Field(default_factory=dict)
    domain_skills: dict[str, list[str]] = Field(default_factory=dict)
    coverage: float = 0.0
    status: DimensionStatus = "weak"
    summary: str = ""


class CertificationGap(BaseModel):
    name: str = ""
    provider: Optional[str] = None
    priority: str = "recommended"
    reason: str = ""
    required_certification: str = ""
    normalized_name: str = ""
    user_closest_certification: Optional[str] = None
    similarity: float = 0.0
    status: str = "missing"


class CertificationDimension(BaseModel):
    matched_certifications: list[str] = Field(default_factory=list)
    missing_certifications: list[CertificationGap] = Field(default_factory=list)
    held: list[str] = Field(default_factory=list)
    related: list[CertificationGap] = Field(default_factory=list)
    missing: list[CertificationGap] = Field(default_factory=list)
    coverage: float = 0.0
    status: DimensionStatus = "weak"
    summary: str = ""


class SeniorityDimension(BaseModel):
    user_level: Optional[str] = None
    role_level: Optional[str] = None
    user_years: Optional[int] = None
    gap: str = "unknown"
    note: Optional[str] = None
    summary: str = ""


class GapActionItem(BaseModel):
    title: str
    description: str
    effort: str = "medium"
    priority: str = "medium"


class GapNarrative(BaseModel):
    readiness_summary: str = ""
    why_this_role: str = ""
    main_gaps: str = ""
    next_steps: str = ""


class GapReport(BaseModel):
    role_id: str | int
    job_title: str
    job_description: Optional[str] = None
    domain_tags: list[str] = Field(default_factory=list)
    overall_readiness: float = 0.0
    readiness_score: float = 0.0
    bucket: RecommendationBucket = RecommendationBucket.ASPIRATIONAL
    skills: SkillDimension = Field(default_factory=SkillDimension)
    certifications: CertificationDimension = Field(default_factory=CertificationDimension)
    seniority: SeniorityDimension = Field(default_factory=SeniorityDimension)
    grounding_used: list[str] = Field(default_factory=list)
    action_plan: list[GapActionItem] = Field(default_factory=list)
    top_actionable_skill_gaps: list[ActionableSkillGap] = Field(default_factory=list)
    narrative: Optional[GapNarrative] = None


MilestoneKind = Literal["role", "skill", "project", "certification", "experience"]


class CareerPathMilestone(BaseModel):
    order: int = Field(ge=1)
    kind: MilestoneKind = "skill"
    title: str
    timeline: str = Field(
        default="",
        pattern=r"^$|^\s*\d+\s+(weeks?|months?)\s*$",
        description=(
            "Exact milestone duration only, for example '3 weeks' or '2 months'. "
            "No ranges, cumulative windows, plus signs, or vague text."
        ),
    )
    rationale: str = ""
    skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)


class CareerPathDraft(BaseModel):
    plan_summary: str = Field(
        default="",
        description=(
            "Two to three concise user-facing sentences summarizing readiness, matched skills, "
            "and main gaps. Do not relist the profile, milestones, or certifications."
        ),
    )
    milestones: list[CareerPathMilestone] = Field(default_factory=list)
    recommended_projects: list[str] = Field(default_factory=list)
    estimated_timeline: str = ""
    certifications: list[str] = Field(default_factory=list)


class CareerPathLLMDraft(CareerPathDraft):
    top_skill_gap_suggestions: list[ActionableSkillGapPolish] = Field(
        default_factory=list,
        description=(
            "Optional wording polish for supplied top_actionable_skill_gaps only. "
            "Do not add, remove, or reorder gaps."
        ),
    )


class CareerPathReport(CareerPathDraft):
    role_id: str | int
    current_profile_summary: str
    target_role: str
    readiness_score: float = 0.0
    top_gaps: list[str] = Field(default_factory=list)
    skills_to_learn: list[str] = Field(default_factory=list)
    requirement_breakdown: GapReport
