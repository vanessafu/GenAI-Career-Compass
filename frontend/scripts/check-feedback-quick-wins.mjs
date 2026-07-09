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
const manualSubmitStart = entry.indexOf("const buildManualProfile = async");
const manualSubmitEnd = entry.indexOf("\n  return (", manualSubmitStart);
const manualSubmit =
  manualSubmitStart === -1 || manualSubmitEnd === -1
    ? ""
    : entry.slice(manualSubmitStart, manualSubmitEnd);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function clearsEmptyDraft(call, fields) {
  const start = manualSubmit.indexOf(`${call}({`);
  const end = manualSubmit.indexOf("});", start);
  if (start === -1 || end === -1) return false;
  const body = manualSubmit.slice(start, end);
  return fields.every((field) => body.includes(`${field}: ""`));
}

assert(pkg.includes("test:feedback-quick-wins"), "package.json needs the quick-win test script.");
assert(
  store.includes("manualDraft") && store.includes("setManualDraft"),
  "Manual entry draft must persist in Zustand.",
);
assert(
  entry.includes("setManualDraft("),
  "EntryStage must save manual form data before leaving the stage.",
);
assert(
  entry.includes("showManualError"),
  "EntryStage must show manual validation errors inside the manual card.",
);
assert(
  entry.includes("isMonthRangeInvalid"),
  "EntryStage must reject end months before start months.",
);
assert(
  /\.manual-input\s*\{[^}]*box-sizing:\s*border-box;/s.test(styles),
  "Manual inputs need border-box sizing.",
);
assert(
  entry.includes("grid grid-cols-1 gap-2.5 sm:grid-cols-2"),
  "Manual two-column grids must collapse on mobile.",
);
assert(
  entry.includes("grid grid-cols-1 gap-2.5 sm:grid-cols-3"),
  "Manual three-column grids must collapse on mobile.",
);
assert(
  entry.includes("grid w-full min-w-0 gap-5 md:grid-cols-2") &&
    entry.includes("liquid-glass flex min-w-0 flex-col rounded-3xl p-7") &&
    entry.includes("flex min-w-0 flex-wrap items-center gap-1.5"),
  "Manual cards and tag fields must shrink inside the mobile column.",
);
assert(recap.includes("cc-skill-presets"), "Recap skills need native suggestions.");
assert(recap.includes("cc-role-presets"), "Recap experience role input needs native suggestions.");
assert(
  recap.includes("cc-degree-presets"),
  "Recap education degree input needs native suggestions.",
);
assert(recap.includes("aria-label={label}"), "Recap add inputs need a real add button.");
assert(!recap.includes('issuer: "—"'), "Certifications must not store placeholder issuers.");
assert(!recap.includes('detail: "—"'), "Projects must not store placeholder details.");
assert(
  (recap.match(/isMonthRangeInvalid\(start, end\)/g) ?? []).length >= 3,
  "Recap add rows must reject impossible year ranges.",
);
assert(
  manualSubmit.includes("setEducation(educationOut)") &&
    manualSubmit.includes("setExperience(experienceOut)") &&
    manualSubmit.includes("setLanguages(languagesOut)") &&
    manualSubmit.includes("setProjects(projectsOut)") &&
    manualSubmit.includes("setCertifications(certificationsOut)"),
  "Manual submit must commit flushed draft rows into local state before retry.",
);
assert(
  clearsEmptyDraft("setEducationDraft", [
    "degree",
    "institution",
    "fieldOfStudy",
    "startDate",
    "endDate",
  ]) &&
    clearsEmptyDraft("setExperienceDraft", ["role", "organization", "startDate", "endDate"]) &&
    clearsEmptyDraft("setLanguageDraft", ["name", "level"]) &&
    clearsEmptyDraft("setProjectDraft", [
      "title",
      "description",
      "technologies",
      "startDate",
      "endDate",
    ]) &&
    clearsEmptyDraft("setCertificationDraft", ["name", "issuingOrganization", "issueDate"]),
  "Manual submit must clear flushed draft fields before retry.",
);
assert(
  /\.removable-chip\s*\{[^}]*min-width:\s*0;[^}]*max-width:\s*100%;/s.test(styles),
  "Shared chip styles must cap long chips.",
);
