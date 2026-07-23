from datetime import UTC, datetime
from pydantic import BaseModel, Field

from backend.app.core.validation import LongText, MAX_ITEMS, ShortText
from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.profile_preparation.schemas import CareerIdentitySummary


class ConfirmationMetadata(BaseModel):
    confirmed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confirmed_sections: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    skipped_sections: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    edited_fields: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)


class ConfirmedCVData(BaseModel):
    confirmed_cv_data: CVData
    confirmation_metadata: ConfirmationMetadata
    # Set by the profile-preparation step once the profile is privacy-stripped and
    # enriched with a generated career identity. This is the object handed to the
    # embedding step.
    career_identity_statement: LongText | None = None
    career_identity_summary: CareerIdentitySummary | None = None
