# Feedback Quick Wins Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement feedback items 1-7: mobile overflow, visible errors, preserved manual input, clearer add controls, date validation/formatting, no placeholder dashes, and recap suggestions.

**Architecture:** Keep this frontend-only. Reuse the existing React stage files, Zustand store, source-check scripts, and native `datalist` for recap suggestions. No new packages, no backend changes, no new design system layer.

**Tech Stack:** React 19, TypeScript, Zustand, Vite, Node source-check scripts.

---

## Subagent Split

- Subagent A: `useStageStore.ts` + `EntryStage.tsx` for manual draft persistence, manual-card errors, mobile input layout, and entry date validation.
- Subagent B: `RecapStage.tsx` + shared presets for add buttons, dashes, recap date validation, and native suggestions.
- Subagent C: `package.json` + `frontend/scripts/check-feedback-quick-wins.mjs` for regression checks and final verification.

Do not run A and B in parallel if both are editing `frontend/src/lib/profilePresets.ts`. Otherwise they can work independently after Task 1 lands.

## File Map

- Create: `frontend/scripts/check-feedback-quick-wins.mjs`
- Create: `frontend/src/lib/profilePresets.ts`
- Modify: `frontend/package.json`
- Modify: `frontend/src/state/useStageStore.ts`
- Modify: `frontend/src/components/compass/stages/EntryStage.tsx`
- Modify: `frontend/src/components/compass/stages/RecapStage.tsx`
- Modify: `frontend/src/styles.css`

---

### Task 1: Add The Failing Regression Check

**Files:**
- Create: `frontend/scripts/check-feedback-quick-wins.mjs`
- Modify: `frontend/package.json`

- [ ] **Step 1: Create the check script**

Create `frontend/scripts/check-feedback-quick-wins.mjs`:

```js
import { readFile } from "node:fs/promises";

const entry = await readFile(
  new URL("../src/components/compass/stages/EntryStage.tsx", import.meta.url),
  "utf8",
);
const recap = await readFile(
  new URL("../src/components/compass/stages/RecapStage.tsx", import.meta.url),
  "utf8",
);
const store = await readFile(new URL("../src/state/useStageStore.ts", import.meta.url), "utf8");
const styles = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
const pkg = await readFile(new URL("../package.json", import.meta.url), "utf8");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(pkg.includes("test:feedback-quick-wins"), "package.json needs the quick-win test script.");
assert(store.includes("manualDraft") && store.includes("setManualDraft"), "Manual entry draft must persist in Zustand.");
assert(entry.includes("setManualDraft("), "EntryStage must save manual form data before leaving the stage.");
assert(entry.includes("showManualError"), "EntryStage must show manual validation errors inside the manual card.");
assert(entry.includes("isMonthRangeInvalid"), "EntryStage must reject end months before start months.");
assert(entry.includes("box-sizing: border-box;"), "Manual inputs need border-box sizing.");
assert(entry.includes("sm:grid-cols-"), "Manual entry grids must collapse on mobile.");
assert(recap.includes("cc-skill-presets"), "Recap skills need native suggestions.");
assert(recap.includes("cc-role-presets"), "Recap experience role input needs native suggestions.");
assert(recap.includes("cc-degree-presets"), "Recap education degree input needs native suggestions.");
assert(recap.includes("aria-label={label}"), "Recap add inputs need a real add button.");
assert(!recap.includes('issuer: "—"'), "Certifications must not store placeholder issuers.");
assert(!recap.includes('detail: "—"'), "Projects must not store placeholder details.");
assert(recap.includes("invalidYearRange"), "Recap add rows must reject impossible year ranges.");
assert(styles.includes("max-width: 100%;"), "Shared chip styles must cap long labels.");
```

- [ ] **Step 2: Add the npm script**

In `frontend/package.json`, add this script next to the other `test:*` scripts:

```json
"test:feedback-quick-wins": "node scripts/check-feedback-quick-wins.mjs"
```

