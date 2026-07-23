import asyncio

import pytest

from backend.app.features.cv_parsing import service
from backend.app.features.cv_parsing.schemas import CVData, InferredSkill, SkillsExtracted, SoftSkill, SourceDocument


def test_cv_parse_uses_combined_parsing_and_extraction_prompt(monkeypatch):
    calls = []

    async def fake_parse_structured(messages, response_format, *, model_purpose=None, model=None):
        calls.append((response_format, model_purpose, model, list(messages)))
        assert response_format is CVData
        return CVData(
            interests=["Cloud platforms"],
            skills_extracted={
                "soft_skills": [{"name": "Cross-team collaboration", "confidence": 80}]
            },
        )

    monkeypatch.setattr(service.openai_client, "parse_structured", fake_parse_structured)

    result = asyncio.run(service.parse_cv_to_pydantic("Python backend developer"))

    assert result.interests == ["Cloud platforms"]
    assert [s.name for s in result.skills_extracted.soft_skills] == ["Cross-team collaboration"]
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


def test_inferred_skills_and_potential_direction_round_trip_through_cv_data():
    cv = CVData(
        potential_direction="Could grow toward ML engineering given the statistics/Python overlap.",
        skills_extracted=SkillsExtracted(
            inferred_skills=[
                InferredSkill(
                    name="Machine Learning Foundations",
                    inferred_from=["Python", "Data Analysis", "Linear Algebra"],
                    rationale="These three together are prerequisites for ML foundations.",
                )
            ]
        ),
    )

    restored = CVData.model_validate_json(cv.model_dump_json())

    assert restored.potential_direction == cv.potential_direction
    assert len(restored.skills_extracted.inferred_skills) == 1
    inferred = restored.skills_extracted.inferred_skills[0]
    assert inferred.name == "Machine Learning Foundations"
    assert inferred.inferred_from == ["Python", "Data Analysis", "Linear Algebra"]
    assert inferred.rationale


def test_inferred_skills_are_never_mixed_into_technical_skills():
    cv = CVData(
        skills_extracted=SkillsExtracted(
            technical_skills=[{"name": "Python"}],
            inferred_skills=[InferredSkill(name="Machine Learning Foundations", inferred_from=["Python"])],
        )
    )

    assert [s.name for s in cv.skills_extracted.technical_skills] == ["Python"]
    assert [s.name for s in cv.skills_extracted.inferred_skills] == ["Machine Learning Foundations"]


def test_prompt_instructs_inferred_skills_and_potential_direction_rules():
    prompt = service._CV_PARSING_AND_EXTRACTING_PROMPT
    assert "inferred_skills" in prompt
    assert "potential direction" in prompt.casefold()
    assert "inferred_from" in prompt


def test_prompt_globally_excludes_personal_contact_data():
    prompt = service._CV_PARSING_AND_EXTRACTING_PROMPT.casefold()
    assert "never extract email" in prompt
    assert "github/gitlab" in prompt
    for field in ("personal_info.email", "personal_info.phone", "personal_info.links"):
        assert field in prompt


def test_prompt_instructs_soft_skill_confidence_and_broadened_inference():
    prompt = service._CV_PARSING_AND_EXTRACTING_PROMPT.casefold()
    assert "confidence" in prompt
    assert "tool" in prompt or "knowledge area" in prompt


def test_soft_skill_carries_a_confidence_score():
    cv = CVData(
        skills_extracted=SkillsExtracted(
            soft_skills=[SoftSkill(name="Stakeholder management", confidence=72.0)]
        )
    )

    restored = CVData.model_validate_json(cv.model_dump_json())

    assert restored.skills_extracted.soft_skills[0].name == "Stakeholder management"
    assert restored.skills_extracted.soft_skills[0].confidence == 72.0


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


def test_pdf_extraction_enforces_page_and_text_limits(monkeypatch):
    class Page:
        def __init__(self, text=""):
            self.text = text

        def extract_text(self):
            return self.text

    class Reader:
        def __init__(self, pages):
            self.pages = pages

    monkeypatch.setattr(service, "PdfReader", lambda *args, **kwargs: Reader([Page()] * 51))
    with pytest.raises(ValueError, match="at most 50 pages"):
        service.extract_text_from_pdf_bytes(b"%PDF-fixture")

    monkeypatch.setattr(service, "PdfReader", lambda *args, **kwargs: Reader([Page("x" * 100_001)]))
    with pytest.raises(ValueError, match="at most 100,000 characters"):
        service.extract_text_from_pdf_bytes(b"%PDF-fixture")


def test_source_document_never_serializes_raw_cv_text():
    source = SourceDocument(filename="resume.pdf", extracted_text="private CV text")
    assert source.model_dump() == {"filename": "resume.pdf"}
