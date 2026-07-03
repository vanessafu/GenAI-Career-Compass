import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/gapRadar.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { buildSkillRadarAxes } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

// --- Enough distinct domains (>=3) -> domain-level axes ---------------------
const domainAxes = buildSkillRadarAxes({
  skills: {
    domain_coverage: {
      Backend: 0.9,
      Frontend: 0.6,
      DevOps: 0.0,
      Databases: 0.45,
      AI: 0.2,
      Networking: 1.0,
    },
    domain_skills: {
      Backend: ["Django", "FastAPI"],
      Frontend: ["React"],
      DevOps: ["Kubernetes", "Docker"],
      Databases: ["Postgres"],
      AI: ["PyTorch"],
      Networking: ["DNS"],
    },
  },
});

assert(domainAxes.length === 5, `Expected 5 radar axes (capped), got ${domainAxes.length}`);
assert(domainAxes[0].label === "DevOps", `Expected weakest domain first, got ${domainAxes[0].label}`);
assert(domainAxes[0].value === 0, `Expected DevOps value 0, got ${domainAxes[0].value}`);
assert(domainAxes[0].state === "gap", `Expected DevOps state 'gap', got ${domainAxes[0].state}`);
assert(
  domainAxes[0].skills.join(",") === "Kubernetes,Docker",
  `Expected DevOps skills list, got ${domainAxes[0].skills.join(",")}`,
);
assert(domainAxes[1].label === "AI", `Expected second-weakest domain second, got ${domainAxes[1].label}`);
assert(domainAxes[1].value === 0.2, `Expected AI value 0.2, got ${domainAxes[1].value}`);
assert(
  !domainAxes.some((axis) => axis.label === "Networking"),
  "Expected the strongest domain (Networking, fully covered) to be cut off by the 5-axis cap",
);

const fullyMatched = buildSkillRadarAxes({
  skills: { domain_coverage: { Backend: 1, Frontend: 1, DevOps: 1 } },
});
assert(fullyMatched[0].state === "matched", `Expected full coverage to be 'matched', got ${fullyMatched[0].state}`);

// --- Too few domains (<3) -> falls back to per-skill axes -------------------
const fallbackAxes = buildSkillRadarAxes({
  skills: {
    domain_coverage: { Backend: 0.5, Frontend: 0.8 },
    matched_skills: ["Python", "Git"],
    skill_gaps: [
      { required_skill: "Algorithms", transferability: 0, severity: "high" },
      { required_skill: "CI/CD", transferability: 0.45, severity: "medium" },
      { required_skill: "Cloud Computing", transferability: 0.2, severity: "low" },
    ],
  },
});

assert(fallbackAxes.length === 5, `Expected 5 fallback axes, got ${fallbackAxes.length}`);
assert(
  fallbackAxes[0].label === "Algorithms",
  `Expected top high-severity gap first, got ${fallbackAxes[0].label}`,
);
assert(fallbackAxes[0].value === 0, `Expected missing skill value 0, got ${fallbackAxes[0].value}`);
assert(fallbackAxes[1].label === "CI/CD", `Expected medium gap second, got ${fallbackAxes[1].label}`);
assert(fallbackAxes[1].value === 0.45, `Expected transferability value 0.45, got ${fallbackAxes[1].value}`);
assert(fallbackAxes[3].label === "Python", `Expected matched skill filler, got ${fallbackAxes[3].label}`);
assert(fallbackAxes[3].value === 1, `Expected matched skill value 1, got ${fallbackAxes[3].value}`);
assert(
  fallbackAxes.every((axis) => axis.skills.length === 0),
  "Expected per-skill fallback axes to have an empty skills list (already as specific as they get)",
);

// No domains at all (never reprocessed) -> also falls back to per-skill axes.
const noDomainAxes = buildSkillRadarAxes({
  skills: {
    domain_coverage: {},
    matched_skills: ["Python"],
    skill_gaps: [{ required_skill: "Docker", transferability: 0, severity: "high" }],
  },
});
assert(noDomainAxes.length === 2, `Expected 2 fallback axes, got ${noDomainAxes.length}`);
assert(noDomainAxes[0].label === "Docker", `Expected gap first, got ${noDomainAxes[0].label}`);

const emptyAxes = buildSkillRadarAxes({ skills: { domain_coverage: {}, matched_skills: [], skill_gaps: [] } });
assert(emptyAxes.length === 0, `Expected no axes for empty report, got ${emptyAxes.length}`);

console.log("check-gap-radar.mjs: all assertions passed.");