- [ ] **Step 3: Run it and confirm it fails**

Run:

```powershell
cd frontend
npm run test:feedback-quick-wins
```

Expected: FAIL with at least one missing quick-win assertion.

- [ ] **Step 4: Commit**

```powershell
git add frontend/package.json frontend/scripts/check-feedback-quick-wins.mjs
git commit -m "test: add feedback quick wins regression check"
```

---

### Task 2: Share Existing Presets And Cap Long Chips

**Files:**
- Create: `frontend/src/lib/profilePresets.ts`
- Modify: `frontend/src/components/compass/stages/EntryStage.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: Create shared preset constants**

Create `frontend/src/lib/profilePresets.ts`:

```ts
export const ROLE_PRESETS = [
  "Senior Backend Developer",
  "Backend Developer",
  "Full-Stack Engineer",
  "Frontend Engineer",
  "DevOps Engineer",
  "Tech Lead",
  "Engineering Manager",
  "Data Engineer",
  "Cloud Engineer",
  "Product Designer",
];

export const DEGREE_LEVELS = [
  "B.Sc.",
  "M.Sc.",
  "B.A.",
  "M.A.",
  "B.Eng.",
  "M.Eng.",
  "PhD",
  "MBA",
  "Abitur",
  "Bootcamp",
  "Other",
];

export const LANGUAGE_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Native"];

export const SKILL_PRESETS = [
  "Python",
  "Java",
  "PostgreSQL",
  "RESTful APIs",
  "Docker",
  "AWS EC2",
  "Git",
  "Microservices Architecture",
  "TypeScript",
  "React",
  "Node.js",
  "Go",
  "Kubernetes",
  "GraphQL",
  "Redis",
  "System Design",
  "Mentoring",
];
```

- [ ] **Step 2: Import presets in EntryStage**

In `frontend/src/components/compass/stages/EntryStage.tsx`, add:

```ts
import {
  DEGREE_LEVELS,
  LANGUAGE_LEVELS,
  ROLE_PRESETS,
  SKILL_PRESETS,
} from "@/lib/profilePresets";
```

Delete the local `ROLE_PRESETS`, `DEGREE_LEVELS`, `LANGUAGE_LEVELS`, and `SKILL_PRESETS` arrays from `EntryStage.tsx`.

- [ ] **Step 3: Cap chip width in shared CSS**

In `frontend/src/styles.css`, update the existing `.removable-chip` rule:

```css
.removable-chip {
  --removable-chip-fade: color-mix(in oklab, var(--brand) 10%, white 90%);
  position: relative;
  isolation: isolate;
  max-width: 100%;
  overflow: hidden;
}
```

Keep the existing `.removable-chip-label` ellipsis rule.

- [ ] **Step 4: Run the existing chip check**

Run:

```powershell
cd frontend
npm run test:scroll
node scripts/check-removable-chip-hover.mjs
```

Expected: both commands PASS.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/lib/profilePresets.ts frontend/src/components/compass/stages/EntryStage.tsx frontend/src/styles.css
git commit -m "fix: share profile presets and cap long chips"
```

---

### Task 3: Persist Manual Input And Surface Entry Errors Locally

**Files:**
- Modify: `frontend/src/state/useStageStore.ts`
- Modify: `frontend/src/components/compass/stages/EntryStage.tsx`

- [ ] **Step 1: Add manual draft state to the store**

In `frontend/src/state/useStageStore.ts`, extend the imports from `@/types`:

```ts
import type {
  AnalyzedSkill,
  CertificationItem,
  EducationItem,
  ExperienceItem,
  Identity,
  ManualProfileForm,
  ProjectItem,
} from "@/types";
import { emptyManualProfileForm } from "@/types";
```

Add these fields to `type Store`:

```ts
  manualDraft: ManualProfileForm;
  setManualDraft: (draft: ManualProfileForm) => void;
```

