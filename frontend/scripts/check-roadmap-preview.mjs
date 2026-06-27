import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const ts = require("typescript");

const source = await readFile(new URL("../src/lib/roadmapPreview.ts", import.meta.url), "utf8");
const iconSource = await readFile(
  new URL("../src/components/compass/RoadmapNodeIcon.tsx", import.meta.url),
  "utf8",
);
const modalSource = await readFile(
  new URL("../src/components/compass/modals/DeepDiveModal.tsx", import.meta.url),
  "utf8",
);
const fullPlanSource = await readFile(
  new URL("../src/components/compass/modals/FullPlanModal.tsx", import.meta.url),
  "utf8",
);
const roleViewSource = await readFile(new URL("../src/lib/roleView.ts", import.meta.url), "utf8");

function loadCommonJs(sourceText) {
  const compiled = ts.transpileModule(sourceText, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
    },
  });
  const module = { exports: {} };
  vm.runInNewContext(compiled.outputText, { module, exports: module.exports });
  return module.exports;
}

const { buildRoadmapPreviewNodes } = loadCommonJs(source);
const { roleMatchToView } = loadCommonJs(roleViewSource);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(
  !iconSource.includes("title.toLowerCase") && !iconSource.includes("RegExp"),
  "Roadmap icons should be selected by node kind only, not title keywords.",
);
assert(
  modalSource.includes("headerDescription"),
  "DeepDiveModal should support headerDescription for wide modal intro text.",
);
assert(
  fullPlanSource.includes("headerDescription={") &&
    fullPlanSource.includes("PlanHeaderDescription"),
  "FullPlanModal should move the profile summary into the modal header.",
);
assert(
  fullPlanSource.includes("function RoadmapCanvas"),
  "FullPlanModal should render desktop roadmap items in one relative canvas.",
);
assert(
  fullPlanSource.includes("canvasX(index, roadmapNodes.length)"),
  "Roadmap canvas positions should come from one x-coordinate helper.",
);
assert(
  fullPlanSource.includes('viewBox="0 0 1000 280"') &&
    fullPlanSource.includes('className="relative h-[280px] overflow-x-hidden"'),
  "Roadmap canvas should be tight enough to avoid dead space around descriptions.",
);
assert(
  fullPlanSource.includes('ModalBlock className="mb-1 border-t border-foreground/10 pt-6"') &&
    fullPlanSource.includes('ModalBlock className="mb-4 mt-1 border-t border-foreground/10 pt-4"'),
  "Roadmap and skills-gap section margins should keep the separator close to descriptions.",
);
assert(
  fullPlanSource.includes("const durationTop = 178") &&
    fullPlanSource.includes("const descriptionTop = 222"),
  "Roadmap canvas should use tighter fixed vertical bands for description content.",
);
assert(
  fullPlanSource.includes('className="min-w-0 px-4 text-center"') &&
    fullPlanSource.includes("break-words text-[13px] leading-relaxed"),
  "Roadmap description text should be centered and compact.",
);
assert(
  fullPlanSource.includes("descriptionCenterX(detailIndex, rawDetailNodes.length)") &&
    fullPlanSource.includes("gridTemplateColumns: `repeat(${detailNodes.length}, minmax(0, 1fr))`"),
  "Roadmap descriptions should share the available horizontal space independent of node positions.",
);
assert(
  fullPlanSource.includes("d={canvasConnectorPath(") &&
    fullPlanSource.includes("node.x") &&
    fullPlanSource.includes("node.descriptionX") &&
    fullPlanSource.includes("function descriptionCenterX"),
  "Roadmap connectors should route from the owning node to its evenly spaced description lane.",
);
assert(
  fullPlanSource.includes("Math.min(80, Math.max(-80") &&
    fullPlanSource.includes("`L ${toX} ${endY}`"),
  "Roadmap connectors should use a calm curve and finish vertically into the description lane.",
);
assert(
  fullPlanSource.includes('vectorEffect="non-scaling-stroke"') &&
    fullPlanSource.includes('strokeDasharray="4 7"') &&
    fullPlanSource.includes("border-dashed"),
  "Roadmap lines should render as thin, non-scaling dashed lines.",
);
assert(
  fullPlanSource.includes("const inset = 8"),
  "Roadmap node positions should stay inset enough to avoid horizontal overflow.",
);
assert(
  !fullPlanSource.includes("laneWidth") && !fullPlanSource.includes("overflow-visible"),
  "Roadmap canvas should avoid edge-overflowing lanes and SVGs that create horizontal scroll.",
);
assert(
  !fullPlanSource.includes("gridColumn: node.index + 1") &&
    !fullPlanSource.includes("connectorSide("),
  "Roadmap canvas should replace the old lane-grid connector routing.",
);

