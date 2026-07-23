# Cloud Run deployment

This is a maintainer procedure. The Dockerfile builds the Vite frontend and serves it with the FastAPI API from one Cloud Run service. Deploy only a clean commit that has passed the checks in the root README.

## 1. Prepare the Supabase runtime login

The hosted database remains in Supabase; deployment does not create a local database.

1. Rotate any previously exposed owner/database password.
2. In the Supabase SQL Editor, run [`database/supabase/runtime_reader.sql`](database/supabase/runtime_reader.sql) as the project owner. The script is idempotent and contains no password.
3. Set a generated password privately. Do not save the real command in a tracked file:

```sql
alter role career_compass_runtime password '<generated-private-password>';
```

4. Build a `DATABASE_URL` for `career_compass_runtime` using the connection details shown by the Supabase **Connect** dialog. Prefer the direct connection for a reachable persistent backend; use the session pooler on port 5432 when the runtime needs IPv4.
5. Test the URL as that login:

```sql
select count(*) from public.career_roles;
update public.career_roles set job_title = job_title where false;
```

The `SELECT` must succeed. The zero-row `UPDATE` must fail with a read-only or permission error. The runtime needs no Supabase API or service-role key.

The SQL under `database/supabase/migrations/` is incremental and does not rebuild the populated catalog from an empty database.

## 2. Store secrets

In Google Secret Manager, create or add versions for:

- `OPENAI_API_KEY`: the existing budget-capped project key.
- `DATABASE_URL`: the read-only runtime URL created above.

Never pass secret values as `--set-env-vars`, place them in deployment commands, or commit them to the repository. Give the Cloud Run service account Secret Manager access if this is the first deployment.

## 3. Deploy

Set non-secret identifiers locally:

```powershell
$env:GCLOUD_PROJECT="replace-with-project-id"
$env:GCLOUD_REGION="europe-west3"
gcloud config set project $env:GCLOUD_PROJECT
```

Deploy from the repository root:

```powershell
gcloud run deploy career-compass `
  --project $env:GCLOUD_PROJECT `
  --source . `
  --region $env:GCLOUD_REGION `
  --allow-unauthenticated `
  --memory 4Gi `
  --cpu 4 `
  --concurrency 4 `
  --max-instances 1 `
  --set-secrets OPENAI_API_KEY=OPENAI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest `
  --set-env-vars OPENAI_TEMPERATURE=1
```

For later deployments, the existing service configuration is retained:

```powershell
gcloud run deploy career-compass `
  --project $env:GCLOUD_PROJECT `
  --source . `
  --region $env:GCLOUD_REGION
```

## 4. Verify the deployed revision

- Open the service URL and complete a manual profile.
- Upload one synthetic CV linked from the root README.
- Select three roles and open their roadmaps.
- Run the frontend locally with `VITE_API_BASE_URL` set to the service URL.
- Confirm invalid/non-PDF uploads are rejected and no raw CV or pipeline-output directory is created.
- Confirm the service still has one maximum instance and the OpenAI project budget remains enabled.

The public service intentionally uses one instance, a small in-process request limit, a read-only database role, and the OpenAI budget as class-demo safeguards. Add managed authentication or distributed rate limiting only if the service is expanded beyond that scope.
