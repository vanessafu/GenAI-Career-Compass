from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from backend.app.core.openai_client import openai_client_lifespan
from backend.app.features.cv_confirmation.router import router as cv_confirmation_router
from backend.app.features.cv_parsing.router import router as cv_parsing_router
from backend.app.features.prompt_engineering.router import router as prompt_engineering_router
from backend.app.features.role_matching.router import router as role_matching_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with openai_client_lifespan():
        yield


app = FastAPI(title="Career Compass API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cv_parsing_router)
app.include_router(cv_confirmation_router)
app.include_router(prompt_engineering_router)
app.include_router(role_matching_router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect the base URL directly to the API documentation."""
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
