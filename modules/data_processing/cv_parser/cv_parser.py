"""
Job 1: CV parsing template.

Input: ...(need to be changed)
Output: ...(need to be changed)

Usage : ...(need to be changed)
"""


from modules.shared.constants import SUPPORTED_CV_FORMATS
from modules.shared.types import CVParseResult, CVProfile


class CVParser:
    """Main entry point for converting an unstructured CV into JSON-like data."""

    def parse(self, file_path: str) -> CVParseResult:
        """Parse a CV file and return structured profile data."""
        