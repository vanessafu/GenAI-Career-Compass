import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/pathPreparation.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { areSelectedPathsPrepared } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const baseState = {
  careerPathReports: {},
  careerPathErrors: {},
  roleGapReports: {},
  roleGapErrors: {},
};

assert(areSelectedPathsPrepared([], baseState), "No selected roles should be considered prepared.");
assert(
  !areSelectedPathsPrepared(["42"], {
    ...baseState,
    careerPathReports: { 42: {} },
    roleGapReports: {},
  }),
  "A role with only career path loaded is not prepared.",
);
assert(
  areSelectedPathsPrepared(["42"], {
    ...baseState,
    careerPathReports: { 42: {} },
    roleGapReports: { 42: {} },
  }),
  "A role with both reports loaded should be prepared.",
);
assert(
  areSelectedPathsPrepared(["42"], {
    ...baseState,
    careerPathErrors: { 42: "failed" },
    roleGapReports: { 42: {} },
  }),
  "A role with career path error and gap report should be prepared.",
);
assert(
  !areSelectedPathsPrepared(["42", "99"], {
    ...baseState,
    careerPathReports: { 42: {}, 99: {} },
    roleGapReports: { 42: {} },
  }),
  "All selected roles must settle before preparation is complete.",
);
