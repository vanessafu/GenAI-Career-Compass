import pytest

from backend.app.core.http_security import reset_rate_limit_state
from backend.app.features.role_matching import skill_ontology


@pytest.fixture(scope="session", autouse=True)
def _load_vendored_ontology():
    previous = skill_ontology._ontology
    skill_ontology._ontology = skill_ontology.SkillOntology()
    yield
    skill_ontology._ontology = previous


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    reset_rate_limit_state()
    yield
    reset_rate_limit_state()