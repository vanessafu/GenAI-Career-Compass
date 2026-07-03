from backend.app.features.cv_parsing.schemas import CVData
from backend.app.features.profile_preparation.schemas import EmbeddingProfile

from pydantic import BaseModel


class ProfilePipelineResponse(BaseModel):
    cv_data: CVData
    privacy_stripped_cv_data: CVData
    embedding_profile: EmbeddingProfile
