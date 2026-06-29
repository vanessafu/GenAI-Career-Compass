from fastapi.testclient import TestClient

from backend.app.features.role_matching.schemas import GapReport
from backend.app.main import app


def minimal_confirmed_profile():
    return {
        "confirmed_cv_data": {
            "personal_info": {"current_role": "Backend Developer"},
            "profile_summary": {
                "summary": "Builds APIs.",
                "current_seniority_level": "mid",
                "years_of_experience": 4,
            },
            "skills_extracted": {
                "technical_skills": [{"name": "Python"}],
                "soft_skills": [],
                "languages": [],
            },
        },
        "confirmation_metadata": {
            "confirmed_at": "2026-06-26T00:00:00",
            "confirmed_sections": [],
            "skipped_sections": [],
            "edited_fields": [],
        },
    }


def test_gap_analysis_endpoint_returns_report(monkeypatch):
    async def fake_explain_role_gap(role_id, confirmed_profile):
        return GapReport(
            role_id=role_id,
            job_title="Backend Engineer",
            overall_readiness=0.75,
            domain_tags=["backend", "cloud"],
        )

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "explain_role_gap", fake_explain_role_gap, raising=False)
    client = TestClient(app)

    response = client.post("/api/v1/roles/42/gap-analysis", json=minimal_confirmed_profile())

    assert response.status_code == 200
    assert response.json()["role_id"] == 42
    assert response.json()["job_title"] == "Backend Engineer"
    assert response.json()["overall_readiness"] == 0.75
    assert response.json()["domain_tags"] == ["backend", "cloud"]


def test_gap_analysis_endpoint_returns_404_for_missing_role(monkeypatch):
    async def fake_explain_role_gap(role_id, confirmed_profile):
        raise ValueError(f"role_id {role_id} not found")

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "explain_role_gap", fake_explain_role_gap)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/roles/404/gap-analysis", json=minimal_confirmed_profile())

    assert response.status_code == 404
    assert response.json()["detail"] == "role_id 404 not found"


def test_gap_analysis_endpoint_returns_503_for_service_failure(monkeypatch):
    async def fake_explain_role_gap(role_id, confirmed_profile):
        raise RuntimeError("database unavailable")

    from backend.app.features.role_matching import router as role_router

    monkeypatch.setattr(role_router, "explain_role_gap", fake_explain_role_gap)
    client = TestClient(app, raise_server_exceptions=False)

    response = client.post("/api/v1/roles/42/gap-analysis", json=minimal_confirmed_profile())

    assert response.status_code == 503
    assert response.json()["detail"] == "database unavailable"
