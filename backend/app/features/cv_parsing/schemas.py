from typing import Literal, Optional

from pydantic import BaseModel, Field


class SourceDocument(BaseModel):
    filename: Optional[str] = None
    extracted_text: Optional[str] = None


class PersonalInfo(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    current_role: Optional[str] = None
    links: list[str] = Field(default_factory=list)


class Metadata(BaseModel):
    parsing_confidence: float = 0.0
    detected_language: Optional[str] = None


class ProfileSummary(BaseModel):
    summary: Optional[str] = None
    current_seniority_level: Optional[str] = None
    years_of_experience: Optional[int] = None


class Experience(BaseModel):
    role: Optional[str] = None
    organization: Optional[str] = None
    industry: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None
    location: Optional[str] = None
    core_responsibilities: list[str] = Field(default_factory=list)
    contextual_skills: list[str] = Field(default_factory=list)


class Education(BaseModel):
    entry_type: Literal["degree", "semester_abroad", "high_school", "certification", "other"] = "degree"
    degree_type: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None
    thesis_title: Optional[str] = None
    thesis_grade: Optional[str] = None
    courses: list[str] = Field(default_factory=list)


class Project(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Certification(BaseModel):
    name: Optional[str] = None
    issuing_organization: Optional[str] = None
    issue_date: Optional[str] = None
    expiration_date: Optional[str] = None
    credential_id: Optional[str] = None
    credential_url: Optional[str] = None


class Thesis(BaseModel):
    title: Optional[str] = None
    degree_type: Optional[str] = None
    institution: Optional[str] = None
    supervisor: Optional[str] = None
    description: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    grade: Optional[str] = None


class TechnicalSkill(BaseModel):
    name: str
    proficiency_indication: Optional[str] = None


class InferredSkill(BaseModel):
    """A technical skill not explicitly stated, reasoned from a direct
    prerequisite/composition relationship to skills the CV does state - kept
    separate from `TechnicalSkill` so an inference can never be mistaken for
    a skill the person actually claimed."""

    name: str
    inferred_from: list[str] = Field(default_factory=list)
    rationale: Optional[str] = None


class SoftSkill(BaseModel):
    """An inferred (not literally stated) soft skill, with a confidence score
    reflecting how strongly the CV's experience/project evidence supports it."""

    name: str
    confidence: float = 65.0


class Language(BaseModel):
    language: str
    level: Optional[str] = None


class SkillsExtracted(BaseModel):
    technical_skills: list[TechnicalSkill] = Field(default_factory=list)
    inferred_skills: list[InferredSkill] = Field(default_factory=list)
    soft_skills: list[SoftSkill] = Field(default_factory=list)
    languages: list[Language] = Field(default_factory=list)


class UnmappedInformation(BaseModel):
    label: Optional[str] = None
    value: str
    source_section: Optional[str] = None
    reason_not_mapped: Optional[str] = None


class CVData(BaseModel):
    source: Optional[SourceDocument] = None
    metadata: Metadata = Field(default_factory=Metadata)
    personal_info: PersonalInfo = Field(default_factory=PersonalInfo)
    profile_summary: ProfileSummary = Field(default_factory=ProfileSummary)
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    thesis: list[Thesis] = Field(default_factory=list)
    skills_extracted: SkillsExtracted = Field(default_factory=SkillsExtracted)
    interests: list[str] = Field(default_factory=list)
    potential_direction: Optional[str] = None
    unmapped_information: list[UnmappedInformation] = Field(default_factory=list)
