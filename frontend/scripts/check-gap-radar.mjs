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

const axes = buildSkillRadarAxes({
  skills: {
    matched_skills: ["Python", "Git"],
    skill_gaps: [
      { required_skill: "Algorithms", transferability: 0, severity: "high" },
      { required_skill: "CI/CD", transferability: 0.45, severity: "medium" },
      { required_skill: "Cloud Computing", transferability: 0.2, severity: "low" },
    ],
  },
});

assert(axes.length === 5, `Expected 5 radar axes, got ${axes.length}`);
assert(
  axes[0].label === "Algorithms",
  `Expected top high-severity gap first, got ${axes[0].label}`,
);
assert(axes[0].value === 0, `Expected missing skill value 0, got ${axes[0].value}`);
assert(axes[1].label === "CI/CD", `Expected medium gap second, got ${axes[1].label}`);
assert(axes[1].value === 0.45, `Expected transferability value 0.45, got ${axes[1].value}`);
assert(axes[3].label === "Python", `Expected matched skill filler, got ${axes[3].label}`);
assert(axes[3].value === 1, `Expected matched skill value 1, got ${axes[3].value}`);

const emptyAxes = buildSkillRadarAxes({ skills: { matched_skills: [], skill_gaps: [] } });
assert(emptyAxes.length === 0, `Expected no axes for empty report, got ${emptyAxes.length}`);
