from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse

from backend.app.core.http_security import secure_requests
from backend.app.core.openai_client import openai_client_lifespan
from backend.app.features.profile_pipeline.router import router as profile_pipeline_router
from backend.app.features.role_matching.router import router as role_matching_router

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from backend.app.features.role_matching.embedder import get_embedder
    from backend.app.features.role_matching.skill_ontology import get_ontology

    await asyncio.to_thread(get_ontology)
    await asyncio.to_thread(get_embedder)
    async with openai_client_lifespan():
        yield


app = FastAPI(title="Career Compass API", lifespan=lifespan)
app.middleware("http")(secure_requests)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profile_pipeline_router)
app.include_router(role_matching_router)


def add_frontend_routes(app: FastAPI, dist_dir: Path = FRONTEND_DIST) -> None:
    """Serve the built Vite app when frontend/dist is present."""
    dist_dir = dist_dir.resolve()
    index_path = dist_dir / "index.html"

    @app.api_route(
        "/api/{path:path}",
        methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        include_in_schema=False,
    )
    async def unknown_api(path: str):
        raise HTTPException(status_code=404)

    @app.get("/", include_in_schema=False)
    async def root():
        if index_path.is_file():
            return FileResponse(index_path)
        return RedirectResponse(url="/docs")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend_or_404(path: str):
        if path.startswith("api/"):
            raise HTTPException(status_code=404)
        if not index_path.is_file():
            raise HTTPException(status_code=404)

        target_path = (dist_dir / path).resolve()
        if target_path.is_file() and target_path.is_relative_to(dist_dir):
            return FileResponse(target_path)
        return FileResponse(index_path)


add_frontend_routes(app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"],
    )
