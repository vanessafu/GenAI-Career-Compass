from typing import Optional
from pydantic import BaseModel, Field

class Metadata(BaseModel):
    parsing_confidence: float
    detected_language: Optional[str] = None

class ProfileSummary(BaseModel):
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

class CVData(BaseModel):
    metadata: Metadata
    profile_summary: ProfileSummary
    experience: list[Experience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills_extracted: SkillsExtracted
    interests: list[str] = Field(default_factory=list)