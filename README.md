# GenAI Career Compass

Career path exploration tool powered by AI, semantic search (pgvector), and the ESCO occupational database.

## Backend

### Setup

1. Ensure PostgreSQL is running with pgvector extension installed
2. Create a `.env` file (copy from `.env.example`):
   - `OPENAI_API_KEY` — your OpenAI API key
   - `DATABASE_URL` — PostgreSQL connection string

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### CV Parsing CLI

Extract and parse CV data:

```bash
# Extract text from PDF
python -m backend.app.cli extract-text test_data/cvs/semjon_eschweiler_04_26.pdf

# Parse PDF CV into JSON with LLM
python -m backend.app.cli parse-cv test_data/cvs/semjon_eschweiler_04_26.pdf

# Full parse + confirmation flow
python -m backend.app.cli confirm-cv test_data/cvs/semjon_eschweiler_04_26.pdf

# Confirm already parsed JSON
python -m backend.app.cli confirm-json outputs/semjon_eschweiler_04_26_parsed.json

# Manual profile entry (no CV)
python -m backend.app.cli manual-profile
```

### Role Matching & RAG Pipeline

Build the occupation index from ESCO dataset (one-time setup):

```bash
# Step 1: Load and filter IT occupations from local ESCO CSV
python -m backend.scripts.data_loader

# Step 2: Join occupations with skills and build embedding text
python -m backend.scripts.data_preprocessing

# Step 3: Embed with OpenAI and insert into pgvector
python -m backend.scripts.build_embeddings
```

Once indexed, use the role matching API:

```bash
# Start FastAPI server
python -m uvicorn backend.main:app --reload
```

Then POST to `/api/v1/roles/match` with parsed CV data.

### API

- `POST /api/v1/roles/match` — Find matching IT occupations for a CV using semantic search
- `POST /api/v1/cv/upload` — Parse uploaded CV file
- `GET /docs` — Interactive API documentation

## Frontend

See `frontend/README.md` for frontend setup and development.

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── features/
│   │   │   ├── cv_parsing/      # CV extraction and parsing
│   │   │   ├── cv_confirmation/ # User confirmation flow
│   │   │   ├── role_matching/   # RAG-based occupational matching
│   │   │   └── prompt_engineering/
│   │   ├── core/
│   │   │   └── config.py        # Environment & API config
│   │   └── cli.py               # Command-line interface
│   ├── scripts/
│   │   ├── data_loader.py       # Fetch ESCO occupations
│   │   ├── data_preprocessing.py # Process and enrich data
│   │   └── build_embeddings.py  # Build pgvector index
│   ├── main.py                  # FastAPI application
│   └── requirements.txt
├── frontend/
│   └── ...
└── docs/
    └── proposal.md
```

## Architecture

- **Backend**: Python/FastAPI with OpenAI API integration
- **Vector DB**: PostgreSQL with pgvector extension for semantic search
- **Data Source**: ESCO dataset (130 IT-relevant occupations, ~1500 skills)
- **Frontend**: React/TypeScript (Vite)

## Development

- Team member 1 (CV parsing): `backend/app/features/cv_parsing` & `backend/app/cli.py`
- Team member 2 (Data & RAG): `backend/app/features/role_matching` & `backend/scripts/`

Create feature branches from `main` for new work.
