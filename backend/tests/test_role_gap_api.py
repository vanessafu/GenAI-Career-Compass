from fastapi.testclient import TestClient

from backend.app.main import app


def test_prepare_skills_endpoint_is_removed():
    client = TestClient(app)
    response = client.post("/api/v1/roles/prepare-skills", json={})
    assert response.status_code == 404


def test_gap_analysis_endpoint_is_removed():
    client = TestClient(app)
    response = client.post("/api/v1/roles/42/gap-analysis", json={})
    assert response.status_code == 404
    assert response.status_code == 404
