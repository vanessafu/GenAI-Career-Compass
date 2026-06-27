import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/skillGapCoverage.ts", import.meta.url), "utf8");
const skillGapSectionSource = await readFile(
  new URL("../src/components/compass/modals/SkillGapSection.tsx", import.meta.url),
  "utf8",
);
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { skillGapCopy } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const kubernetesGap = {
  skill: "Kubernetes",
  importance: "medium",
  suggestion: "",
  required_skill: "Kubernetes",
  user_closest_skill: "Docker",
  transferability: 0.55,
  severity: "medium",
  source: "test",
};

const kubernetesMilestone = {
  order: 1,
  kind: "skill",
  title: "Ship one Kubernetes-backed service",
  timeline: "3 weeks",
  rationale: "",
  skills: ["Kubernetes"],
  projects: [],
};

const coveredCopy = skillGapCopy(kubernetesGap, [kubernetesMilestone]);
assert(
  coveredCopy ===
    "Kubernetes is partly covered by: Docker.\nContinue building strengths in this area by meeting the roadmap milestone: Ship one Kubernetes-backed service (3 weeks).",
  `Expected roadmap coverage copy, got: ${coveredCopy}`,
);
assert(
  skillGapSectionSource.includes("whitespace-pre-line"),
  "Skill gap body should render the roadmap sentence on a new line.",
);

const unmatchedCopy = skillGapCopy(kubernetesGap, [
  { ...kubernetesMilestone, title: "Build Terraform module", skills: ["Terraform"] },
]);
assert(
  !unmatchedCopy.includes("roadmap milestone"),
  `Expected unmatched gap to keep silent fallback, got: ${unmatchedCopy}`,
);

const normalizedCopy = skillGapCopy(
  { ...kubernetesGap, required_skill: "Infrastructure   as Code", user_closest_skill: null },
  [
    {
      ...kubernetesMilestone,
      title: "Add Terraform to the deployment portal",
      skills: [" infrastructure as code "],
    },
  ],
);
assert(
  normalizedCopy ===
    "Infrastructure   as Code is not visible in your profile yet.\nBuild strengths in this area by meeting the roadmap milestone: Add Terraform to the deployment portal (3 weeks).",
  `Expected deterministic missing-profile copy, got: ${normalizedCopy}`,
);