Add this to `initialState`:

```ts
  manualDraft: emptyManualProfileForm,
```

Add this store action near `clearError`:

```ts
  setManualDraft: (manualDraft) => set({ manualDraft }),
```

- [ ] **Step 2: Initialize EntryStage from the draft**

In `EntryStage.tsx`, read and use the draft:

```ts
  const manualDraft = useStageStore((s) => s.manualDraft);
  const setManualDraft = useStageStore((s) => s.setManualDraft);
```

Change the manual state initializers to use `manualDraft`, for example:

```ts
  const [role, setRole] = useState(manualDraft.currentRole);
  const [education, setEducation] = useState(manualDraft.education);
  const [experience, setExperience] = useState(manualDraft.experience);
  const [skills, setSkills] = useState<string[]>(manualDraft.skills);
  const [interests, setInterests] = useState<string[]>(manualDraft.interests);
  const [softSkills, setSoftSkills] = useState<string[]>(manualDraft.softSkills);
  const [languages, setLanguages] = useState(manualDraft.languages);
  const [projects, setProjects] = useState(manualDraft.projects);
  const [certifications, setCertifications] = useState(manualDraft.certifications);
  const [summary, setSummary] = useState(manualDraft.summary);
```

- [ ] **Step 3: Save draft changes while editing**

Add this `useEffect` after the manual state declarations:

```ts
  useEffect(() => {
    setManualDraft({
      currentRole: role,
      education,
      experience,
      skills,
      interests,
      softSkills,
      languages,
      projects,
      certifications,
      summary,
    });
  }, [
    role,
    education,
    experience,
    skills,
    interests,
    softSkills,
    languages,
    projects,
    certifications,
    summary,
    setManualDraft,
  ]);
```

- [ ] **Step 4: Add local manual errors and date validation**

Add these helpers inside `EntryStage` before `analyzeCv`:

```ts
  const showManualError = (message: string) => {
    setFormError(message);
    setManualOpen(true);
    window.setTimeout(() => {
      manualCardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 0);
  };

  const isMonthRangeInvalid = (start: string, end: string) =>
    Boolean(start.trim() && end.trim() && start.trim() > end.trim());
```

Use `showManualError(...)` instead of `setFormError(...)` for manual validation failures in `buildManualProfile`.

After `educationOut`, `experienceOut`, and `projectsOut` are computed, add:

```ts
    if (educationOut.some((item) => isMonthRangeInvalid(item.startDate, item.endDate))) {
      showManualError("Education end date cannot be before start date.");
      return;
    }
    if (experienceOut.some((item) => isMonthRangeInvalid(item.startDate, item.endDate))) {
      showManualError("Experience end date cannot be before start date.");
      return;
    }
    if (projectsOut.some((item) => isMonthRangeInvalid(item.startDate, item.endDate))) {
      showManualError("Project end date cannot be before start date.");
      return;
    }
```

- [ ] **Step 5: Render the error inside the manual card**

Inside the manual form body, just above the helper text that starts with the required-field marker, add:

```tsx
                  {formError && manualOpen && (
                    <div
                      className="rounded-xl border border-red-300/60 bg-red-50/80 px-3 py-2 text-[12.5px] text-red-700"
                      role="alert"
                    >
                      {formError}
                    </div>
                  )}
```

Change the existing top-level alert condition to:

```tsx
        {formError && !parsing && !manualOpen && (
```

- [ ] **Step 6: Make manual inputs mobile-safe**

In the inline `.manual-input` CSS in `EntryStage.tsx`, add:

```css
          box-sizing: border-box;
          min-width: 0;
          max-width: 100%;
```

Change fixed manual grids that currently use only `grid-cols-2` or `grid-cols-3` to responsive classes, for example:

```tsx
className="grid grid-cols-1 gap-2.5 sm:grid-cols-2"
className="grid grid-cols-1 gap-2.5 sm:grid-cols-3"
```

