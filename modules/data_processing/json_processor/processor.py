"""
Job 2: JSON/profile processor template.

Input: CVParseResult
Output: JSONProcessorOutput with missing-data questions

This module should not re-parse the CV. It validates Job 1 output and asks only
for information that is useful for career matching.
"""

from typing import List

from modules.shared.types import (
    CVParseResult,
    ClarifyingQuestion,
    JSONProcessorOutput,
    ProfileReview,
    QuestionType,
)


class JSONProcessor:
    """Validate parsed CV JSON and prepare follow-up questions."""

    def process(self, cv_result: CVParseResult) -> JSONProcessorOutput:
        """Return profile review and clarifying questions."""
        missing_fields = identify_missing_fields(cv_result)
        review = ProfileReview(
            #...
        )
        questions = ""
        return JSONProcessorOutput(review=review, questions=questions)


def identify_missing_fields(cv_result: CVParseResult) -> List[str]:
    """Return field names that would improve matching quality."""
    # TODO: Decide the minimum profile fields for v1.
    # Example fields: current_goal, target_industries, preferred_work_style.
    return []


