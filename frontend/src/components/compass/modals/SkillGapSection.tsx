import { ModalBlock } from "./DeepDiveModal";
import type { GapReport, SeniorityDimension, SkillGap } from "@/lib/api";

export function SkillGapSection({ report }: { report: GapReport }) {
  const topGaps = sortSkillGaps(report.skills.skill_gaps).slice(0, 3);
  const readiness = percent(report.overall_readiness || report.readiness_score);

  return (
    <>
      <ModalBlock className="mb-6">
        <p className="mb-1 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Readiness</p>
        <p className="font-display text-4xl tracking-tight text-[color:var(--brand-deep)]">
          {readiness}%
        </p>
        <p className="mt-2 text-[13px] leading-relaxed text-foreground/70">
          {report.narrative?.readiness_summary || readinessCopy(readiness)}
        </p>
      </ModalBlock>

      <SkillMap report={report} />
      <GapList title="Top skill gaps" gaps={topGaps} />
      <SeniorityGap seniority={report.seniority} />

      {report.narrative?.next_steps && (
        <ModalBlock className="mb-5">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            Next steps
          </p>
          <p className="text-[13px] leading-relaxed text-foreground/75">
            {report.narrative.next_steps}
          </p>
        </ModalBlock>
      )}
    </>
  );
}

const DOMAIN_LABELS: Record<string, string> = {
  ai_ml: "AI/ML",
  automation_scripting: "Automation",
  data_analytics: "Data",
  data_engineering: "Data",
  devops: "DevOps",
  qa_testing: "QA",
  role_requirements: "Role requirements",
  software_engineering: "Software",
  ux_ui: "UX/UI",
};

function SkillMap({ report }: { report: GapReport }) {
  const coverage = percent(report.skills.coverage);
  const matched = report.skills.matched_skills.length;
  const total = matched + report.skills.skill_gaps.length;
  const domains = domainLabels(report.domain_tags);

  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Skill map</p>
      <div className="flex flex-wrap gap-1.5">
        {domains.map((domain) => (
          <span
            key={domain}
            className="rounded-full bg-[color:var(--brand)]/10 px-2.5 py-1 text-[12px] text-[color:var(--brand-deep)]"
          >
            {domain}
          </span>
        ))}
      </div>
      <div className="mt-4">
        <div className="mb-1.5 flex items-center justify-between gap-3 text-[11.5px] text-foreground/55">
          <span>Skill coverage</span>
          <span>{total > 0 ? `${matched} of ${total} core skills covered` : `${coverage}%`}</span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-foreground/[0.08]">
          <div
            className="h-full rounded-full bg-[color:var(--brand)]"
            style={{ width: `${coverage}%` }}
          />
        </div>
      </div>
    </ModalBlock>
  );
}

function GapList({ title, gaps }: { title: string; gaps: SkillGap[] }) {
  if (gaps.length === 0) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">{title}</p>
      <div className="space-y-2">
        {gaps.map((gap) => (
          <GapRow
            key={`${gap.required_skill}-${gap.user_closest_skill ?? ""}`}
            title={gap.required_skill}
            meta={`${gap.severity} priority - ${effortLabel(gap)}`}
            body={skillGapCopy(gap)}
          />
        ))}
      </div>
    </ModalBlock>
  );
}

function SeniorityGap({ seniority }: { seniority: SeniorityDimension }) {
  if (seniority.gap !== "under" && seniority.gap !== "over") return null;
  const body = seniority.note || seniorityCopy(seniority);
  if (!body) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
        Seniority gap
      </p>
      <GapRow
        title="Seniority check"
        meta={`${seniority.user_level || "unknown"} -> ${seniority.role_level || "unknown"}`}
        body={body}
      />
    </ModalBlock>
  );
}

function GapRow({ title, meta, body }: { title: string; meta: string; body: string }) {
  return (
    <div className="border-t border-foreground/10 pt-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-[13px] font-medium text-foreground/85">{title}</p>
        <span className="rounded-full bg-foreground/[0.05] px-2 py-0.5 text-[11px] text-foreground/55">
          {meta}
        </span>
      </div>
      <p className="mt-1 text-[12.5px] leading-relaxed text-foreground/65">{body}</p>
    </div>
  );
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function percent(value: number): number {
  return Math.round(clamp01(value > 1 ? value / 100 : value) * 100);
}

function readinessCopy(readiness: number): string {
  if (readiness >= 70) return "You already cover most of what this role asks for.";
  if (readiness >= 40) return "This looks reachable, but a few gaps need focused work.";
  return "This role is a stretch based on the visible profile data.";
}

function sortSkillGaps(gaps: SkillGap[]): SkillGap[] {
  const rank: Record<string, number> = { high: 0, medium: 1, low: 2 };
  return [...gaps].sort(
    (a, b) =>
      (rank[a.severity] ?? 3) - (rank[b.severity] ?? 3) || a.transferability - b.transferability,
  );
}

function effortLabel(gap: SkillGap): string {
  if (gap.transferability >= 0.5) return "low effort";
  if (gap.transferability > 0) return "medium effort";
  return "high effort";
}

function skillGapCopy(gap: SkillGap): string {
  if (gap.transferability > 0 && gap.user_closest_skill) {
    return `${gap.required_skill} is partly covered by ${gap.user_closest_skill}; build direct proof around ${gap.required_skill}.`;
  }
  return `${gap.required_skill} is not visible in your profile yet. Add evidence through work, a project, or training.`;
}

function seniorityCopy(seniority: SeniorityDimension): string {
  if (seniority.gap === "match") return "Your current level appears aligned with this role.";
  if (seniority.gap === "over") return "Your profile may be above the level implied by this role.";
  if (seniority.gap === "under")
    return "This role appears to require more seniority than your profile shows.";
  return "There is not enough seniority signal to compare levels confidently.";
}

function domainLabels(tags: string[]): string[] {
  const source = tags.length > 0 ? tags : ["role_requirements"];
  const labels = source.map(formatDomainTag).filter(Boolean);
  return [...new Set(labels)];
}

function formatDomainTag(tag: string): string {
  const key = tag.trim().toLowerCase().replace(/\s+/g, "_");
  if (!key) return "Role requirements";
  if (DOMAIN_LABELS[key]) return DOMAIN_LABELS[key];
  return key
    .split("_")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
