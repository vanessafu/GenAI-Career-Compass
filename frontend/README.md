# Career Compass - Frontend

Multi-stage Career Compass UI integrated as a conventional single-page React
app.

## Stack

- **React 19** + **TypeScript**
- **Vite 7** client-side SPA
- **Tailwind CSS v4**
- **Zustand** for client state (`src/state/useStageStore.ts`)
- **Framer Motion** for animation
- **lucide-react** for icons

## Prerequisites

- Node.js 20+ (developed against Node 24)
- Backend running on `http://localhost:8000` (see the project root `SETUP.md`)
- For matching, gap analysis, and career paths: an OpenAI key plus the populated
  pgvector/Supabase database

The backend base URL defaults to `http://localhost:8000` and can be overridden
with `VITE_API_BASE_URL`, for example in a frontend `.env` file.

## Setup

```powershell
cd frontend
npm install
```

## Development

```powershell
npm run dev      # http://localhost:5173 (matches backend CORS)
```

### Demo Fixtures

Use frontend-only fixtures when working on layout without paying for CV parsing
or LLM role analysis:

- `http://localhost:5173/?demo=recap` opens the parsed-profile recap.
- `http://localhost:5173/?demo=roles` opens role selection with 9 demo matches.
- `http://localhost:5173/?demo=1` is an alias for role selection.
- `http://localhost:5173/?demo=focus` opens selected roadmaps and gap analysis.

This is only a formatting aid. The normal upload, manual entry, and backend API
flow is unchanged.

## Build / Lint

```powershell
npm run build
npm run lint
```

## Project Layout

```text
index.html           SPA entry document (fonts, #root)
src/
  main.tsx           App bootstrap; mounts CareerCompassApp and imports styles.css
  types.ts           Shared UI view-model types
  components/
    compass/         App-specific feature components
      stages/        Entry -> Recap -> Matching -> Directions -> Preparing paths -> Focus
      modals/        DeepDiveModal shell, RoleDetailModal, skill gap, and roadmap surfaces
      ui/            Compass-specific primitives such as GlassCard and PillButton
  state/             Zustand store driving stage navigation, profile state, and async actions
  lib/               API client, config, CV/profile mappers, role views, roadmap helpers
  styles.css         Tailwind v4 plus design tokens
```

## Backend Wiring

The app talks to the FastAPI backend; normal upload/manual entry uses backend
calls, not fixture data. The flow:

1. **Entry** - upload a PDF through `POST /api/v1/profile-pipeline/parse-cv` or submit manual fields through `POST /api/v1/profile-pipeline/manual-cv`.
2. **Recap** - edit the returned `CVData`; the identity summary comes from `embedding_profile.career_identity_summary`.
3. **Matching** - convert edited `CVData` into `UserCareerProfile`, then call `POST /api/v1/roles/match` with `top_k: 9`.
4. **Directions** - select up to 3 roles from the bucketed `RoleMatch` results.
5. **Preparing paths** - for each selected role, call `POST /api/v1/roles/{role_id}/gap-analysis` and `POST /api/v1/roles/{role_id}/career-path`.
6. **Focus** - render the returned gap reports and career path reports.

The typed client is `src/lib/api.ts`; mappers between backend schemas and the
UI live in `src/lib/cvData.ts`, `src/lib/roleView.ts`, and
`src/lib/pathPreparation.ts`.

`BACKEND_INTEGRATION.md` documents the exact endpoint contracts, frontend
modules, fixture-only demo mode, and current limitations.
