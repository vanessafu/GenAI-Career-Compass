from typing import Any

from pydantic import BaseModel, Field


class CareerIdentitySummary(BaseModel):
    """Structured LLM output for the career identity step."""

    label: str
    summary: str


class CareerIdentityGeneration(CareerIdentitySummary):
    """Backward-compatible name for structured identity generation."""


class EmbeddingProfile(BaseModel):
    career_identity_summary: CareerIdentitySummary
    education: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    certifications: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    potential_direction: str = ""
