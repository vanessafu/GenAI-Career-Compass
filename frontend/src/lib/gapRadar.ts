import type { GapReport, SkillGap } from "./api";

export type SkillRadarAxis = {
  label: string;
  value: number;
  state: "matched" | "gap";
};

type RadarReport = Pick<GapReport, "skills">;

const MAX_AXES = 5;

export function buildSkillRadarAxes(report: RadarReport): SkillRadarAxis[] {
  const axes: SkillRadarAxis[] = [];
  const seen = new Set<string>();

  for (const gap of sortSkillGaps(report.skills.skill_gaps ?? [])) {
    const label = clean(gap.required_skill || gap.skill);
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    axes.push({ label, value: clamp01(gap.transferability), state: "gap" });
    if (axes.length >= MAX_AXES) return axes;
  }

  for (const skill of report.skills.matched_skills ?? []) {
    const label = clean(skill);
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    axes.push({ label, value: 1, state: "matched" });
    if (axes.length >= MAX_AXES) return axes;
  }

  return axes;
}

function sortSkillGaps(gaps: SkillGap[]): SkillGap[] {
  const rank: Record<string, number> = { high: 0, medium: 1, low: 2 };
  return [...gaps].sort(
    (a, b) =>
      (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3) || a.transferability - b.transferability,
  );
}

function clean(value: string | null | undefined): string {
  return (value || "").split(/\s+/).filter(Boolean).join(" ");
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}
