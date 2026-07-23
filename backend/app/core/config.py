import logging
import os

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_CV_PARSING_MODEL = os.getenv("OPENAI_CV_PARSING_MODEL", "gpt-5.5")
OPENAI_IDENTITY_MODEL = os.getenv("OPENAI_IDENTITY_MODEL", "gpt-5.4-mini")
OPENAI_ROLE_DESCRIPTION_MODEL = os.getenv("OPENAI_ROLE_DESCRIPTION_MODEL", "gpt-5.4-mini")
OPENAI_CAREER_PATH_MODEL = os.getenv("OPENAI_CAREER_PATH_MODEL", "gpt-5.4")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))

# Only the offline role-catalog enrichment script uses Gemini.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

DATABASE_URL = os.getenv("DATABASE_URL")
