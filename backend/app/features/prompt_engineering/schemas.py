from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 1. Privacy-safe draft models
# ---------------------------------------------------------------------------
# These models are the prompt-engineering-owned projection of confirmed CV data.
# They intentionally exclude direct identifiers, organization names, locations,
# links, and other fields that should not be sent into identity/RAG prompts.


class DraftExperience(BaseModel):
    role: str | None = None
    industry: str | None = None
    duration_months: int | None = None
    core_responsibilities: list[str] = Field(default_factory=list)
    contextual_skills: list[str] = Field(default_factory=list)


class DraftEducation(BaseModel):
    degree_type: str | None = None
    field_of_study: str | None = None


class DraftProject(BaseModel):
    title: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)


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
    projects: list[DraftProject] = Field(default_factory=list)
    technical_skills: list[DraftTechnicalSkill] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    language_skills: list[DraftLanguageSkill] = Field(default_factory=list)
    career_signals: list[DraftCareerSignal] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. Structured career profile models
# ---------------------------------------------------------------------------
# This is the internal career profile layer used to normalize roles, infer
# domains, preserve competency signals, and carry seniority reasoning forward.


class CareerProfile(BaseModel):
    normalized_roles: list[str] = Field(default_factory=list)
    career_domains: list[str] = Field(default_factory=list)
    technical_domains: list[str] = Field(default_factory=list)
    competency_signals: list[str] = Field(default_factory=list)
    career_orientation: list[str] = Field(default_factory=list)
    seniority_estimate: str | None = None
    seniority_evidence: list[str] = Field(default_factory=list)
    career_direction_candidates: list[str] = Field(default_factory=list)


class CareerProfileResponse(BaseModel):
    privacy_stripped_profile_draft: PrivacyStrippedProfileDraft
    career_profile: CareerProfile


# ---------------------------------------------------------------------------
# 3. User-facing identity and follow-up models
# ---------------------------------------------------------------------------
# These models represent content shown to the user or stored for iterative
# refinement after the system has generated an initial career identity.


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


class CareerIdentityResponse(BaseModel):
    career_profile: CareerProfile
    career_identity_statement: str
    suggested_questions: list[SuggestedQuestion]


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


# ---------------------------------------------------------------------------
# 4. Semantic embedding models
# ---------------------------------------------------------------------------
# The legacy single-text embedding response is kept for the current MVP.
# EmbeddingChunk and SemanticEmbeddingInputResponse support the target RAG
# architecture where experience, projects, competencies, and intent can be
# embedded separately.
# TODO: Keep both EmbeddingInputResponse and SemanticEmbeddingInputResponse only
# during the migration. Once the retrieval layer settles on either legacy
# single-text input or chunked semantic input, remove the unused schema and
# expose one canonical embedding preparation response.


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


class EmbeddingChunk(BaseModel):
    chunk_id: str
    chunk_type: str
    text: str
    skills: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)


class SemanticEmbeddingInputResponse(BaseModel):
    career_profile: CareerProfile
    chunks: list[EmbeddingChunk] = Field(default_factory=list)
    embedding_metadata: EmbeddingMetadata
