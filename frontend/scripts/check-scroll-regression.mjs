import { readFile } from "node:fs/promises";

const styles = await readFile(new URL("../src/styles.css", import.meta.url), "utf8");
const bodyRule = styles.match(/body\s*\{(?<declarations>[\s\S]*?)\n\s*\}/);
const rootHeightRule = styles.match(
  /html,\s*\n\s*body,\s*\n\s*#root\s*\{(?<declarations>[\s\S]*?)\n\s*\}/,
);

if (!bodyRule?.groups?.declarations) {
  throw new Error("Could not find the base body rule in src/styles.css.");
}

if (!rootHeightRule?.groups?.declarations) {
  throw new Error("Could not find the root sizing rule in src/styles.css.");
}

if (/\boverflow\s*:\s*hidden\s*;/.test(bodyRule.groups.declarations)) {
  throw new Error("The base body rule must not lock vertical page scrolling.");
}

if (/(?:^|[;\n\r])\s*height\s*:\s*100%\s*;/.test(rootHeightRule.groups.declarations)) {
  throw new Error("The root sizing rule must not clamp the page to viewport height.");
}
