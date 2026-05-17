"""
Job 3: prompt generator template.

Input: 
Output: 

"""

from typing import Dict

from modules.shared.types import EnrichedUserProfile, PromptGeneratorOutput


class PromptGenerator:
    """Build an editable career-search prompt from profile data."""

    def generate(self, profile: EnrichedUserProfile) -> PromptGeneratorOutput:
        """Create the prompt"""
        
