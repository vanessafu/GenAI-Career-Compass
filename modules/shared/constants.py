"""
Shared constants for Career Compass v1.

Only keep values here when multiple modules need the same value.

"""
from modules.shared.types import DataSource

PROJECT_NAME = "Career Compass"

SUPPORTED_CV_FORMATS = {"pdf", "docx", "txt"}

DEFAULT_DATA_SOURCE = DataSource.MOCK
DEFAULT_LANGUAGE = "en"

MAX_CAREER_SUGGESTIONS = 10