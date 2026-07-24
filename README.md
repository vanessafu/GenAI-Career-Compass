# Career Compass

Career Compass turns a CV or manually entered profile into career-role recommendations, skill-gap analysis, and a practical career roadmap. The deployed Cloud Run service hosts both the React frontend and FastAPI backend.

## Evaluate in two minutes

Live application: [career-compass-hqrdul4iqa-ey.a.run.app](https://career-compass-hqrdul4iqa-ey.a.run.app)

1. Choose **Upload CV** and use one of the synthetic PDFs below, or choose **Enter manually**.
2. Review the extracted profile and correct anything that is wrong.
3. Generate recommendations and select up to three roles.
4. Open a selected role to inspect its requirement breakdown and roadmap.

The hosted backend already has its own budget-capped OpenAI key and read-only database connection. Evaluators do not need credentials.

## Run the frontend locally

This is the recommended local setup. It uses the hosted backend and does not require an OpenAI key, database URL, Supabase API key, or service-role key.

Prerequisites: Node.js 20.19+ or 22.12+.

PowerShell:

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL="https://career-compass-hqrdul4iqa-ey.a.run.app"
npm run dev
```

macOS/Linux:

```bash
cd frontend
npm ci
VITE_API_BASE_URL="https://career-compass-hqrdul4iqa-ey.a.run.app" npm run dev
```

Open [http://localhost:5173](http://localhost:5173). There is no dummy-data or query-parameter demo mode; this runs the real application against the hosted API.

## Test CVs

Synthetic fixtures:

- [Anna Schmidt — Data Analyst](test_data/cvs/anna_schmidt_data_analyst_cv.pdf)
- [Benjamin Weber — Backend Engineer](test_data/cvs/benjamin_weber_backend_engineer_cv.pdf)
- [Clara Meyer — UX Researcher](test_data/cvs/clara_meyer_ux_researcher_cv.pdf)
- [David Klein — Cybersecurity](test_data/cvs/david_klein_cybersecurity_cv.pdf)
- [Maya Rodriguez — Product Data](test_data/cvs/maya_rodriguez_product_data_cv.pdf)
- [Nathan Lee — Cloud Security](test_data/cvs/nathan_lee_cloud_security_cv.pdf)

Personal fixtures included with the contributors' consent:

- [Alison Thorpe](test_data/cvs/alison_thorpe.pdf)
- [Ben Theurich](test_data/cvs/ben_theurich_12_25.pdf)
- [Semjon Eschweiler](test_data/cvs/semjon_eschweiler_04_26.pdf)

## Privacy

CV/profile text is sent to OpenAI for structured extraction, identity generation, and roadmap text. Structured contact and link fields are removed before matching; free-text fields are not a general-purpose PII scrubber. The application does not retain uploaded PDFs, extracted CV text, or generated profile artifacts. The browser keeps the current session in memory and clears it on refresh.

Use a synthetic fixture or manual entry if you do not want to submit a personal CV.

## How it works

1. FastAPI validates and extracts an uploaded PDF, or accepts the bounded manual-profile form.
2. OpenAI converts the input into a structured profile. Contact and link fields are removed before the profile continues through matching.
3. The bundled [MIND tech-skills ontology](https://github.com/MIND-TechAI/MIND-tech-ontology) canonicalizes technical skills and supplies synonym and prerequisite relationships.
4. PostgreSQL/pgvector retrieves roles using capability, intent, and identity embeddings, plus explicit skill overlap, interests, and seniority. Each role is scored under three normalized lenses: **current fit** emphasizes present capability and skills, **growth fit** balances present evidence with intent, and **direction fit** emphasizes interests and intended direction.
5. With the default `top_k=9`, the allocator builds a balanced, globally unique shortlist and quota-aware Maximal Marginal Relevance (MMR) selects three **Ready now**, three **Next step**, and three **Aspirational** roles using 75% lens score and 25% title/skill/domain redundancy. Seniority constraints can shift those counts safely. MMR changes membership only; cards are re-sorted by their raw lens score, so percentages remain honest and should be compared within the same section.
6. Career-path generation uses the selected catalog role, ESCO grounding, and computed requirement gaps rather than inventing role requirements.

MIND is pinned to commit [`2367527d1a2f5665f595d6e0518294cc69dfb0fe`](https://github.com/MIND-TechAI/MIND-tech-ontology/tree/2367527d1a2f5665f595d6e0518294cc69dfb0fe). See [third-party notices](THIRD_PARTY_NOTICES.md) for licenses and data provenance.

## Optional: run the full backend locally

This is a maintainer workflow. It requires Python 3.11+, [uv](https://docs.astral.sh/uv/), a private OpenAI key, and a read-only connection to the existing populated Supabase catalog. Credentials are delivered outside GitLab.

The checked-in SQL files are incremental changes and runtime-access configuration. They do **not** reconstruct or populate the production database from an empty Postgres instance.

```powershell
Copy-Item .env.example .env
# Fill OPENAI_API_KEY and the read-only DATABASE_URL in .env.
uv sync --frozen
uv run uvicorn backend.app.main:app --reload --reload-dir backend
```

In a second terminal:

```powershell
cd frontend
npm ci
$env:VITE_API_BASE_URL="http://localhost:8000"
npm run dev
```

The runtime uses only the Postgres `DATABASE_URL`; it does not use a Supabase API or service-role key. Maintainers provision the least-privilege login with [`database/supabase/runtime_reader.sql`](database/supabase/runtime_reader.sql) as described in [DEPLOYMENT.md](DEPLOYMENT.md).

## Verification

Backend and metrics:

```powershell
uv sync --frozen
uv run pytest -q
```

Frontend:

```powershell
cd frontend
npm ci
npm test
npm run lint
npm run build
Get-ChildItem scripts/*.mjs | Sort-Object Name | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

Repository whitespace check:

```powershell
git diff --check
```

## Repository layout

```text
backend/    FastAPI API, CV processing, MIND integration, and role matching
frontend/   React 19, TypeScript, and Vite interface
database/   Incremental Supabase SQL and read-only runtime-role template
metrics/    Evaluation fixtures and aggregate results
test_data/  Six synthetic and three consented personal CV fixtures
```

## Data, models, and limitations

This service uses the ESCO classification of the European Commission.

The user-facing role catalog began with the [IT Job Roles Skills Dataset](https://www.kaggle.com/datasets/dhivyadharunaba/it-job-roles-skills-dataset) and was mapped to ESCO occupation and skill records. German salary bands use Bundesagentur für Arbeit/KldB occupational-group statistics. Local embeddings use [`BAAI/bge-base-en-v1.5`](https://huggingface.co/BAAI/bge-base-en-v1.5); OpenAI models perform profile parsing, summaries, and roadmap generation.

Recommendations are guidance, not hiring or financial advice. The role catalog is static, salary values are broad German occupational-group estimates, scanned/image-only PDFs may not contain extractable text, and generated wording can vary between requests.

## Contributors and license

Zitong Fu, Yuxuan Qian, Benjamin Theurich, Anh Tu Ly, Moritz Busch, Anthea Kleiner, Semjon Eschweiler, and Vanessa Fu.

Career Compass code is licensed under the [MIT License](LICENSE). Third-party data, models, and the MIND ontology remain under their respective terms in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
