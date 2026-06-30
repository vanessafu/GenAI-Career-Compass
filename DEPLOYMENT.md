# Minimal Cloud Run Deployment

This deploys one Cloud Run service that serves both the FastAPI backend and the
built Vite frontend.

## 1. Pick a project and enable services

```powershell
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com
```

## 2. Store secrets

```powershell
$env:OPENAI_API_KEY_VALUE="sk-..."
$env:DATABASE_URL_VALUE="postgresql://postgres.[PROJECT-ID]:[PASSWORD]@aws-1-eu-central-1.pooler.supabase.com:6543/postgres"

[System.IO.File]::WriteAllText("$env:TEMP\openai_api_key.txt", $env:OPENAI_API_KEY_VALUE, [System.Text.UTF8Encoding]::new($false))
[System.IO.File]::WriteAllText("$env:TEMP\database_url.txt", $env:DATABASE_URL_VALUE, [System.Text.UTF8Encoding]::new($false))

gcloud secrets create OPENAI_API_KEY --data-file="$env:TEMP\openai_api_key.txt"
gcloud secrets create DATABASE_URL --data-file="$env:TEMP\database_url.txt"

Remove-Item "$env:TEMP\openai_api_key.txt", "$env:TEMP\database_url.txt"
```

For later rotations, write the new value to a no-newline temp file and run
`gcloud secrets versions add SECRET_NAME --data-file=PATH`.

## 3. Deploy

```powershell
gcloud run deploy career-compass `
  --source . `
  --region europe-west3 `
  --allow-unauthenticated `
  --memory 4Gi `
  --cpu 4 `
  --concurrency 1 `
  --max-instances 1 `
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest `
  --set-env-vars PIPELINE_OUTPUT_DIR=/tmp/pipeline,OPENAI_TEMPERATURE=1
```

Cloud Run prints the service URL after deployment. Share that URL with testers
and send the feedback survey link separately.

## Redeploy after code changes

After changes are merged or pushed to the branch you want to deploy, run this
from the repo root:

```powershell
git pull

gcloud run deploy career-compass `
  --project careercompass-501022 `
  --source . `
  --region europe-west3
```

This uploads the current source, rebuilds the Docker image from `Dockerfile`,
and creates a new Cloud Run revision. Existing secrets, environment variables,
memory, CPU, concurrency, and instance limits stay on the service unless you
change them with `gcloud run services update`.

## 4. Before sharing

Set an OpenAI project budget or usage limit. The Cloud Run URL is public, so the
budget is the safety net for this short feedback test.

## Local Docker Smoke Test

```powershell
docker build -t career-compass .
docker run --rm -p 8080:8080 --env-file .env -e PORT=8080 -e PIPELINE_OUTPUT_DIR=/tmp/pipeline -e OPENAI_TEMPERATURE=1 career-compass
```

Open `http://localhost:8080`.
