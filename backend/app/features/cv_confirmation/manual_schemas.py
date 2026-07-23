from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.validation import LongText, MAX_ITEMS, ShortText
from backend.app.features.cv_parsing.schemas import Language


class ManualEducationInput(BaseModel):
    degree_type: ShortText
    institution: ShortText | None = None
    field_of_study: ShortText | None = None
    start_date: ShortText | None = None
    end_date: ShortText | None = None


class ManualExperienceInput(BaseModel):
    role: ShortText
    organization: ShortText | None = None
    description: LongText | None = None
    start_date: ShortText | None = None
    end_date: ShortText | None = None


class ManualCertificationInput(BaseModel):
    name: ShortText
    issuing_organization: ShortText | None = None
    issue_date: ShortText | None = None


class ManualProjectInput(BaseModel):
    title: ShortText
    description: LongText | None = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    start_date: ShortText | None = None
    end_date: ShortText | None = None


class ManualCVInput(BaseModel):
    """Frontend-friendly payload mapped to the full CVData schema server-side."""

    model_config = ConfigDict(extra="forbid")

    current_role: ShortText | None = None
    seniority_level: ShortText | None = None
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    summary: LongText | None = None
    education: list[ManualEducationInput] = Field(default_factory=list, max_length=MAX_ITEMS)
    experience: list[ManualExperienceInput] = Field(default_factory=list, max_length=MAX_ITEMS)
    technical_skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    soft_skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    languages: list[Language] = Field(default_factory=list, max_length=MAX_ITEMS)
    interests: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    projects: list[ManualProjectInput] = Field(default_factory=list, max_length=MAX_ITEMS)
    certifications: list[ManualCertificationInput] = Field(
        default_factory=list,
        max_length=MAX_ITEMS,
    )