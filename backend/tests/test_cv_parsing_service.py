import asyncio

from backend.app.features.cv_parsing import service
from backend.app.features.cv_parsing.schemas import CVData


def test_blank_parsed_interests_are_generated(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None):
        calls.append((response_format, model_purpose, list(messages)))
        if response_format is CVData:
            return CVData(interests=[])
        return response_format(interests=[" Cloud platforms ", "AI", "ai", "", "Data"])

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == ["Cloud platforms", "AI", "Data"]
    assert len(calls) == 2
    assert calls[1][1] == "identity"


def test_existing_parsed_interests_skip_generation(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None):
        calls.append((response_format, model_purpose, list(messages)))
        assert response_format is CVData
        return CVData(interests=["Cloud platforms"])

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == ["Cloud platforms"]
    assert len(calls) == 1


def test_interest_generation_failure_keeps_cv_parse_result(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None):
        calls.append((response_format, model_purpose, list(messages)))
        if response_format is CVData:
            return CVData(interests=[])
        raise RuntimeError("interest generation unavailable")

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == []
    assert len(calls) == 2
