"""
Shared data contracts/types for Career Compass.

This is just the template. Feel free to change the type/class attributes here. 
Then every module can implement coherently.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class DataSource(str, Enum):
    """Supported role/skill databases."""

    ESCO = "esco"
    ONET = "onet"
    MOCK = "mock"


class QuestionType(str, Enum):
    """Question formats the frontend can render."""

    TEXT = "text"
    LIST = "list"
    MULTIPLE_CHOICE = "multiple_choice"
    YES_NO = "yes_no"


@dataclass
class Skill:
    """A skill extracted from the CV or provided by the user."""

    name: str
    category: Optional[str] = None
    level: Optional[str] = None
    source: Optional[str] = None


@dataclass
class Education:
    """Education item from a CV."""

    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None


@dataclass
class Experience:
    """Work experience item from a CV."""

    title: Optional[str] = None
    company: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None


@dataclass
class CVProfile:
    """Structured profile extracted from a CV."""

    name: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    skills: List[Skill] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)


@dataclass
class CVParseResult:
    """Job 1 output: parsed CV data plus parser metadata."""

    profile: CVProfile
    raw_text: Optional[str] = None
    file_name: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class ClarifyingQuestion:
    """Job 2 output item: a missing-data question for the user."""

    id: str
    text: str
    field: str
    type: QuestionType = QuestionType.TEXT
    options: List[str] = field(default_factory=list)
    required: bool = False


@dataclass
class ProfileReview:
    """Validated profile state after checking the parsed CV."""

    cv_result: CVParseResult
    completeness_score: float = 0.0
    missing_fields: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class JSONProcessorOutput:
    """Job 2 output: validated profile plus optional questions."""

    review: ProfileReview
    questions: List[ClarifyingQuestion] = field(default_factory=list)


@dataclass
class UserAnswer:
    """Answer provided by the user after CV parsing."""

    question_id: str
    value: Any


@dataclass
class EnrichedUserProfile:
    """Job 3 input: parsed CV plus user-provided missing information."""

    review: ProfileReview
    answers: List[UserAnswer] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass
class PromptGeneratorOutput:
    """Job 3 output: editable prompt for career matching."""

    prompt: str
    editable_sections: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CareerMatch:
    """Job 4 output item: one matched role from the chosen database."""

    role_id: str
    title: str
    source: DataSource
    score: float
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RAGMatcherOutput:
    """Job 4 output: ranked role matches."""

    matches: List[CareerMatch] = field(default_factory=list)
    query: Optional[str] = None
    source: DataSource = DataSource.MOCK


@dataclass
class RoleDescription:
    """Job 5 output item: user-facing role details."""

    role_id: str
    title: str
    source: DataSource
    description: str
    required_skills: List[Skill] = field(default_factory=list)
    next_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CareerSuggestionsResponse:
    """Final API response for the v1 position suggestion flow."""

    session_id: str
    suggestions: List[RoleDescription] = field(default_factory=list)
    matches: List[CareerMatch] = field(default_factory=list)
    status: str = "success"
