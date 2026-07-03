"""Always-on persistence of intermediate pipeline artifacts.

Every step of the parse -> confirm -> profile-preparation -> embedding flow writes
its output to ``<PIPELINE_OUTPUT_DIR>/<profile_stem>/<step>.<suffix>`` so the data
handed between stages can be inspected on disk.
"""

import json
import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from backend.app.core.config import PIPELINE_OUTPUT_DIR
from backend.app.features.cv_parsing.schemas import CVData

logger = logging.getLogger("CareerCompass.PipelineDebug")


def _safe_stem(value: str | None) -> str:
    stem = Path(value or "profile").stem
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in stem)
    return safe or "profile"


def derive_profile_stem(cv_data: CVData, *, fallback: str = "profile") -> str:
    """Best-effort stable folder name for a profile's debug artifacts."""
    if cv_data.source and cv_data.source.filename:
        return _safe_stem(cv_data.source.filename)
    if cv_data.personal_info.current_role:
        return _safe_stem(cv_data.personal_info.current_role)
    return _safe_stem(fallback)


def save_pipeline_artifact(
    step: str,
    payload: BaseModel | dict[str, Any] | str,
    *,
    profile_stem: str,
    suffix: str = "json",
) -> Path:
    """Write a single pipeline step to disk and return the output path."""
    step_dir = PIPELINE_OUTPUT_DIR / profile_stem
    step_dir.mkdir(parents=True, exist_ok=True)
    output_path = step_dir / f"{step}.{suffix}"

    if isinstance(payload, str):
        output_path.write_text(payload, encoding="utf-8")
    elif isinstance(payload, BaseModel):
        output_path.write_text(
            json.dumps(payload.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    else:
        output_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    logger.info("Pipeline artifact [%s] saved to %s", step, output_path.resolve())
    return output_path
