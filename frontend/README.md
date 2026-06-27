# Career Compass — Frontend

Multi-stage Career Compass UI (originally designed in Lovable), integrated into
this repository as a conventional single-page React app.

## Stack

- **React 19** + **TypeScript**
- **Vite 7** (client-side SPA — no SSR)
- **Tailwind CSS v4**
- **Zustand** for client state (`src/state/useStageStore.ts`)
- **Framer Motion** for animation
- **lucide-react** for icons

> This was migrated off Lovable's TanStack Start + Cloudflare Workers setup to a
> standard Vite SPA. If you later need server-side rendering or a multi-page
> router, add `@tanstack/react-router` (client-only) or TanStack Start back
> deliberately. To re-add shadcn/ui primitives, run `npx shadcn@latest init`.

## Prerequisites

- Node.js 20+ (developed against Node 24)
- Backend running on `http://localhost:8000` (see the project root `SETUP.md`).
  For the Matching stage, the backend also needs an OpenAI key and the populated
  pgvector DB (see `backend/app/features/role_matching/router.py`).

The backend base URL defaults to `http://localhost:8000` and can be overridden
with `VITE_API_BASE_URL` (e.g. in a `.env` file).

## Setup

```powershell
cd frontend
npm install
```

## Development

```powershell
npm run dev      # http://localhost:5173 (matches backend CORS)
```

### Demo fixtures

Use frontend-only fixtures when working on layout without paying for CV parsing
or LLM role analysis:

- `http://localhost:5173/?demo=recap` opens the parsed-profile recap.
- `http://localhost:5173/?demo=roles` opens role selection with 9 demo matches.
- `http://localhost:5173/?demo=1` is an alias for role selection.
- `http://localhost:5173/?demo=focus` opens selected roadmaps and gap analysis.

This is only a formatting aid. The normal upload, manual entry, and backend API
flow is unchanged.

## Build / lint

```powershell
npm run build
npm run lint
```

## Project layout

```
index.html           SPA entry document (fonts, #root)
src/
  main.tsx           App bootstrap — mounts CareerCompassApp, imports styles.css
  types.ts           Shared UI view-model types
  components/
    compass/         App-specific feature components
      stages/        Entry → Recap → Matching → Directions → Focus screens
      modals/        DeepDiveModal shell + RoleDetailModal (real role breakdown)
      ui/            Compass-specific primitives (GlassCard, PillButton, …)
  state/             Zustand store driving stage navigation + profile + async actions
  lib/               api client (api.ts), config, cvData/roleView mappers, cn helper
  styles.css         Tailwind v4 + design tokens
```

## Backend wiring

The app talks to the FastAPI backend (no mock data). The flow:

1. **Entry** — upload a PDF (`POST /api/v1/parse-cv`) or fill the manual form
   (assembled into `CVData` client-side).
2. **Recap** — edit the parsed profile; the career identity comes from
   `POST /api/v1/prompt-engineering/starter-profile`.
3. **Matching** — `POST /api/v1/roles/match` returns ranked ESCO roles.
4. **Directions / Focus** — render those `RoleMatch` results.

The typed client is `src/lib/api.ts`; mappers between the backend schema and the
UI live in `src/lib/cvData.ts` and `src/lib/roleView.ts`.

`BACKEND_INTEGRATION.md` documents what is connected, the derive-and-hide
decisions, and the remaining backend gaps (skill vectors, viability, peers,
salary/duration, synthetic roadmaps) that keep some UI hidden.
