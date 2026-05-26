from typing import Optional

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
    duration_months: Optional[int] = None
    core_responsibilities: list[str] = Field(default_factory=list)
    contextual_skills: list[str] = Field(default_factory=list)


class Education(BaseModel):
    degree_type: Optional[str] = None
    field_of_study: Optional[str] = None
    institution: Optional[str] = None


class Project(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)


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


class Language(BaseModel):
    language: str
    level: Optional[str] = None


class SkillsExtracted(BaseModel):
    technical_skills: list[TechnicalSkill] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
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
    unmapped_information: list[UnmappedInformation] = Field(default_factory=list)
