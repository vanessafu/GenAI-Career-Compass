from typing import Literal, Optional

from pydantic import BaseModel, Field

from backend.app.core.validation import LongText, MAX_ITEMS, ShortText


class SourceDocument(BaseModel):
    filename: Optional[ShortText] = None


class PersonalInfo(BaseModel):
    full_name: Optional[ShortText] = None
    email: Optional[ShortText] = None
    phone: Optional[ShortText] = None
    location: Optional[ShortText] = None
    current_role: Optional[ShortText] = None
    links: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)


class Metadata(BaseModel):
    parsing_confidence: float = Field(default=0.0, ge=0.0, le=100.0)
    detected_language: Optional[ShortText] = None


class ProfileSummary(BaseModel):
    summary: Optional[LongText] = None
    current_seniority_level: Optional[ShortText] = None
    years_of_experience: Optional[int] = Field(default=None, ge=0, le=80)


class Experience(BaseModel):
    role: Optional[ShortText] = None
    organization: Optional[ShortText] = None
    industry: Optional[ShortText] = None
    start_date: Optional[ShortText] = None
    end_date: Optional[ShortText] = None
    duration_months: Optional[int] = Field(default=None, ge=0)
    location: Optional[ShortText] = None
    core_responsibilities: list[LongText] = Field(default_factory=list, max_length=MAX_ITEMS)
    contextual_skills: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)


class Education(BaseModel):
    entry_type: Literal["degree", "semester_abroad", "high_school", "certification", "other"] = "degree"
    degree_type: Optional[ShortText] = None
    field_of_study: Optional[ShortText] = None
    institution: Optional[ShortText] = None
    start_date: Optional[ShortText] = None
    end_date: Optional[ShortText] = None
    grade: Optional[ShortText] = None
    thesis_title: Optional[LongText] = None
    thesis_grade: Optional[ShortText] = None
    courses: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)


class Project(BaseModel):
    title: Optional[ShortText] = None
    description: Optional[LongText] = None
    organization: Optional[ShortText] = None
    role: Optional[ShortText] = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    outcomes: list[LongText] = Field(default_factory=list, max_length=MAX_ITEMS)
    links: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    start_date: Optional[ShortText] = None
    end_date: Optional[ShortText] = None


class Certification(BaseModel):
    name: Optional[ShortText] = None
    issuing_organization: Optional[ShortText] = None
    issue_date: Optional[ShortText] = None
    expiration_date: Optional[ShortText] = None
    credential_id: Optional[ShortText] = None
    credential_url: Optional[ShortText] = None


class Thesis(BaseModel):
    title: Optional[LongText] = None
    degree_type: Optional[ShortText] = None
    institution: Optional[ShortText] = None
    supervisor: Optional[ShortText] = None
    description: Optional[LongText] = None
    technologies: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    grade: Optional[ShortText] = None


class TechnicalSkill(BaseModel):
    name: ShortText
    proficiency_indication: Optional[ShortText] = None


class InferredSkill(BaseModel):
    name: ShortText
    inferred_from: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    rationale: Optional[LongText] = None


class SoftSkill(BaseModel):
    name: ShortText
    confidence: float = Field(default=65.0, ge=0.0, le=100.0)


class Language(BaseModel):
    language: ShortText
    level: Optional[ShortText] = None


class SkillsExtracted(BaseModel):
    technical_skills: list[TechnicalSkill] = Field(default_factory=list, max_length=MAX_ITEMS)
    inferred_skills: list[InferredSkill] = Field(default_factory=list, max_length=MAX_ITEMS)
    soft_skills: list[SoftSkill] = Field(default_factory=list, max_length=MAX_ITEMS)
    languages: list[Language] = Field(default_factory=list, max_length=MAX_ITEMS)


class UnmappedInformation(BaseModel):
    label: Optional[ShortText] = None
    value: LongText
    source_section: Optional[ShortText] = None
    reason_not_mapped: Optional[LongText] = None


class CVData(BaseModel):
    source: Optional[SourceDocument] = None
    metadata: Metadata = Field(default_factory=Metadata)
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    profile_summary: ProfileSummary = Field(default_factory=ProfileSummary)
    experience: list[Experience] = Field(default_factory=list, max_length=MAX_ITEMS)
    education: list[Education] = Field(default_factory=list, max_length=MAX_ITEMS)
    projects: list[Project] = Field(default_factory=list, max_length=MAX_ITEMS)
    certifications: list[Certification] = Field(default_factory=list, max_length=MAX_ITEMS)
    thesis: list[Thesis] = Field(default_factory=list, max_length=MAX_ITEMS)
    skills_extracted: SkillsExtracted = Field(default_factory=SkillsExtracted)
    interests: list[ShortText] = Field(default_factory=list, max_length=MAX_ITEMS)
    potential_direction: Optional[LongText] = None
    unmapped_information: list[UnmappedInformation] = Field(
        default_factory=list,
        max_length=MAX_ITEMS,
    )