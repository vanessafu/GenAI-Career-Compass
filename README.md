# Career Compass

An AI-powered career exploration tool that takes a user's CV and current background, then suggests realistic next-step roles, generates personalised career paths, and highlights the skill gaps between where they are and where they want to go.

See [`docs/proposal.md`](docs/proposal.md) for the full project proposal.

## Tech stack

- **Backend:** FastAPI, Pydantic, OpenAI Python SDK, PyMuPDF (PDF text extraction)
- **Vector search:** PostgreSQL + [`pgvector`](https://github.com/pgvector/pgvector) over the ESCO occupations database
- **Frontend:** React 19 + TypeScript + Vite
- **CLI:** `argparse`-based CLI for running the parse / confirm / manual-profile flows locally
- **Package manager:** [`uv`](https://docs.astral.sh/uv/)

## Repository layout

```
.
├── backend/
│   └── app/
│       ├── main.py             # FastAPI app entry point
│       ├── cli.py              # Local CLI (extract-text, parse-cv, confirm-cv, ...)
│       ├── core/config.py      # Env + OpenAI client wiring
│       ├── features/
│       │   ├── cv_parsing/         # PDF -> structured CVData via OpenAI
│       │   ├── cv_confirmation/    # Interactive confirmation + manual entry
│       │   ├── role_matching/      # pgvector RAG over ESCO occupations
│       │   └── prompt_engineering/ # Career identity and embedding input generation
│       └── scripts/                # (planned) data loader / preprocessing / embeddings
├── frontend/                   # React + Vite CV upload UI
├── docs/                       # Project proposal and additional docs
├── data/                       # Local datasets (gitignored)
├── test_data/                  # Local test CVs (not committed; add your own)
├── pyproject.toml
├── uv.lock
└── .env.example
```

## Setup

### 1. Python environment

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it, then:

```powershell
uv sync
```

This creates `.venv/`, resolves all dependencies from `uv.lock`, and installs the project itself as an editable package — no manual `venv` or `pip install` needed.

### 2. Environment variables

Copy `.env.example` to `.env` and fill in your values:

```powershell
Copy-Item .env.example .env
```

Required keys:

| Variable | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key used for CV parsing and role-matching analysis |
| `OPENAI_MODEL` | Chat model to use (e.g. `gpt-4o-mini`) |
| `OPENAI_TEMPERATURE` | Sampling temperature (default `0.0`) |
| `DATABASE_URL` | Postgres connection string for the `esco_occupations` pgvector table |

### 3. Database (only required for role matching)

The role-matching feature expects a Postgres database with the `pgvector` extension enabled and an `esco_occupations` table populated with ESCO data and precomputed embeddings. Loader scripts will live under `backend/scripts/` (work in progress).

## Running the backend

### API server

```powershell
uv run uvicorn backend.app.main:app --reload
```

The server listens on `http://localhost:8000`. Interactive docs are available at `http://localhost:8000/docs` (the root redirects there).

Key endpoints:

- `POST /api/v1/parse-cv` — upload a PDF, get back a structured `CVData` profile
- `POST /api/v1/roles/match` — submit a confirmed profile, get back the top-k matching ESCO roles with reasoning

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


## Running the frontend

```powershell
cd frontend
npm install
npm run dev
```

The dev server runs on `http://localhost:5173` and talks to the backend at `http://localhost:8000` (CORS is preconfigured for this origin).

See [`frontend/README.md`](frontend/README.md) for more details.

## License

MIT — see [`LICENSE`](LICENSE).
