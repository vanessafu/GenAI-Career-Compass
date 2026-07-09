from pydantic import BaseModel, Field

from backend.app.features.cv_parsing.schemas import Language


class ManualEducationInput(BaseModel):
    degree_type: str
    institution: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ManualExperienceInput(BaseModel):
    role: str
    organization: str | None = None
    description: str | None = None
    start_date: str | None = None
    end_date: str | None = None


class ManualCertificationInput(BaseModel):
    name: str
    issuing_organization: str | None = None
    issue_date: str | None = None


class ManualProjectInput(BaseModel):
    title: str
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None


class ManualCVInput(BaseModel):
    """Frontend-friendly payload for manually entered profiles.

    A thin DTO that is mapped to the full CVData schema server-side, so the
    frontend does not need to assemble CVData itself.
    """

    current_role: str | None = None
    seniority_level: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0, le=80)
    summary: str | None = None
    education: list[ManualEducationInput] = Field(default_factory=list)
    experience: list[ManualExperienceInput] = Field(default_factory=list)
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    projects: list[ManualProjectInput] = Field(default_factory=list)
    certifications: list[ManualCertificationInput] = Field(default_factory=list)
