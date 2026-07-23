import asyncio
from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from backend.app.core.http_security import secure_requests
from backend.app.core import database
from backend.app.features.profile_pipeline.router import (
    MAX_FILENAME_CHARS,
    MAX_PDF_BYTES,
    _read_pdf,
)


def upload(payload: bytes, filename: str = "resume.pdf") -> UploadFile:
    return UploadFile(file=BytesIO(payload), filename=filename)


def test_pdf_upload_boundary_accepts_only_bounded_pdf_content():
    valid = b"%PDF-1.7\nfixture"
    assert asyncio.run(_read_pdf(upload(valid))) == valid

    invalid = upload(b"not a pdf")
    try:
        asyncio.run(_read_pdf(invalid))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Expected invalid PDF content to be rejected")

    long_filename = upload(valid, filename="a" * (MAX_FILENAME_CHARS - 3) + ".pdf")
    try:
        asyncio.run(_read_pdf(long_filename))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 400
    else:
        raise AssertionError("Expected an oversized PDF filename to be rejected")

    oversized = upload(b"%PDF-" + b"x" * MAX_PDF_BYTES)
    try:
        asyncio.run(_read_pdf(oversized))
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 413
    else:
        raise AssertionError("Expected an oversized PDF to be rejected")


def test_api_rate_limit_and_security_headers():
    app = FastAPI()
    app.middleware("http")(secure_requests)

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    @app.get("/")
    async def root():
        return {"ok": True}

    client = TestClient(app)
    for _ in range(20):
        assert client.options("/api/v1/ping").status_code == 405

    for _ in range(15):
        response = client.get("/api/v1/ping", headers={"x-forwarded-for": "198.51.100.1"})
        assert response.status_code == 200

    limited = client.get("/api/v1/ping", headers={"x-forwarded-for": "198.51.100.1"})
    assert limited.status_code == 429
    assert client.get("/api/v1/ping", headers={"x-forwarded-for": "203.0.113.1"}).status_code == 200
    assert limited.headers["x-content-type-options"] == "nosniff"
    assert limited.headers["referrer-policy"] == "no-referrer"
    assert limited.headers["retry-after"] == "60"
    assert client.get("/").status_code == 200


def test_database_connection_is_rolled_back_before_pool_return(monkeypatch):
    events = []

    class Connection:
        def rollback(self):
            events.append("rollback")

    connection = Connection()

    class Pool:
        def getconn(self):
            return connection

        def putconn(self, returned):
            assert returned is connection
            events.append("putconn")

    monkeypatch.setattr(database, "db_pool", Pool())
    monkeypatch.setattr(database, "register_vector", lambda conn: events.append("register"))

    with database.get_db_connection() as returned:
        assert returned is connection

    assert events == ["register", "rollback", "putconn"]


def test_public_api_failures_are_generic_and_obsolete_routes_are_absent(monkeypatch):
    from backend.app.features.cv_parsing.schemas import CVData
    from backend.app.features.profile_pipeline import router as profile_router
    from backend.app.features.role_matching import router as role_router
    from backend.app.main import app

    async def parsed_cv(_raw_text):
        return CVData()

    async def fail_pipeline(_cv_data):
        raise RuntimeError("sensitive upstream details")

    async def fail_match(*_args, **_kwargs):
        raise RuntimeError("sensitive database details")

    monkeypatch.setattr(profile_router, "extract_text_from_pdf_bytes", lambda _payload: "CV text")
    monkeypatch.setattr(profile_router, "parse_cv_to_pydantic", parsed_cv)
    monkeypatch.setattr(profile_router, "run_profile_pipeline", fail_pipeline)
    monkeypatch.setattr(role_router, "match_roles_for_profile", fail_match)

    client = TestClient(app, raise_server_exceptions=False)
    parsed = client.post(
        "/api/v1/profile-pipeline/parse-cv",
        files={"file": ("resume.pdf", b"%PDF-fixture", "application/pdf")},
    )
    manual = client.post(
        "/api/v1/profile-pipeline/manual-cv",
        json={
            "current_role": "Data Analyst",
            "technical_skills": ["SQL"],
            "interests": ["Analytics"],
        },
    )
    matched = client.post(
        "/api/v1/roles/match",
        json={
            "profile": {
                "career_identity": {"title": "Data Analyst"},
                "skills": ["SQL"],
                "interests": ["Analytics"],
            }
        },
    )

    assert parsed.status_code == 503
    assert parsed.json()["detail"] == "CV processing is temporarily unavailable."
    assert manual.status_code == 503
    assert manual.json()["detail"] == "Profile processing is temporarily unavailable."
    assert matched.status_code == 503
    assert matched.json()["detail"] == "Role matching is temporarily unavailable."
    assert client.post("/api/v1/parse-cv").status_code == 404
    assert client.post("/api/v1/manual-cv").status_code == 404
