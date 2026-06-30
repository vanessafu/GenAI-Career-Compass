from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import add_frontend_routes


def test_frontend_dist_serves_index_and_keeps_api_404(tmp_path):
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "index.html").write_text("<main>Career Compass</main>", encoding="utf-8")
    (dist_dir / "app.js").write_text("console.log('ok')", encoding="utf-8")

    app = FastAPI()
    add_frontend_routes(app, dist_dir)
    client = TestClient(app)

    assert "Career Compass" in client.get("/").text
    assert "Career Compass" in client.get("/roles/123").text
    assert client.get("/app.js").text == "console.log('ok')"
    assert client.get("/api/missing").status_code == 404
