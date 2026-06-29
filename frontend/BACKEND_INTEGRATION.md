# Frontend <-> Backend Integration Notes

The React app is wired to the FastAPI backend for the MVP flow. Demo fixtures
exist only behind `?demo=...` URLs for layout work; normal upload, manual entry,
matching, gap analysis, and career roadmap generation use backend calls.

## Connected Flow

The typed client lives in `frontend/src/lib/api.ts`. Its base URL is defined in
`frontend/src/lib/config.ts` and can be overridden with `VITE_API_BASE_URL`.

| Stage        | Call                                        | Notes                                                               |
| ------------ | ------------------------------------------- | ------------------------------------------------------------------- |
| Entry upload | `POST /api/v1/profile-pipeline/parse-cv`    | Uploads a PDF and returns `ProfilePipelineResponse`.                |
| Entry manual | `POST /api/v1/profile-pipeline/manual-cv`   | Posts `ManualCVInput` and returns the same pipeline response shape. |
| Recap        | no extra backend call                       | Edits happen in frontend state and are merged back into `CVData`.   |
| Matching     | `POST /api/v1/roles/match`                  | Sends `UserCareerProfile`, `top_k: 9`, `mode: "balanced"`.          |
| Gap analysis | `POST /api/v1/roles/{role_id}/gap-analysis` | Sends `ConfirmedCVData` for the selected role.                      |
| Career path  | `POST /api/v1/roles/{role_id}/career-path`  | Sends `ConfirmedCVData`; response includes `requirement_breakdown`. |

Balanced matching displays up to 3 roles per bucket, so the response can contain
fewer than 9 roles when a bucket has fewer qualified candidates.

```text
profile-pipeline/* -> frontend profile conversion -> /roles/match -> gap API -> path API
```

## Manual Entry

The manual path goes through the profile pipeline instead of being assembled
client-side. The frontend posts a `ManualCVInput` DTO and receives
`ProfilePipelineResponse`, so manual entry and PDF upload converge before Recap.

The Entry form stays tiered:

- **Tier 1 (always visible):** current role, seniority, years of experience, degree + school, technical skills, interests.
- **Tier 2 (collapsible "Add more context"):** most recent job, professional summary, soft skills, one language + level.
- **Tier 3 (Recap screen):** multiple experiences, projects, certifications, and other profile details.

Backend manual mapping lives in
`backend/app/features/cv_confirmation/manual_service.py`, with the request DTO in
`manual_schemas.py`. The profile-pipeline route wraps that mapping and returns
privacy-stripped CV data plus the embedding profile.

## Key Frontend Modules

- `src/lib/api.ts` - typed fetch client and backend DTOs.
- `src/lib/cvData.ts` - manual form DTO mapping, `CVData` recap projection, recap edit merge, `UserCareerProfile` conversion, and `ConfirmedCVData` envelope creation.
- `src/lib/roleView.ts` - `RoleMatch` to UI role card/detail mapping.
- `src/lib/pathPreparation.ts` - waits until selected role gap/path calls have either succeeded or failed.
- `src/lib/demoData.ts` - fixture-only data for `?demo=...` URLs.
- `src/state/useStageStore.ts` - owns stage navigation, profile state, selected roles, and all async calls.

## Data Decisions

- **Skill confidence %:** Recap derives this from `proficiency_indication` in `deriveConfidence`; it is a UI confidence display, not a backend score.
- **Identity:** The profile pipeline returns `embedding_profile.career_identity_summary`; Recap edits can change the identity text before matching and path generation.
- **Role detail:** Built from `RoleMatch`, gap reports, and career path reports.
- **Selected roles:** Users can select up to 3 roles; the store then loads both gap analysis and career paths for each selected role.

## Cross-Cutting Concerns

- CORS allows `http://localhost:5173` and `http://127.0.0.1:5173`.
- State is in memory via Zustand; refreshing resets the current session.
- Backend calls are stateless and receive the relevant profile data in the request body.
- The frontend builds the `ConfirmedCVData` envelope client-side in `toConfirmedCvData`.
- Backend errors use FastAPI `detail`; the client surfaces them through `ApiError`.

## Current Limitations

- Demo fixtures are intentionally synthetic and only available through query params.
- `roles/match`, gap analysis, and career paths require the populated database and model configuration.
- Older direct parsing/manual endpoints still exist on the backend, but the frontend uses `profile-pipeline/*`.
