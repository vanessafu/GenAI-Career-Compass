from typing import Optional

from pydantic import BaseModel, Field

from backend.app.features.cv_parsing.schemas import CVData


class RoleMatch(BaseModel):
    uri: str
    isco_group: Optional[str] = None
    isco_label: Optional[str] = None
    title: str
    alt_labels: list[str] = Field(default_factory=list)
    description: Optional[str] = None
    essential_knowledge: list[str] = Field(default_factory=list)
    essential_skills: list[str] = Field(default_factory=list)
    optional_knowledge: list[str] = Field(default_factory=list)
    optional_skills: list[str] = Field(default_factory=list)
    similarity_score: float


class RoleMatchRequest(BaseModel):
    cv_data: CVData
    top_k: int = Field(default=5, ge=1, le=20)


class RoleMatchResponse(BaseModel):
    query_text: str
    matched_roles: list[RoleMatch]
    analysis: Optional[str] = None
