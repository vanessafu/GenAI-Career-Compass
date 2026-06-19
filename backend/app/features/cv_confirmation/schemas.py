from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.features.cv_parsing.schemas import CVData

ConfirmationStatus = Literal["pending", "confirmed", "edited", "skipped"]


class ConfirmationSection(BaseModel):
    section_id: str
    title: str
    path: list[str | int]
    status: ConfirmationStatus = "pending"


class ConfirmationMetadata(BaseModel):
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_sections: list[str] = Field(default_factory=list)
    skipped_sections: list[str] = Field(default_factory=list)
    edited_fields: list[str] = Field(default_factory=list)


class ConfirmedCVData(BaseModel):
    confirmed_cv_data: CVData
    confirmation_metadata: ConfirmationMetadata
    # Set by the prompt-engineering step once the profile is privacy-stripped and
    # enriched with a generated career identity. This is the object handed to the
    # embedding step.
    career_identity_statement: str | None = None
