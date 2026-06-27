import { readFile } from "node:fs/promises";

const source = await readFile(
  new URL("../src/components/compass/stages/DirectionsStage.tsx", import.meta.url),
  "utf8",
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(source.includes("aria-pressed={selected}"), "Role cards should expose pressed state.");
assert(
  source.includes("{selected && (") &&
    /\{selected && \([\s\S]*?\bSelected\b[\s\S]*?\)\}/.test(source),
  "The Selected badge text should only render for selected cards.",
);
