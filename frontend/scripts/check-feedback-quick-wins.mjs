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
assert(entry.includes("box-sizing: border-box;"), "Manual inputs need border-box sizing.");
assert(
  entry.includes("grid grid-cols-1 gap-2.5 sm:grid-cols-2"),
  "Manual two-column grids must collapse on mobile.",
);
assert(
  entry.includes("grid grid-cols-1 gap-2.5 sm:grid-cols-3"),
  "Manual three-column grids must collapse on mobile.",
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
assert(recap.includes("invalidYearRange"), "Recap add rows must reject impossible year ranges.");
assert(
  /\.removable-chip-label\s*\{[^}]*max-width:\s*100%;/s.test(styles),
  "Shared chip styles must cap long labels.",
);