- [ ] **Step 7: Add real buttons to Entry tag inputs**

In `SkillTypeahead` and `PlainTagInput`, add a small button after the input:

```tsx
      <button
        type="button"
        onClick={() => onAdd(draft)}
        className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[color:var(--brand)]/10 text-[color:var(--brand)] transition hover:bg-[color:var(--brand)]/15"
        aria-label="Add"
      >
        <Plus size={11} />
      </button>
```

- [ ] **Step 8: Run checks**

Run:

```powershell
cd frontend
npm run test:feedback-quick-wins
npm run build
```

Expected: the quick-win check may still fail on recap assertions. Build must PASS.

- [ ] **Step 9: Commit**

```powershell
git add frontend/src/state/useStageStore.ts frontend/src/components/compass/stages/EntryStage.tsx
git commit -m "fix: preserve manual entry and show inline errors"
```

---

### Task 4: Fix Recap Add Rows, Dashes, Dates, And Suggestions

**Files:**
- Modify: `frontend/src/components/compass/stages/RecapStage.tsx`

- [ ] **Step 1: Import shared presets**

Add:

```ts
import { DEGREE_LEVELS, ROLE_PRESETS, SKILL_PRESETS } from "@/lib/profilePresets";
```

- [ ] **Step 2: Add native datalists**

Inside `RecapStage`, just inside the top-level returned `<div>`, render:

```tsx
      <PresetDatalist id="cc-skill-presets" options={SKILL_PRESETS} />
      <PresetDatalist id="cc-role-presets" options={ROLE_PRESETS} />
      <PresetDatalist id="cc-degree-presets" options={DEGREE_LEVELS} />
```

Add this helper near the other building blocks:

```tsx
function PresetDatalist({ id, options }: { id: string; options: string[] }) {
  return (
    <datalist id={id}>
      {options.map((option) => (
        <option key={option} value={option} />
      ))}
    </datalist>
  );
}
```

- [ ] **Step 3: Make AddPill a real add control**

Replace `AddPill` with:

```tsx
function AddPill({
  value,
  setValue,
  onSubmit,
  placeholder,
  label,
  listId,
}: {
  value: string;
  setValue: (v: string) => void;
  onSubmit: () => void;
  placeholder: string;
  label: string;
  listId?: string;
}) {
  const submit = () => {
    if (!value.trim()) return;
    onSubmit();
  };

  return (
    <div className="inline-flex max-w-full items-center gap-1 rounded-full border border-dashed border-foreground/20 bg-white/60 px-2 py-1 text-[13px]">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") submit();
        }}
        placeholder={placeholder}
        list={listId}
        className="w-24 min-w-0 bg-transparent py-0.5 outline-none placeholder:text-foreground/40"
      />
      <button
        type="button"
        onClick={submit}
        className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-white"
        style={{ background: "var(--gradient-warm)" }}
        aria-label={label}
      >
        <Plus size={11} />
      </button>
    </div>
  );
}
```

Update the calls:

```tsx
                <AddPill
                  value={newSkill}
                  setValue={setNewSkill}
                  placeholder="Skill"
                  label="Add skill"
                  listId="cc-skill-presets"
                  onSubmit={() => {
                    addSkill(newSkill);
                    setNewSkill("");
                  }}
                />
```

```tsx
                <AddPill
                  value={newInterest}
                  setValue={setNewInterest}
                  placeholder="Interest"
                  label="Add interest"
                  onSubmit={() => {
                    addInterest(newInterest);
                    setNewInterest("");
                  }}
                />
```

- [ ] **Step 4: Suppress placeholder dashes**

Add:

```ts
function visibleText(value: string | undefined): string {
  const cleaned = value?.trim() ?? "";
  return cleaned && cleaned !== "—" ? cleaned : "";
}
```

Change `RowItem` props:

```ts
  subtitle?: string;
  meta?: string;
```

Change the rendered subtitle and meta:

