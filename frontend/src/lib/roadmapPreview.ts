import type { CareerPathMilestone } from "./api";

export type RoadmapPreviewNode = {
  label: string;
  title: string;
};

type MilestonePreview = Pick<CareerPathMilestone, "order" | "title"> & {
  kind?: CareerPathMilestone["kind"];
};

const KIND_LABELS: Record<CareerPathMilestone["kind"], string> = {
  role: "Intermediate role",
  skill: "Skill",
  project: "Project",
  certification: "Certification",
  experience: "Experience",
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
  milestones: MilestonePreview[];
}): RoadmapPreviewNode[] {
  const sorted = [...milestones]
    .filter((milestone) => milestone.title?.trim())
    .sort((a, b) => a.order - b.order);

  return [
    { label: "Start", title: clean(currentRole, "Current profile") },
    { label: kindLabel(sorted[0]), title: clean(sorted[0]?.title, "Priority milestone") },
    { label: kindLabel(sorted[1]), title: clean(sorted[1]?.title, "Proof milestone") },
    { label: "Target role", title: clean(targetRole, "Target role") },
  ];
}

function kindLabel(milestone: MilestonePreview | undefined): string {
  if (!milestone?.kind) return "Milestone";
  return KIND_LABELS[milestone.kind] ?? "Milestone";
}
