import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/demoData.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const {
  DEMO_CAREER_PATH_REPORTS,
  DEMO_GAP_REPORTS,
  DEMO_IDENTITY,
  DEMO_ROLE_MATCHES,
  DEMO_SELECTED_ROLE_IDS,
} = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const storeSource = await readFile(
  new URL("../src/state/useStageStore.ts", import.meta.url),
  "utf8",
);
const maxPicks = Number(storeSource.match(/export const MAX_PICKS = (\d+);/)?.[1]);
assert(Number.isInteger(maxPicks), "Could not read MAX_PICKS from the store.");

const roleIds = new Set(DEMO_ROLE_MATCHES.map((role) => String(role.role_id)));
const identityText = `${DEMO_IDENTITY.archetype} ${DEMO_IDENTITY.lead}`.toLowerCase();
for (const banned of ["ready-now", "ready now", "path", "matched role", "bucket", "fit"]) {
  assert(!identityText.includes(banned), `Demo identity should not mention ${banned}.`);
}
for (const banned of ["northstar", "atlas", "blueleaf", "berlin", "hamburg", "cologne"]) {
  assert(
    !identityText.includes(banned),
    `Demo identity should not include private CV detail ${banned}.`,
  );
}

assert(DEMO_ROLE_MATCHES.length === 9, `Expected 9 demo roles, got ${DEMO_ROLE_MATCHES.length}.`);
assert(
  DEMO_SELECTED_ROLE_IDS.length > 0 && DEMO_SELECTED_ROLE_IDS.length <= maxPicks,
  `Selected demo roles must be 1..${maxPicks}.`,
);

for (const roleId of DEMO_SELECTED_ROLE_IDS) {
  assert(roleIds.has(String(roleId)), `Selected role ${roleId} is not in demo matches.`);
}

for (const role of DEMO_ROLE_MATCHES) {
  const roleId = String(role.role_id);
  const description = role.description.toLowerCase();
  for (const banned of ["user", "candidate", "profile", "fit", "readiness", "matched skills"]) {
    assert(!description.includes(banned), `${roleId} role description mentions ${banned}.`);
  }
  assert(role.description.length <= 180, `${roleId} role description is over 180 characters.`);
  assert(
    role.description.split(/\s+/).length <= 35,
    `${roleId} role description is over 35 words.`,
  );
  assert(role.matching_score >= 0 && role.matching_score <= 100, `${roleId} score is invalid.`);
  assert(DEMO_GAP_REPORTS[roleId], `${roleId} is missing a gap report.`);
  assert(DEMO_CAREER_PATH_REPORTS[roleId], `${roleId} is missing a career path report.`);
  assert(
    DEMO_CAREER_PATH_REPORTS[roleId].requirement_breakdown === DEMO_GAP_REPORTS[roleId],
    `${roleId} career path should reuse the matching gap report object.`,
  );
  assert(
    DEMO_CAREER_PATH_REPORTS[roleId].plan_summary?.trim(),
    `${roleId} career path should include a plan summary.`,
  );
  assert(
    !hasRange(DEMO_CAREER_PATH_REPORTS[roleId].estimated_timeline),
    `${roleId} career path should use one exact total timeline.`,
  );
  assert(
    usesDisplayUnit(DEMO_CAREER_PATH_REPORTS[roleId].estimated_timeline),
    `${roleId} total timeline should use weeks only up to 4 weeks, then months.`,
  );
  const milestoneWeeks = DEMO_CAREER_PATH_REPORTS[roleId].milestones.map((milestone) =>
    durationWeeks(milestone.timeline),
  );
  assert(
    milestoneWeeks.every((weeks) => weeks !== null),
    `${roleId} milestones should use exact week/month durations.`,
  );
  assert(
    DEMO_CAREER_PATH_REPORTS[roleId].milestones.every((milestone) =>
      usesDisplayUnit(milestone.timeline),
    ),
    `${roleId} milestone timelines should use weeks only up to 4 weeks, then months.`,
  );
  assert(
    DEMO_CAREER_PATH_REPORTS[roleId].estimated_timeline ===
      formatDurationWeeks(milestoneWeeks.reduce((total, weeks) => total + (weeks ?? 0), 0)),
    `${roleId} total timeline should add up from milestones and use display units.`,
  );

  const readiness = DEMO_GAP_REPORTS[roleId].overall_readiness;
  assert(readiness >= 0 && readiness <= 1, `${roleId} readiness is invalid.`);
}

function hasRange(value) {
  return /\d+\s*(?:-|to|–|—)\s*\d+/i.test(value);
}

function durationWeeks(value) {
  const match = String(value).match(/^\s*(\d+)\s+(weeks?|months?)\s*$/i);
  if (!match) return null;
  const amount = Number(match[1]);
  return match[2].toLowerCase().startsWith("month") ? amount * 4 : amount;
}

function usesDisplayUnit(value) {
  const match = String(value).match(/^\s*(\d+)\s+(weeks?|months?)\s*$/i);
  return Boolean(match && (!match[2].toLowerCase().startsWith("week") || Number(match[1]) <= 4));
}

function formatDurationWeeks(weeks) {
  if (weeks <= 4) return `${weeks} ${weeks === 1 ? "week" : "weeks"}`;
  const months = Math.ceil(weeks / 4);
  return `${months} ${months === 1 ? "month" : "months"}`;
}
