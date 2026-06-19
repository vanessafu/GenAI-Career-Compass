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
|       |   |-- role_matching/
|       |   `-- prompt_engineering/
|       `-- scripts/
|-- frontend/
|-- docs/
|-- data/
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
| `OPENAI_API_KEY` | API key used for CV parsing and role-matching analysis |
| `OPENAI_MODEL` | Chat model to use, for example `gpt-4o-mini` |
| `OPENAI_TEMPERATURE` | Sampling temperature, default `0.0` |
| `DATABASE_URL` | Postgres connection string for the `esco_occupations` pgvector table |

### 3. Database

The role-matching feature expects a Postgres database with the `pgvector` extension enabled and an `esco_occupations` table populated with ESCO data and precomputed embeddings. Loader scripts live under `backend/scripts/`.

## Running The Backend

### API Server

```powershell
uv run uvicorn backend.app.main:app --reload
```

The server listens on `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs`.

Key endpoints:

- `POST /api/v1/parse-cv` uploads a PDF and returns a structured `CVData` profile
- `POST /api/v1/roles/match` submits a confirmed profile and returns top-k matching ESCO roles with reasoning

### CLI

The `career-compass` script is registered as an entry point, so after `uv sync` you can call it directly:

```powershell
uv run career-compass extract-text test_data/cvs/your_cv.pdf
uv run career-compass parse-cv test_data/cvs/your_cv.pdf
uv run career-compass confirm-cv test_data/cvs/your_cv.pdf
uv run career-compass confirm-json outputs/your_cv_parsed.json
uv run career-compass manual-profile
uv run career-compass identity-followups outputs/your_confirmed.json
uv run career-compass career-profile outputs/your_confirmed.json
uv run career-compass embedding-input outputs/your_confirmed.json
uv run career-compass embedding-chunks outputs/your_confirmed.json
```

The manual and CV-based flows both collect or confirm current role, education, work experience, projects, certifications, thesis, skills, languages, interests, and unmapped information into the same confirmed JSON format.

## Running The Frontend

```powershell
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and talks to the backend at `http://localhost:8000`.

See [frontend/README.md](frontend/README.md) for more details.

## License

MIT. See [LICENSE](LICENSE).
