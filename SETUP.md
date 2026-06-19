# Setup

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python package manager).

## Python environment

```bash
uv sync
```

Creates `.venv/`, installs all dependencies from `uv.lock`, and installs the project as an editable package. No manual `venv` or `pip install` needed.

## Environment variables

```bash
cp .env.example .env
# then fill in OPENAI_API_KEY and DATABASE_URL
```

## Running the backend

```bash
uv run uvicorn backend.app.main:app --reload
```

## Running the frontend

The frontend is a TanStack Start (React 19 + Vite + Tailwind) app. It currently
runs on local mock data — see `frontend/BACKEND_INTEGRATION.md` for the endpoints
the backend team still needs to provide.

```bash
cd frontend
npm install
npm run dev
```

The dev server listens on `http://localhost:5173` (already in the backend CORS allow-list).
