import { readFile } from "node:fs/promises";

const source = await readFile(new URL("../src/state/useStageStore.ts", import.meta.url), "utf8");

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(
  source.includes("let matchingRequest: Promise<boolean> | null = null"),
  "runMatching should keep a module-level in-flight request.",
);
assert(
  source.includes("if (matchingRequest) return matchingRequest"),
  "runMatching should return the in-flight request instead of starting a duplicate.",
);
assert(
  source.includes("matchingRequest = request.finally(() => {"),
  "runMatching should clear the in-flight request after it settles.",
);
