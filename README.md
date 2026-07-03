# Career Compass

An AI-powered career exploration tool that takes a user's CV and current background, then suggests realistic next-step roles, generates personalized career paths, and highlights the skill gaps between where they are and where they want to go.

See [docs/proposal.md](docs/proposal.md) for the full project proposal.

## Tech Stack

- **Backend:** FastAPI, Pydantic, OpenAI Python SDK, PyMuPDF
- **Vector search:** PostgreSQL + [pgvector](https://github.com/pgvector/pgvector) over the ESCO occupations database
- **Frontend:** React 19 + TypeScript + Vite
- **CLI:** `argparse`-based CLI for running parse, confirm, and manual-profile flows locally
- **Package manager:** [uv](https://docs.astral.sh/uv/)

## Repository Layout

```text
.
|-- backend/
|   `-- app/
|       |-- main.py
|       |-- cli.py
|       |-- core/config.py
|       |-- features/
|       |   |-- cv_parsing/
|       |   |-- cv_confirmation/
|       |   |-- profile_pipeline/
|       |   |-- role_matching/
|       |   `-- profile_preparation/
|       `-- scripts/
|-- database/
|   `-- supabase/migrations/
|-- frontend/
|-- docs/
|-- test_data/
|-- pyproject.toml
|-- uv.lock
`-- .env.example
```

## Setup

### 1. Python Environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you do not have it, then:

```powershell
uv sync
```

This creates `.venv/`, resolves all dependencies from `uv.lock`, and installs the project itself as an editable package.

### 2. Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```powershell
Copy-Item .env.example .env
```

Required keys:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key used for CV parsing, identity generation, role summaries, and roadmaps |
| `OPENAI_MODEL` | Fallback chat model for unclassified LLM calls |
| `OPENAI_CV_PARSING_MODEL` | Strong model for CV parsing, default `gpt-5.5` |
| `OPENAI_IDENTITY_MODEL` | Cheaper model for identity/context generation, default `gpt-5.4-mini` |
| `OPENAI_ROLE_DESCRIPTION_MODEL` | Cheaper model for role card summaries, default `gpt-5.4-mini` |
| `OPENAI_CAREER_PATH_MODEL` | Middle/strong model for career path generation, default `gpt-5.4` |
| `OPENAI_TEMPERATURE` | Sampling temperature, default `0.0` |
| `DATABASE_URL` | Postgres/Supabase connection string used by matching, gap analysis, and career paths |

### 3. Database

The role-matching feature expects a Postgres/Supabase database with `pgvector`
enabled, populated `career_roles`, ESCO mapping/skill tables, certification
tables, and split role embeddings. Apply the SQL migrations in
`database/supabase/migrations/`, then rebuild role embeddings with:

```powershell
uv run python -m backend.scripts.role_embeddings
```

## Running The Backend

### API Server

```powershell
uv run uvicorn backend.app.main:app --reload
```

The server listens on `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

Key endpoints used by the frontend:

- `POST /api/v1/profile-pipeline/parse-cv` uploads a PDF, parses it, privacy-strips it, and returns `ProfilePipelineResponse`
- `POST /api/v1/profile-pipeline/manual-cv` builds the same pipeline response from manual profile input
- `POST /api/v1/roles/match` submits the frontend-converted career profile and returns up to 9 bucketed ESCO role matches
- `POST /api/v1/roles/{role_id}/gap-analysis` returns the selected role's gap report for a confirmed profile
- `POST /api/v1/roles/{role_id}/career-path` returns the selected role's grounded roadmap, including the gap report as `requirement_breakdown`

The main app flow is:

```text
profile-pipeline/* -> frontend profile conversion -> /roles/match -> gap API -> path API
```

The older `POST /api/v1/parse-cv` and `POST /api/v1/manual-cv` routes still
exist for lower-level parsing/manual DTO work, but the frontend uses the
profile-pipeline routes.

### CLI

The `career-compass` script is registered as an entry point, so after `uv sync` you can call it directly:

```powershell
uv run career-compass extract-text test_data/cvs/your_cv.pdf
uv run career-compass parse-cv test_data/cvs/your_cv.pdf
uv run career-compass confirm-cv test_data/cvs/your_cv.pdf
uv run career-compass confirm-json outputs/your_cv_parsed.json
uv run career-compass manual-profile
```

The manual and CV-based flows both collect or confirm current role, education, work experience, projects, certifications, thesis, skills, languages, interests, and unmapped information into the same confirmed JSON format.

## Running The Frontend

```powershell
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and talks to the backend at `http://localhost:8000`.

### Demo Data

For frontend-only demo data, start the Vite dev server and open one of:

- `http://localhost:5173/?demo=recap`
- `http://localhost:5173/?demo=roles`
- `http://localhost:5173/?demo=focus`

These fixture screens are useful for layout/demo work and do not require the backend flow.

See [frontend/README.md](frontend/README.md) for more details.

## Deployment

For the temporary feedback deployment on Cloud Run, see [DEPLOYMENT.md](DEPLOYMENT.md).
After code changes are pushed to GitHub, redeploy from the repo root with the
command in that file.

## License

MIT. See [LICENSE](LICENSE).
