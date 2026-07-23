import asyncio

from backend.app.core import openai_client


def test_select_model_routes_known_purposes_and_fallback(monkeypatch):
    monkeypatch.setattr(openai_client, "OPENAI_MODEL", "fallback-model", raising=False)
    monkeypatch.setattr(openai_client, "OPENAI_CV_PARSING_MODEL", "cv-model", raising=False)
    monkeypatch.setattr(openai_client, "OPENAI_IDENTITY_MODEL", "identity-model", raising=False)
    monkeypatch.setattr(openai_client, "OPENAI_ROLE_DESCRIPTION_MODEL", "role-description-model", raising=False)
    monkeypatch.setattr(openai_client, "OPENAI_CAREER_PATH_MODEL", "career-path-model", raising=False)

    assert openai_client.select_model("cv_parsing") == "cv-model"
    assert openai_client.select_model("identity") == "identity-model"
    assert openai_client.select_model("role_description") == "role-description-model"
    assert openai_client.select_model("career_path") == "career-path-model"
    assert openai_client.select_model(None) == "fallback-model"

    assert openai_client.select_model("gap_narrative") == "fallback-model"

def test_openai_client_has_bounded_timeout_and_no_automatic_retries(monkeypatch):
    captured = {}

    class FakeClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def close(self):
            return None

    monkeypatch.setattr(openai_client, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(openai_client, "AsyncOpenAI", FakeClient)
    monkeypatch.setattr(openai_client, "_client", None)

    async def exercise_lifespan():
        async with openai_client.openai_client_lifespan():
            assert openai_client.get_client() is not None

    asyncio.run(exercise_lifespan())
    assert captured == {"api_key": "test-key", "timeout": 180.0, "max_retries": 0}
