from datetime import datetime

from pydantic import BaseModel, Field


class DraftExperience(BaseModel):
    role: str | None = None
    industry: str | None = None
    duration_months: int | None = None
    core_responsibilities: list[str] = Field(default_factory=list)
    contextual_skills: list[str] = Field(default_factory=list)


class DraftEducation(BaseModel):
    degree_type: str | None = None
    field_of_study: str | None = None


class DraftTechnicalSkill(BaseModel):
    name: str
    proficiency_indication: str | None = None


class DraftLanguageSkill(BaseModel):
    language: str
    level: str | None = None


class DraftCareerSignal(BaseModel):
    label: str | None = None
    value: str


class PrivacyStrippedProfileDraft(BaseModel):
    current_role: str | None = None
    current_seniority_level: str | None = None
    years_of_experience: int | None = None
    summary: str | None = None
    experience: list[DraftExperience] = Field(default_factory=list)
    education: list[DraftEducation] = Field(default_factory=list)
    technical_skills: list[DraftTechnicalSkill] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    language_skills: list[DraftLanguageSkill] = Field(default_factory=list)
    career_signals: list[DraftCareerSignal] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


class SuggestedQuestion(BaseModel):
    question: str
    options: list[str] = Field(min_length=3, max_length=5)


class StarterIdentityGeneration(BaseModel):
    starter_identity: str
    suggested_questions: list[SuggestedQuestion] = Field(min_length=1, max_length=2)


class StarterProfileResponse(BaseModel):
    privacy_stripped_profile_draft: PrivacyStrippedProfileDraft
    starter_identity: str
    suggested_questions: list[SuggestedQuestion]


class EmbeddingMetadata(BaseModel):
    current_role: str | None = None
    current_seniority_level: str | None = None
    years_of_experience: int | None = None
    technical_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)


class EmbeddingInputResponse(BaseModel):
    embedding_input_text: str
    embedding_metadata: EmbeddingMetadata


class StoredFollowupQuestion(SuggestedQuestion):
    id: str


class IdentityFollowupsGeneration(BaseModel):
    version: int
    source_confirmed_profile: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    privacy_stripped_profile_draft: PrivacyStrippedProfileDraft
    starter_identity: str
    suggested_questions: list[StoredFollowupQuestion] = Field(min_length=1, max_length=2)


class IdentityFollowupsHistory(BaseModel):
    active_version: int
    generations: list[IdentityFollowupsGeneration] = Field(default_factory=list)


class FollowupAnswer(BaseModel):
    question_id: str
    question: str
    selected_option: str
    answered_at: datetime = Field(default_factory=datetime.utcnow)
    generation_version: int | None = None


class FollowupAnswersHistory(BaseModel):
    answers: list[FollowupAnswer] = Field(default_factory=list)
