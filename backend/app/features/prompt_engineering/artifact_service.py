import json
from pathlib import Path

from backend.app.features.prompt_engineering.schemas import (
    CareerProfileResponse,
    EmbeddingInputResponse,
    SemanticEmbeddingInputResponse,
)

PROMPT_ENGINEERING_DIRNAME = "prompt_engineering"
CONFIRMED_SUFFIX = "_confirmed"
EMBEDDING_INPUT_FILENAME = "embedding_input.txt"
CAREER_PROFILE_FILENAME = "career_profile.json"
EMBEDDING_CHUNKS_FILENAME = "embedding_chunks.json"


def profile_output_dir_from_confirmed_path(confirmed_json_path: Path) -> Path:
    """Return outputs/<profile>/ for a confirmed JSON file.

    Supports the current flat CLI output style, for example
    outputs/semjon_eschweiler_04_26_confirmed_old.json, and the proposed nested
    style, for example outputs/semjon_eschweiler_04_26_old/confirmed.json.
    """
    if confirmed_json_path.stem == "confirmed":
        return confirmed_json_path.parent

    profile_name = confirmed_json_path.stem
    if profile_name.endswith(CONFIRMED_SUFFIX):
        profile_name = profile_name[: -len(CONFIRMED_SUFFIX)]

    return confirmed_json_path.parent / profile_name


def prompt_engineering_output_dir(confirmed_json_path: Path) -> Path:
    return profile_output_dir_from_confirmed_path(confirmed_json_path) / PROMPT_ENGINEERING_DIRNAME


def _career_profile_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / CAREER_PROFILE_FILENAME


def _embedding_chunks_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / EMBEDDING_CHUNKS_FILENAME


def save_embedding_input_text_artifact(
    confirmed_json_path: Path,
    result: EmbeddingInputResponse,
) -> Path:
    output_dir = prompt_engineering_output_dir(confirmed_json_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / EMBEDDING_INPUT_FILENAME
    output_path.write_text(result.embedding_input_text, encoding="utf-8")
    return output_path


def save_career_profile_artifact(
    confirmed_json_path: Path,
    result: CareerProfileResponse,
) -> Path:
    output_dir = prompt_engineering_output_dir(confirmed_json_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _career_profile_path(confirmed_json_path)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


def save_embedding_chunks_artifact(
    confirmed_json_path: Path,
    result: SemanticEmbeddingInputResponse,
) -> Path:
    output_dir = prompt_engineering_output_dir(confirmed_json_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _embedding_chunks_path(confirmed_json_path)
    output_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
