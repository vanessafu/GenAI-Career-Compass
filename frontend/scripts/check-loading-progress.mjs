import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/loadingProgress.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { CV_UPLOAD_PROGRESS, MATCHING_PROGRESS, getLoadingProgressState } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const start = getLoadingProgressState(CV_UPLOAD_PROGRESS, 0);
const eightSeconds = getLoadingProgressState(CV_UPLOAD_PROGRESS, 8000);
const thirtySeconds = getLoadingProgressState(CV_UPLOAD_PROGRESS, 30000);
const matchingStart = getLoadingProgressState(MATCHING_PROGRESS, 0);
const matchingFiveSeconds = getLoadingProgressState(MATCHING_PROGRESS, 5000);
const matchingTwentySeconds = getLoadingProgressState(MATCHING_PROGRESS, 20000);

assert(start.progress <= 12, `Upload progress starts too high: ${start.progress}`);
assert(eightSeconds.progress < 65, `Upload progress races too far by 8s: ${eightSeconds.progress}`);
assert(
  thirtySeconds.progress <= 90,
  `Upload progress should wait below completion: ${thirtySeconds.progress}`,
);
assert(thirtySeconds.step === 2, `Long uploads should honestly show the final processing step.`);

assert(
  matchingStart.progress <= 12,
  `Matching progress starts too high: ${matchingStart.progress}`,
);
assert(
  matchingFiveSeconds.progress < 65,
  `Matching progress races too far by 5s: ${matchingFiveSeconds.progress}`,
);
assert(
  matchingTwentySeconds.progress <= 90,
  `Matching progress should wait below completion: ${matchingTwentySeconds.progress}`,
);
assert(
  matchingTwentySeconds.step === 2,
  `Long role matching should honestly show the final alignment step.`,
);
