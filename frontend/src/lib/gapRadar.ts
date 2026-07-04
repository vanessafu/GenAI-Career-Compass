import type { GapReport, SkillGap } from "./api";

export type SkillRadarAxis = {
  label: string;
  value: number;
  state: "matched" | "gap";
  /** Specific skills behind this axis's score, for display under the domain
   * name. Only populated for domain axes - per-skill fallback axes are
   * already as specific as they get, so this stays empty for those. */
  skills: string[];
};

type RadarReport = Pick<GapReport, "skills">;

const MAX_AXES = 5;
const MIN_DOMAIN_AXES = 3;
const MATCHED_THRESHOLD = 0.99;

/** Prefer one axis per domain (e.g. "Backend", "DevOps"), value = the average
 * match score across that domain's required skills (backend: SkillAlignment
 * domain_scores -> GapReport.skills.domain_coverage). If the role has too few
 * distinct domains to make a readable radar (fewer than MIN_DOMAIN_AXES -
 * e.g. a role reprocessed with only 1-2 domains, or not reprocessed at all),
 * fall back to the original per-skill axes so the chart still has enough
 * points to be worth showing. */
export function buildSkillRadarAxes(report: RadarReport): SkillRadarAxis[] {
  const domainAxes = buildDomainAxes(report);
  if (domainAxes.length >= MIN_DOMAIN_AXES) return domainAxes;
  return buildSkillAxes(report);
}

function buildDomainAxes(report: RadarReport): SkillRadarAxis[] {
  const entries = Object.entries(report.skills.domain_coverage ?? {});
  const domainSkills = report.skills.domain_skills ?? {};

  return entries
    .map(([domain, value]) => ({ domain, value: clamp01(value) }))
    .sort((a, b) => a.value - b.value)
    .slice(0, MAX_AXES)
    .map(({ domain, value }) => ({
      label: clean(domain),
      value,
      state: value >= MATCHED_THRESHOLD ? "matched" : ("gap" as const),
      skills: (domainSkills[domain] ?? []).map(clean).filter(Boolean),
    }));
}

function buildSkillAxes(report: RadarReport): SkillRadarAxis[] {
  const axes: SkillRadarAxis[] = [];
  const seen = new Set<string>();

  for (const gap of sortSkillGaps(report.skills.skill_gaps ?? [])) {
    const label = clean(gap.display || gap.required_skill || gap.skill);
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    axes.push({ label, value: clamp01(gap.transferability), state: "gap", skills: [] });
    if (axes.length >= MAX_AXES) return axes;
  }

  for (const skill of report.skills.matched_skills ?? []) {
    const label = clean(skill);
    if (!label || seen.has(label.toLowerCase())) continue;
    seen.add(label.toLowerCase());
    axes.push({ label, value: 1, state: "matched", skills: [] });
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
