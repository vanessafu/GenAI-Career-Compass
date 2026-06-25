from fastapi.testclient import TestClient

from backend.app.main import app


def test_localhost_alias_origin_is_allowed_for_dev_frontend_preflight():
    client = TestClient(app)

    response = client.options(
        "/api/v1/profile-pipeline/manual-cv",
        headers={
            "Origin": "http://127.0.0.1:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"
