from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.features.cv_parsing.schemas import CVData


# ---------------------------------------------------------------------------
# Job dataset schema
# ---------------------------------------------------------------------------

class JobRecord(BaseModel):
    """Normalised job posting as stored in job_postings table."""
    job_id: str
    jobtitle: str
    description: Optional[str] = None
    essential_skills: list[str] = Field(default_factory=list)
    raw_text: str = ""


# ---------------------------------------------------------------------------
# Gap analysis
# ---------------------------------------------------------------------------

class SkillGap(BaseModel):
    framework: str
    required_skill: str
    user_closest_skill: Optional[str] = None
    transferability: float = 0.0
    severity: Literal["matched", "low", "medium", "high"] = "high"


class GapAnalysis(BaseModel):
    matched_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    match_coverage: float = 0.0   # fraction of job skills covered by user


# ---------------------------------------------------------------------------
# Role match result
# ---------------------------------------------------------------------------

class RoleMatch(BaseModel):
    job_id: str
    jobtitle: str
    description: Optional[str] = None
    essential_skills: list[str] = Field(default_factory=list)
    similarity_score: float        # dense cosine similarity
    interest_score: float = 0.0
    rerank_score: float = 0.0
    final_score: float = 0.0
    gap_analysis: Optional[GapAnalysis] = None


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------

class RoleMatchRequest(BaseModel):
    cv_data: CVData
    top_k: int = Field(default=5, ge=1, le=20)


class RoleMatchResponse(BaseModel):
    query_text: str
    matched_roles: list[RoleMatch]
    analysis: Optional[str] = None