```tsx
        {visibleText(subtitle) && <p className="truncate text-[12px] text-foreground/55">{subtitle}</p>}
      </div>
      {visibleText(meta) && (
        <span className="shrink-0 text-[12px] tabular-nums text-foreground/60">{meta}</span>
      )}
```

In the certification add call, change:

```tsx
onAdd={(a, b) => addCertification({ name: a, issuer: "", year: b })}
```

In the project add call, change:

```tsx
onAdd={(a, b) => addProject({ name: a, detail: "", year: b })}
```

In `AddSimpleRow`, change submit to:

```ts
    onAdd(a.trim(), b.trim());
```

- [ ] **Step 5: Add recap year validation**

Add helpers near `formatYearRange`:

```ts
function normalizeYear(value: string): string {
  return value.trim().match(/\d{4}/)?.[0] ?? "";
}

function invalidYearRange(start: string, end: string): boolean {
  const s = normalizeYear(start);
  const e = normalizeYear(end);
  return Boolean(s && e && s > e);
}
```

In `AddExperienceRow`, add:

```ts
  const [error, setError] = useState("");
```

At the start of `submit`, after required role/company checks:

```ts
    if (invalidYearRange(start, end)) {
      setError("End date cannot be before start date.");
      return;
    }
```

When adding the item, normalize years:

```ts
      start: normalizeYear(start),
      end: normalizeYear(end) || "Present",
```

Render the error below the row inputs:

```tsx
      {error && <p className="text-[11.5px] text-red-700" role="alert">{error}</p>}
```

Repeat the same pattern in `AddEducationRow`, with:

```ts
      start: normalizeYear(start),
      end: normalizeYear(end),
```

- [ ] **Step 6: Add recap suggestions**

In `AddExperienceRow`, add `list="cc-role-presets"` to the role input:

```tsx
        list="cc-role-presets"
```

In `AddEducationRow`, add `list="cc-degree-presets"` to the degree input:

```tsx
        list="cc-degree-presets"
```

- [ ] **Step 7: Keep long skill icons stable**

In the skill chip icon span, add `shrink-0`:

```tsx
className="grid h-6 w-6 shrink-0 place-items-center rounded-full text-white"
```

- [ ] **Step 8: Run checks**

Run:

```powershell
cd frontend
npm run test:feedback-quick-wins
npm run build
```

Expected: both commands PASS.

- [ ] **Step 9: Commit**

```powershell
git add frontend/src/components/compass/stages/RecapStage.tsx
git commit -m "fix: improve recap add rows and suggestions"
```

---

### Task 5: Final Verification

**Files:**
- No file edits.

- [ ] **Step 1: Run targeted checks**

Run:

```powershell
cd frontend
npm run test:feedback-quick-wins
npm run test:scroll
node scripts/check-removable-chip-hover.mjs
```

Expected: all PASS.

- [ ] **Step 2: Run build**

Run:

```powershell
cd frontend
npm run build
```

Expected: PASS.

- [ ] **Step 3: Manual smoke check**

Run:

```powershell
cd frontend
npm run dev
```

Open the local Vite URL and check:

- Mobile width: long skill text does not overflow the viewport.
- Manual submit with missing role: error appears inside the manual card.
- Manual education start `2026-06`, end `2025-01`: submit is blocked.
- Submit manual profile, go back to input: entered values are still visible.
- Recap skill input: typing `Pyt` offers `Python`.
- Recap role input: typing `Data` offers `Data Engineer`.
- Recap certification with no issuer: no dash is displayed.

- [ ] **Step 4: Commit only if smoke-check changes were needed**

```powershell
git status --short
```

Expected: clean working tree after the prior task commits, or only intentional smoke-check fixes.

---

## Skipped

- No AI-generated follow-up questions. Add after these UI trust fixes ship.
- No company/school autocomplete. Add when there is a real data source.
- No backend recommendation changes. Items 8-9 are separate backend ranking work.
