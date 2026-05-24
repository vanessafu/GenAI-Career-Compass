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

```bash
cd frontend
npm install
npm run dev
```
