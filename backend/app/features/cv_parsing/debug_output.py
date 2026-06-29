"""On-disk persistence for parsed CV data (first pipeline step)."""

from backend.app.core.pipeline_debug import derive_profile_stem, save_pipeline_artifact
from backend.app.features.cv_parsing.schemas import CVData


def save_cv_debug_artifact(cv: CVData, *, name: str | None = None) -> None:
    """Persist parsed CVData as the first pipeline artifact."""
    profile_stem = derive_profile_stem(cv, fallback=name or "upload")
    save_pipeline_artifact("01_parsed_cv", cv, profile_stem=profile_stem)


def save_parsed_cv(cv: CVData, *, filename: str | None = None) -> None:
    """Backwards-compatible wrapper for the parse-cv route."""
    save_cv_debug_artifact(cv, name=filename)
