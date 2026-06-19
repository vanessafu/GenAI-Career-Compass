from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RecommendationMode(str, Enum):
    BALANCED = "balanced"
    GROWTH = "growth"
    SAFE = "safe"
    balanced = "balanced"
    growth = "growth"
    safe = "safe"


class RecommendationBucket(str, Enum):
    READY_NOW = "ready_now"
    NEXT_STEP = "next_step"
    ASPIRATIONAL = "aspirational"
    ready_now = "ready_now"
    next_step = "next_step"
    aspirational = "aspirational"


DimensionStatus = Literal["strong", "partial", "weak"]


class ScoringWeights(BaseModel):
    capability_vector_similarity: float = 0.25
    intent_vector_similarity: float = 0.15
    normalized_skill_overlap: float = 0.30
    interest_domain_overlap: float = 0.15
    certification_overlap: float = 0.10
    seniority_fit: float = 0.05


DEFAULT_WEIGHTS = ScoringWeights()


def _has_text(value: Optional[str]) -> bool:
    return bool(value and value.strip())


def _has_any_text(values: list[str]) -> bool:
    return any(_has_text(value) for value in values)


class CareerIdentity(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None

    @property
    def has_signal(self) -> bool:
        return _has_text(self.title) or _has_text(self.summary)


class UserEducation(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    start_year: Optional[str] = None
    end_year: Optional[str] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text(
            [self.degree or "", self.institution or "", self.start_year or "", self.end_year or ""]
        )


class UserExperience(BaseModel):
    role: Optional[str] = None
    organization: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    summary: Optional[str] = None
    skills: list[str] = Field(default_factory=list)

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
    name: Optional[str] = None
    issuer: Optional[str] = None
    year: Optional[str] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text([self.name or "", self.issuer or "", self.year or ""])


class UserProject(BaseModel):
    title: Optional[str] = None
    summary: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    year: Optional[str] = None

    @property
    def has_signal(self) -> bool:
        return _has_any_text([self.title or "", self.summary or "", self.year or "", *self.technologies])


class UserCareerProfile(BaseModel):
    career_identity: CareerIdentity = Field(default_factory=CareerIdentity)
    education: list[UserEducation] = Field(default_factory=list)
    experience: list[UserExperience] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    certifications: list[UserCertification] = Field(default_factory=list)
    projects: list[UserProject] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_capability_and_intent(self) -> "UserCareerProfile":
        has_capability = (
            any(item.has_signal for item in self.experience)
            or any(item.has_signal for item in self.education)
            or _has_any_text(self.skills)
            or any(item.has_signal for item in self.certifications)
            or any(item.has_signal for item in self.projects)
        )
        has_intent = self.career_identity.has_signal or _has_any_text(self.interests)

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
    bucket: str
    title: str
    matching_score: int = Field(ge=0, le=100)
    salary: str = ""
    description: str = ""

    @classmethod
    def from_role_match(cls, role: RoleMatch) -> "CareerResultV1":
        score = max(0.0, min(1.0, role.final_score))
        return cls(
            bucket=role.bucket.value,
            title=role.job_title,
            matching_score=int(round(score * 100)),
            salary=role.salary,
            description=role.description,
        )


class CareerResultsV1(BaseModel):
    results: list[CareerResultV1] = Field(default_factory=list)

    @classmethod
    def from_bucketed_roles(cls, buckets: BucketedRoles) -> "CareerResultsV1":
        roles = [
            *buckets.ready_now,
            *buckets.next_step,
            *buckets.aspirational,
        ]
        return cls(results=[CareerResultV1.from_role_match(role) for role in roles])


class RoleMatchDebug(BaseModel):
    capability_text: str
    intent_text: str
    normalized_user_skills: list[str] = Field(default_factory=list)
    mapped_domains: list[str] = Field(default_factory=list)


class RoleMatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: UserCareerProfile
    top_k: int = Field(default=3, ge=1, le=20)
    mode: RecommendationMode = RecommendationMode.BALANCED
    include_debug: bool = False


class RoleMatchResponse(BaseModel):
    mode: RecommendationMode
    buckets: BucketedRoles
    debug: Optional[RoleMatchDebug] = None


class SkillGap(BaseModel):
    skill: str = ""
    importance: str = ""
    suggestion: str = ""
    required_skill: str = ""
    user_closest_skill: Optional[str] = None
    transferability: float = 0.0
    severity: str = "medium"
    source: str = ""


class GapAnalysis(BaseModel):
    missing_essential: list[SkillGap] = Field(default_factory=list)
    missing_optional: list[SkillGap] = Field(default_factory=list)
    bridge_projects: list[str] = Field(default_factory=list)
    learning_plan: list[str] = Field(default_factory=list)
    estimated_months: int = 0


class SkillDimension(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    optional_missing_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
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
    user_seniority: str = "unknown"
    role_seniority: str = "unknown"
    fit: str = "unknown"
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
    overall_readiness: float = 0.0
    readiness_score: float = 0.0
    bucket: RecommendationBucket = RecommendationBucket.ASPIRATIONAL
    skills: SkillDimension = Field(default_factory=SkillDimension)
    certifications: CertificationDimension = Field(default_factory=CertificationDimension)
    seniority: SeniorityDimension = Field(default_factory=SeniorityDimension)
    grounding_used: list[str] = Field(default_factory=list)
    action_plan: list[GapActionItem] = Field(default_factory=list)
    narrative: Optional[GapNarrative] = None
