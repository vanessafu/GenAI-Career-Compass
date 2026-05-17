"""
Job 4: RAG career matcher .

Input: ...
Output: ...

This module owns the database choice and matching strategy. 
"""

from modules.shared.constants import DEFAULT_DATA_SOURCE, MAX_CAREER_SUGGESTIONS
from modules.shared.types import CareerMatch, DataSource, PromptGeneratorOutput, RAGMatcherOutput


class RAGMatcher:
    """Find career roles that match the generated user prompt."""

   