import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/roadmapPreview.ts", import.meta.url), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
  },
});

const module = { exports: {} };
vm.runInNewContext(compiled.outputText, { module, exports: module.exports });

const { buildRoadmapPreviewNodes } = module.exports;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const nodes = buildRoadmapPreviewNodes({
  currentRole: "Senior Backend Developer",
  targetRole: "Cloud Architect",
  milestones: [
    { order: 2, title: "Lead cloud migration" },
    { order: 1, title: "AWS SA Pro exam" },
    { order: 3, title: "IaC ownership" },
  ],
});

assert(nodes.length === 4, `Expected 4 nodes, got ${nodes.length}`);
assert(nodes[0].label === "Start", `Expected first label Start, got ${nodes[0].label}`);
assert(nodes[0].title === "Senior Backend Developer", `Unexpected start title ${nodes[0].title}`);
assert(nodes[1].title === "AWS SA Pro exam", `Milestones should sort by order.`);
assert(nodes[2].title === "Lead cloud migration", `Expected second milestone as third node.`);
assert(nodes[3].label === "Target role", `Expected final label Target role.`);
assert(nodes[3].title === "Cloud Architect", `Unexpected target title ${nodes[3].title}`);

const fallbackNodes = buildRoadmapPreviewNodes({
  currentRole: "",
  targetRole: "DevOps Engineer",
  milestones: [],
});

assert(fallbackNodes[0].title === "Current profile", "Blank current role should fall back.");
assert(fallbackNodes[1].title === "Priority milestone", "Missing milestone should fall back.");
assert(fallbackNodes[2].title === "Proof milestone", "Second missing milestone should fall back.");
