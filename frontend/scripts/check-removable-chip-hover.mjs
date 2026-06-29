import { readFile } from "node:fs/promises";

const styles = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
const recap = await readFile(
  new URL("../src/components/compass/stages/RecapStage.tsx", import.meta.url),
  "utf8",
);
const entry = await readFile(
  new URL("../src/components/compass/stages/EntryStage.tsx", import.meta.url),
  "utf8",
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(styles.includes(".removable-chip::after"), "Removable chips need a hover fade layer.");
assert(
  styles.includes(".removable-chip:hover::after") &&
    styles.includes(".removable-chip:focus-within::after"),
  "Removable chip fade should appear on hover and keyboard focus.",
);
assert(
  /\.removable-chip-remove\s*\{[\s\S]*?position:\s*absolute;[\s\S]*?right:/.test(styles),
  "Remove buttons should be absolutely positioned instead of taking flex space.",
);
assert(
  recap.includes("removable-chip") &&
    recap.includes("removable-chip-label") &&
    recap.includes("removable-chip-remove"),
  "Recap removable skill and interest chips should use the shared chip classes.",
);
assert(
  entry.includes("removable-chip") &&
    entry.includes("removable-chip-label") &&
    entry.includes("removable-chip-remove"),
  "Entry tag chips should use the shared chip classes.",
);
