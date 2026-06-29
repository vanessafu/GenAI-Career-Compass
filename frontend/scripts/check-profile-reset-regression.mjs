import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const source = readFileSync(join(root, "src/state/useStageStore.ts"), "utf8");

const checks = [
  {
    name: "uploadCv",
    start: "uploadCv: async",
    end: "/** Build a CVData",
  },
  {
    name: "submitManualProfile",
    start: "submitManualProfile: async",
    end: "/** Legacy local fallback",
  },
];

const requiredResets = [
  "roleMatches: []",
  "matchAnalysis: null",
  "selectedRoleIds: []",
  "selectedRoleId: null",
  "roleGapReports: {}",
  "roleGapLoading: {}",
  "roleGapErrors: {}",
];

for (const check of checks) {
  const start = source.indexOf(check.start);
  const end = source.indexOf(check.end, start);
  if (start === -1 || end === -1) throw new Error(`Could not find ${check.name} block.`);

  const block = source.slice(start, end);
  const missing = requiredResets.filter((token) => !block.includes(token));
  if (missing.length > 0) {
    throw new Error(`${check.name} does not clear stale role/gap state: ${missing.join(", ")}`);
  }
}
