import { readFile } from "node:fs/promises";

const focusSource = await readFile(
  new URL("../src/components/compass/stages/FocusStage.tsx", import.meta.url),
  "utf8",
);
const fullPlanSource = await readFile(
  new URL("../src/components/compass/modals/FullPlanModal.tsx", import.meta.url),
  "utf8",
);

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

assert(
  focusSource.includes("showPlanStepDetails") && focusSource.includes("setShowPlanStepDetails"),
  "FocusStage should remember the roadmap detail toggle while browsing plans.",
);
assert(
  fullPlanSource.includes("showStepDetails") && fullPlanSource.includes("onToggleStepDetails"),
  "FullPlanModal should receive the roadmap detail toggle state from its parent.",
);
assert(
  fullPlanSource.includes("Show details") &&
    fullPlanSource.includes("Hide details") &&
    !fullPlanSource.includes("Show step details") &&
    !fullPlanSource.includes("Hide step details"),
  "Roadmap toggle should use the shorter show/hide details labels.",
);
assert(
  fullPlanSource.includes("expanded={showStepDetails}") &&
    fullPlanSource.includes("aria-expanded={expanded}"),
  "Roadmap toggle should expose its expanded state.",
);
assert(
  fullPlanSource.includes("AnimatePresence") &&
    fullPlanSource.includes("function RoadmapDetailLayer") &&
    fullPlanSource.includes("clipPath") &&
    fullPlanSource.includes("descriptionDelay") &&
    fullPlanSource.includes("pillDelay"),
  "Roadmap details should use a staged line, description, then pill reveal.",
);
assert(
  fullPlanSource.includes("showStepDetails={showStepDetails}") &&
    fullPlanSource.includes("animate={{ height: showStepDetails ? detailLayerHeight : 0 }}") &&
    !fullPlanSource.includes("{showStepDetails && (\n          <RoadmapDetailLayer"),
  "Roadmap detail layer should stay mounted so repeated toggles cannot interrupt remount animations.",
);
assert(
  !fullPlanSource.includes("rounded-full bg-white/75") &&
    !fullPlanSource.includes("focus-visible:ring-2") &&
    fullPlanSource.includes("focus-visible:underline"),
  "Roadmap toggle should read as quiet centered text, with only text-like keyboard focus affordance.",
);
