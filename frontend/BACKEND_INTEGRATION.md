# Frontend ↔ Backend integration notes

The Lovable UI is now **wired to the FastAPI backend**. The mock data layer
(`frontend/src/data/mock.ts`) has been **deleted**. This document records what is
connected, and the remaining backend gaps that forced parts of the UI to be
hidden.

> No backend code was changed as part of this integration. Everything here is
> frontend-only, using the existing endpoints.

---

## 1. What is connected

The typed client lives in `frontend/src/lib/api.ts` (base URL in
`frontend/src/lib/config.ts`, overridable via `VITE_API_BASE_URL`).

| Stage              | Call                                                  | Notes                                                            |
| ------------------ | ----------------------------------------------------- | ---------------------------------------------------------------- |
| Entry (upload)     | `POST /api/v1/parse-cv` (multipart `file`) → `CVData` | Seeds the editable Recap lists.                                  |
| Entry (manual)     | `POST /api/v1/manual-cv` (`ManualCVInput`) → `CVData` | Backend maps the thin form DTO to full `CVData`.                 |
| Recap (identity)   | `POST /api/v1/prompt-engineering/starter-profile`     | Sends a client-built `ConfirmedCVData`; uses `starter_identity`. |
| Matching           | `POST /api/v1/roles/match` (`{ cv_data, top_k: 6 }`)  | Requires the populated pgvector DB.                              |
| Directions / Focus | _from match results_                                  | Rendered from `RoleMatch` (no extra calls).                      |

### Manual entry (`POST /api/v1/manual-cv`)

The manual path now goes through the backend instead of being assembled
client-side. The frontend posts a thin `ManualCVInput` DTO and receives the same
`CVData` shape as `parse-cv`, so both entry paths converge on identical
downstream behaviour. The Entry form is tiered to stay uncluttered:

- **Tier 1 (always visible):** current role, seniority, years of experience,
  degree + school, technical skills, interests.
- **Tier 2 (collapsible "Add more context"):** most recent job (role / company /
  from / to), professional summary, soft skills, one language + level.
- **Tier 3 (Recap screen):** multiple experiences, projects, certifications, etc.

Backend mapping lives in `backend/app/features/cv_confirmation/manual_service.py`
(`build_cv_data_from_manual_input`), with the DTO in `manual_schemas.py` and the
route in `cv_confirmation/router.py`. It validates that at least a current role
or one technical skill is provided (HTTP 422 otherwise) and trims/dedupes lists.

Key frontend modules:

- `src/lib/api.ts` — typed fetch client + backend types; surfaces FastAPI `detail`.
- `src/lib/cvData.ts` — `manualFormToInput` (form → `ManualCVInput`),
  `CVData ↔ Recap` mappers, `toConfirmedCvData` (mirrors backend
  `to_confirmed_cv_data`, all sections marked confirmed), `applyEditsToCvData`
  (Recap edits flow into matching/identity).
- `src/lib/roleView.ts` — `RoleMatch → RoleView` for cards + detail.
- `src/state/useStageStore.ts` — holds `cvData`, editable lists, `identity`,
  `roleMatches`; async actions `uploadCv`, `submitManualProfile`,
  `generateIdentity`, `runMatching`.

CORS already allows `http://localhost:5173` (the dev origin in `vite.config.ts`).

## 2. Decisions taken (derive-and-hide)

Where the backend has no data source, we **derived a simple value from real
fields** or **hid the feature** rather than faking data:

- **Skill confidence %** (Recap): derived from `proficiency_indication`
  (expert→90, advanced→80, intermediate→70, beginner→50, default 65) in
  `deriveConfidence`. Not a real backend score.
- **Identity `archetype`**: derived from `personal_info.current_role` +
  `profile_summary.current_seniority_level`. Only `lead` is the real LLM
  `starter_identity`. If `starter-profile` fails, the whole identity falls back
  to CV-derived text.
- **Role `trackLabel`**: `RoleMatch.isco_label` (falls back to "Role").
- **Role detail** (Focus + `RoleDetailModal`): built from `RoleMatch`
  essential/optional skills + knowledge and the match `analysis` text.

## 3. Hidden / removed UI (no backend source)

These components were deleted because nothing in the backend can populate them:

- `dashboard/RadarOverlay`, `dashboard/ScoreBar`, `dashboard/BentoCard`,
  `dashboard/useMouseTilt` (skill-vector radar + score bars).
- `modals/SkillGapModal` (per-axis skill vectors).
- `modals/ViabilityModal` (`viability { rate, medianMonths, sample }`).
- `modals/PeersModal` (peer stats).
- `modals/MatchingModal` (4-dim `skills/experience/difficulty/market` breakdown).
- `modals/CareerPathModal` (synthetic milestone roadmap, bootcamps, live jobs).

`DeepDiveModal` was kept and repurposed by `modals/RoleDetailModal` for the real
role breakdown.

Also dropped from the Directions cards: **`durationMonths`** and
**`targetSalary`** (no source).

## 4. Concrete asks for the backend team (to restore hidden UI)

1. **Role enrichment** on `RoleMatch` (or a new endpoint): per-role
   `duration_months`, `target_salary`, and a `path_steps[]` roadmap
   (current role → steps → target). Restores the Focus roadmap + card metadata.
2. **Skill-gap vectors**: a fixed set of skill axes + a 0..1 vector for both the
   candidate and each role. Restores `SkillGapModal` + radar.
3. **Decision-support data**: viability (`rate`, `median_months`, `sample`),
   `peers[]`, structured `matching` sub-scores + `rationale[]`, `bootcamps[]`,
   live `jobs[]`. Restores the viability/peers/matching/career-path modals.
4. **Numeric skill confidence** (0–100) instead of free-text
   `proficiency_indication`.
5. _(Optional)_ Return identity `archetype` + `lead` separately instead of one
   `starter_identity` string.

## 5. Cross-cutting concerns

- **State/session**: everything is in memory (Zustand). All backend calls are
  stateless and take the full `CVData` / `ConfirmedCVData` in the body; the
  frontend carries the parsed CV between stages. No session/IDs needed.
- **Confirmation envelope**: the frontend builds `ConfirmedCVData` client-side
  in `toConfirmedCvData` (all sections marked confirmed, no edited-field
  tracking). If the backend later adds a confirm endpoint, swap this helper.
- **`roles/match` prerequisite**: requires the pgvector DB to be populated (run
  the three scripts noted in `backend/app/features/role_matching/router.py`).
  When unavailable, the Matching screen shows an inline error and a way back.
- **Error shape**: backend raises `HTTPException(status_code, detail=...)`; the
  client throws `ApiError` carrying `detail`, surfaced in the UI.
