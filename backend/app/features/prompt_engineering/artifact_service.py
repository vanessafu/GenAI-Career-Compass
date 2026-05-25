import json
from pathlib import Path

from backend.app.features.prompt_engineering.schemas import (
    CareerProfileResponse,
    EmbeddingInputResponse,
    FollowupAnswer,
    FollowupAnswersHistory,
    IdentityFollowupsGeneration,
    IdentityFollowupsHistory,
    SemanticEmbeddingInputResponse,
    StarterProfileResponse,
    StoredFollowupQuestion,
)

PROMPT_ENGINEERING_DIRNAME = "prompt_engineering"
CONFIRMED_SUFFIX = "_confirmed"
IDENTITY_FOLLOWUPS_FILENAME = "identity_followups.json"
FOLLOWUP_ANSWERS_FILENAME = "followup_answers.json"
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


def _identity_followups_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / IDENTITY_FOLLOWUPS_FILENAME


def _followup_answers_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / FOLLOWUP_ANSWERS_FILENAME


def _career_profile_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / CAREER_PROFILE_FILENAME


def _embedding_chunks_path(confirmed_json_path: Path) -> Path:
    return prompt_engineering_output_dir(confirmed_json_path) / EMBEDDING_CHUNKS_FILENAME


def _load_identity_followups_history(output_path: Path) -> IdentityFollowupsHistory:
    if not output_path.exists():
        return IdentityFollowupsHistory(active_version=0)

    raw_payload = json.loads(output_path.read_text(encoding="utf-8"))
    if "generations" in raw_payload:
        return IdentityFollowupsHistory.model_validate(raw_payload)

    legacy_response = StarterProfileResponse.model_validate(raw_payload)
    legacy_generation = _build_identity_followups_generation(
        source_confirmed_profile="unknown",
        result=legacy_response,
        version=1,
    )
    return IdentityFollowupsHistory(
        active_version=1,
        generations=[legacy_generation],
    )


def _next_identity_followups_version(history: IdentityFollowupsHistory) -> int:
    if not history.generations:
        return 1
    return max(generation.version for generation in history.generations) + 1


def _build_identity_followups_generation(
    source_confirmed_profile: str,
    result: StarterProfileResponse,
    version: int,
) -> IdentityFollowupsGeneration:
    return IdentityFollowupsGeneration(
        version=version,
        source_confirmed_profile=source_confirmed_profile,
        privacy_stripped_profile_draft=result.privacy_stripped_profile_draft,
        starter_identity=result.starter_identity,
        suggested_questions=[
            StoredFollowupQuestion(
                id=f"v{version}_q{index}",
                question=question.question,
                options=question.options,
            )
            for index, question in enumerate(result.suggested_questions, start=1)
        ],
    )


def save_identity_followups_artifact(
    confirmed_json_path: Path,
    result: StarterProfileResponse,
) -> Path:
    output_dir = prompt_engineering_output_dir(confirmed_json_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _identity_followups_path(confirmed_json_path)
    history = _load_identity_followups_history(output_path)
    next_version = _next_identity_followups_version(history)
    history.generations.append(
        _build_identity_followups_generation(
            source_confirmed_profile=str(confirmed_json_path),
            result=result,
            version=next_version,
        )
    )
    history.active_version = next_version
    output_path.write_text(
        json.dumps(history.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path


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


def save_followup_answer_artifact(
    confirmed_json_path: Path,
    answer: FollowupAnswer,
) -> Path:
    output_dir = prompt_engineering_output_dir(confirmed_json_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = _followup_answers_path(confirmed_json_path)
    if output_path.exists():
        history = FollowupAnswersHistory.model_validate_json(
            output_path.read_text(encoding="utf-8")
        )
    else:
        history = FollowupAnswersHistory()
    history.answers.append(answer)
    output_path.write_text(
        json.dumps(history.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return output_path
