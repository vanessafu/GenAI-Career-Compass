import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.0"))

DATABASE_URL = os.getenv("DATABASE_URL")

# Pipeline artifacts: every step persists its output under this directory.
PIPELINE_OUTPUT_DIR = Path(os.getenv("PIPELINE_OUTPUT_DIR", "outputs/pipeline"))
