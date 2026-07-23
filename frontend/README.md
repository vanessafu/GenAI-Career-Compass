# Career Compass frontend

React 19, TypeScript, Vite, and Zustand interface for the Career Compass API. The root [README](../README.md) contains the evaluator walkthrough, CV fixtures, architecture, privacy disclosure, and optional backend setup.

## Run with the hosted backend

Requires Node.js 20.19+ or 22.12+. No API keys or database credentials are needed.

PowerShell:

```powershell
npm ci
$env:VITE_API_BASE_URL="https://career-compass-hqrdul4iqa-ey.a.run.app"
npm run dev
```

macOS/Linux:

```bash
npm ci
VITE_API_BASE_URL="https://career-compass-hqrdul4iqa-ey.a.run.app" npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

To use a local backend instead, set `VITE_API_BASE_URL=http://localhost:8000`. There is no fixture or query-parameter demo mode; use the real API with a linked CV fixture or manual entry.

## Flow

1. Upload a PDF or submit a manual profile.
2. Review and edit the returned profile.
3. Request up to nine role recommendations.
4. Select up to three roles.
5. Load each selected role's grounded requirement breakdown and career roadmap.

State remains in browser memory and is cleared on refresh. The typed API client is [`src/lib/api.ts`](src/lib/api.ts); profile mapping and recap merging are in [`src/lib/cvData.ts`](src/lib/cvData.ts); stage state is in [`src/state/useStageStore.ts`](src/state/useStageStore.ts).

## Verification

```powershell
npm ci
npm test
npm run lint
npm run build
Get-ChildItem scripts/*.mjs | Sort-Object Name | ForEach-Object {
  node $_.FullName
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```
