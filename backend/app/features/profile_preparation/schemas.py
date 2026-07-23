from typing import Any

from pydantic import BaseModel, Field

from backend.app.core.validation import LongText, MAX_ITEMS, ShortText


class CareerIdentitySummary(BaseModel):
    """Structured LLM output for the career identity step."""

    label: ShortText
    summary: LongText


class CareerIdentityGeneration(CareerIdentitySummary):
    """Backward-compatible name for structured identity generation."""


class EmbeddingProfile(BaseModel):
    career_identity_summary: CareerIdentitySummary
    education: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_ITEMS)
    experience: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_ITEMS)
    skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    interests: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    certifications: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_ITEMS)
    projects: list[dict[str, Any]] = Field(default_factory=list, max_length=MAX_ITEMS)
    potential_direction: LongText = ""
