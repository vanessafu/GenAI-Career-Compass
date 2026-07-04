# Setup

## Prerequisites

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) for
Python dependency management.

## Python Environment

```powershell
uv sync
```

This creates `.venv/`, installs dependencies from `uv.lock`, and installs the
project as an editable package. No manual `venv` or `pip install` is needed.

## Environment Variables

```powershell
Copy-Item .env.example .env
# then fill in the values below
```

Required:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key used for CV parsing, identity generation, role summaries, and roadmaps |
| `DATABASE_URL` | Postgres/Supabase connection string used by role matching, gap analysis, and career paths |

Optional model overrides:

| Variable | Purpose |
|---|---|
| `OPENAI_MODEL` | Fallback chat model |
| `OPENAI_CV_PARSING_MODEL` | CV parsing model |
| `OPENAI_IDENTITY_MODEL` | Profile identity model |
| `OPENAI_ROLE_DESCRIPTION_MODEL` | Role card summary model |
| `OPENAI_CAREER_PATH_MODEL` | Career roadmap model |
| `OPENAI_TEMPERATURE` | LLM sampling temperature |

## Running The Backend

```powershell
uv run uvicorn backend.app.main:app --reload --reload-dir backend
```

`--reload-dir backend` keeps the file-watcher scoped to backend source code, so writes
to `outputs/pipeline/` (debug artifacts written on every profile run) don't trigger a
full server restart mid-request.

The backend listens on `http://localhost:8000`.

## Running The Frontend

The frontend is a Vite React SPA. It calls the FastAPI backend by default at
`http://localhost:8000`; override with `VITE_API_BASE_URL` if needed.

```powershell
cd frontend
npm install
npm run dev
```

The dev server listens on `http://localhost:5173` and is already in the backend
CORS allow-list.

Useful fixture-only URLs for layout work:

- `http://localhost:5173/?demo=recap`
- `http://localhost:5173/?demo=roles`
- `http://localhost:5173/?demo=focus`

These fixtures do not replace the normal backend flow.

## Main App Flow

```text
profile-pipeline/* -> frontend profile conversion -> /roles/match -> gap API -> path API
```

Start the backend before the frontend for the normal upload/manual-entry flow.
