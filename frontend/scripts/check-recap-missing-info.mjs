import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/recapMissingInfo.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { buildMissingBigSections } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function same(actual, expected, label) {
  assert(
    JSON.stringify(actual) === JSON.stringify(expected),
    `${label}: expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`,
  );
}

same(
  buildMissingBigSections({
    educations: [],
    experiences: [],
    skills: [],
    interests: [],
    certifications: [],
    projects: [],
  }),
  ["education", "experience", "skills", "interests", "certifications", "projects"],
  "empty profile",
);

same(
  buildMissingBigSections({
    educations: [{ degree: "Education", school: "\u2014" }],
    experiences: [{ role: "Role", company: "\u2014" }],
    skills: [{ name: "TypeScript", confidence: 80 }],
    interests: ["Frontend"],
    certifications: [{ name: "Certification", issuer: "\u2014" }],
    projects: [{ name: "Project", detail: "\u2014" }],
  }),
  ["education", "experience", "certifications", "projects"],
  "placeholder profile",
);

same(
  buildMissingBigSections({
    educations: [{ degree: "BSc Computer Science", school: "University" }],
    experiences: [{ role: "Software Developer", company: "\u2014" }],
    skills: [{ name: "C#", confidence: 75 }],
    interests: ["Accessibility"],
    certifications: [{ name: "Azure Fundamentals", issuer: "Microsoft" }],
    projects: [{ name: "Mobile app", detail: "Java" }],
  }),
  [],
  "all big sections present",
);
