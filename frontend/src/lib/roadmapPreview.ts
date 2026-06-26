import type { CareerPathMilestone } from "./api";

export type RoadmapPreviewNode = {
  label: string;
  title: string;
};

function clean(value: string | null | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed || fallback;
}

export function buildRoadmapPreviewNodes({
  currentRole,
  targetRole,
  milestones,
}: {
  currentRole: string | null | undefined;
  targetRole: string | null | undefined;
  milestones: Pick<CareerPathMilestone, "order" | "title">[];
}): RoadmapPreviewNode[] {
  const sorted = [...milestones]
    .filter((milestone) => milestone.title?.trim())
    .sort((a, b) => a.order - b.order);

  return [
    { label: "Start", title: clean(currentRole, "Current profile") },
    { label: "Milestone", title: clean(sorted[0]?.title, "Priority milestone") },
    { label: "Proof", title: clean(sorted[1]?.title, "Proof milestone") },
    { label: "Target role", title: clean(targetRole, "Target role") },
  ];
}
