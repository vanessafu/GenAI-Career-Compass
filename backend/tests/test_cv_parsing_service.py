import asyncio

from backend.app.features.cv_parsing import service
from backend.app.features.cv_parsing.schemas import CVData


def test_cv_parse_uses_combined_parsing_and_extraction_prompt(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None, model=None):
        calls.append((response_format, model_purpose, model, list(messages)))
        assert response_format is CVData
        return CVData(
            interests=["Cloud platforms"],
            skills_extracted={"soft_skills": ["Cross-team collaboration"]},
        )

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == ["Cloud platforms"]
    assert result.skills_extracted.soft_skills == ["Cross-team collaboration"]
    assert len(calls) == 1
    assert calls[0][1] == "cv_parsing"
    system_prompt = calls[0][3][0]["content"]
    assert system_prompt == service._CV_PARSING_AND_EXTRACTING_PROMPT
    assert "interests" in system_prompt
    assert "soft skills" in system_prompt


def test_existing_parsed_interests_return_from_single_parse(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None, model=None):
        calls.append((response_format, model_purpose, model, list(messages)))
        assert response_format is CVData
        return CVData(interests=["Cloud platforms"])

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == ["Cloud platforms"]
    assert len(calls) == 1


def test_blank_parsed_interests_do_not_trigger_second_llm_call(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None, model=None):
        calls.append((response_format, model_purpose, model, list(messages)))
        assert response_format is CVData
        return CVData(interests=[])

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == []
    assert len(calls) == 1


def test_model_override_is_used_for_single_cv_parse(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None, model=None):
        calls.append((response_format, model_purpose, model))
        assert response_format is CVData
        return CVData(interests=["AI"])

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer", model="model-x"))

    assert result.interests == ["AI"]
    assert calls == [(CVData, "cv_parsing", "model-x")]
