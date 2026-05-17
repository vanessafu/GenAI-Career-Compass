"""Shared exports used across Career Compass modules."""

from .constants import MAX_CAREER_SUGGESTIONS, MIN_MATCH_SCORE, PipelineStep
from .errors import CareerCompassError, handle_error
from .types import (
    CVParseResult,
    CareerSuggestionsResponse,
    DataSource,
    EnrichedUserProfile,
    JSONProcessorOutput,
    PromptGeneratorOutput,
    RAGMatcherOutput,
    RoleDescription,
    UserAnswer,
)

__all__ = [
    "CVParseResult",
    "CareerSuggestionsResponse",
    "DataSource",
    "EnrichedUserProfile",
    "JSONProcessorOutput",
    "PromptGeneratorOutput",
    "RAGMatcherOutput",
    "RoleDescription",
    "UserAnswer",
    "CareerCompassError",
    "handle_error",
    "MAX_CAREER_SUGGESTIONS",
    "MIN_MATCH_SCORE",
    "PipelineStep",
]
