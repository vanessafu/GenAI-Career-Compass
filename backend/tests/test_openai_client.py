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
