import type { CareerPathMilestone, SkillGap } from "./api";

export function skillGapCopy(gap: SkillGap, milestones: CareerPathMilestone[] = []): string {
  const skillLabel = gap.display || gap.required_skill;
  const hasProfileSignal = gap.transferability > 0 && gap.user_closest_skill;
  const base = hasProfileSignal
    ? `${skillLabel} is partly covered by: ${gap.user_closest_skill}.`
    : `${skillLabel} is not visible in your profile yet.`;

  const milestone = roadmapMilestoneForGap(gap, milestones);
  if (!milestone) return base;

  const timeline = milestone.timeline.trim();
  const label = timeline ? `${milestone.title} (${timeline})` : milestone.title;
  const action = hasProfileSignal ? "Continue building" : "Build";
  return `${base}\n${action} strengths in this area by meeting the roadmap milestone: ${label}.`;
}

function roadmapMilestoneForGap(
  gap: SkillGap,
  milestones: CareerPathMilestone[],
): CareerPathMilestone | undefined {
  const target = normalizeSkill(gap.required_skill || gap.skill);
  if (!target) return undefined;
  return milestones.find((milestone) =>
    milestone.skills.some((skill) => normalizeSkill(skill) === target),
  );
}

function normalizeSkill(value: string): string {
  return value.trim().toLowerCase().split(/\s+/).join(" ");
}