const demoUriRole = roleMatchToView({
  role_id: "demo-role",
  bucket: "next_step",
  title: "Platform Engineer",
  matching_score: 86,
  salary: "",
  description: "",
  esco_title: "Platform Engineer",
  esco_uri: "demo:demo-role",
  matched_skills: [],
  missing_skills: [],
  matched_domains: [],
  matched_certifications: [],
});
assert(demoUriRole.escoUri === "", "Demo ESCO URIs should not render as broken links.");

const realUriRole = roleMatchToView({
  ...demoUriRole,
  role_id: "real-role",
  esco_uri: "http://data.europa.eu/esco/occupation/528f90ed-e250-48bd-aacc-ffb7b1de5654",
});
assert(
  realUriRole.escoUri ===
    "http://data.europa.eu/esco/occupation/528f90ed-e250-48bd-aacc-ffb7b1de5654",
  "HTTP ESCO URIs should remain clickable.",
);

const nodes = buildRoadmapPreviewNodes({
  currentRole: "Senior Backend Developer",
  targetRole: "Cloud Architect",
  milestones: [
    { order: 2, kind: "project", title: "Lead cloud migration" },
    { order: 1, kind: "certification", title: "AWS SA Pro exam" },
    { order: 3, kind: "role", title: "Platform Engineer" },
  ],
});

assert(nodes.length === 4, `Expected 4 nodes, got ${nodes.length}`);
assert(nodes[0].label === "Start", `Expected first label Start, got ${nodes[0].label}`);
assert(nodes[0].kind === "start", `Expected first kind start, got ${nodes[0].kind}`);
assert(nodes[0].title === "Senior Backend Developer", `Unexpected start title ${nodes[0].title}`);
assert(nodes[1].label === "Certification", `Expected certification label, got ${nodes[1].label}`);
assert(nodes[1].kind === "certification", `Expected certification kind, got ${nodes[1].kind}`);
assert(nodes[1].title === "AWS SA Pro exam", `Milestones should sort by order.`);
assert(nodes[2].label === "Project", `Expected project label, got ${nodes[2].label}`);
assert(nodes[2].kind === "project", `Expected project kind, got ${nodes[2].kind}`);
assert(nodes[2].title === "Lead cloud migration", `Expected second milestone as third node.`);
assert(nodes[3].label === "Target role", `Expected final label Target role.`);
assert(nodes[3].kind === "target", `Expected final kind target, got ${nodes[3].kind}`);
assert(nodes[3].title === "Cloud Architect", `Unexpected target title ${nodes[3].title}`);

const fallbackNodes = buildRoadmapPreviewNodes({
  currentRole: "",
  targetRole: "DevOps Engineer",
  milestones: [],
});

assert(fallbackNodes[0].title === "Current profile", "Blank current role should fall back.");
assert(fallbackNodes[1].title === "Priority milestone", "Missing milestone should fall back.");
assert(fallbackNodes[2].title === "Proof milestone", "Second missing milestone should fall back.");

const mixedNodes = buildRoadmapPreviewNodes({
  currentRole: "Support Engineer",
  targetRole: "QA Engineer",
  milestones: [
    { order: 1, kind: "skill", title: "Automation fundamentals" },
    { order: 2, kind: "experience", title: "Own a test suite" },
  ],
});

assert(mixedNodes[1].label === "Skill", `Expected Skill label, got ${mixedNodes[1].label}`);
assert(mixedNodes[1].kind === "skill", `Expected skill kind, got ${mixedNodes[1].kind}`);
assert(
  mixedNodes[2].label === "Experience",
  `Expected Experience label, got ${mixedNodes[2].label}`,
);
assert(mixedNodes[2].kind === "experience", `Expected experience kind, got ${mixedNodes[2].kind}`);
