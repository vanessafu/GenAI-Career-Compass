"""Prepares a confirmed profile for the embedding step.

Takes the confirmed CV, privacy-strips it (same CVData schema), generates a career
identity statement, and returns a ConfirmedCVData carrying both. Every intermediate
step is persisted to disk.
"""

import logging

from backend.app.core.pipeline_debug import derive_profile_stem, save_pipeline_artifact
from backend.app.features.cv_confirmation.schemas import ConfirmedCVData
from backend.app.features.prompt_engineering.identity_generation_service import (
    generate_career_identity,
)
from backend.app.features.prompt_engineering.profile_projector import privacy_strip_cv_data

logger = logging.getLogger("CareerCompass.PromptEngineering.EmbeddingHandoff")


async def prepare_for_embedding(confirmed_profile: ConfirmedCVData) -> ConfirmedCVData:
    """Privacy-strip the CV, generate the career identity, and persist each step.

    Returns the ConfirmedCVData that the embedding step consumes: the
    privacy-stripped CV plus the generated ``career_identity_statement``.
    """
    profile_stem = derive_profile_stem(confirmed_profile.confirmed_cv_data)

    stripped_cv = privacy_strip_cv_data(confirmed_profile.confirmed_cv_data)
    save_pipeline_artifact("02_privacy_stripped", stripped_cv, profile_stem=profile_stem)

    identity = await generate_career_identity(stripped_cv)
    save_pipeline_artifact(
        "03_identity_statement",
        {"career_identity_statement": identity},
        profile_stem=profile_stem,
    )

    result = ConfirmedCVData(
        confirmed_cv_data=stripped_cv,
        confirmation_metadata=confirmed_profile.confirmation_metadata,
        career_identity_statement=identity,
    )
    save_pipeline_artifact("04_confirmed_with_identity", result, profile_stem=profile_stem)

    return result
