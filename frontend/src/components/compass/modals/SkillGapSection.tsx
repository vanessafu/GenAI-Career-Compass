import { ModalBlock } from "./DeepDiveModal";
import { buildSkillRadarAxes, type SkillRadarAxis } from "@/lib/gapRadar";
import type { GapReport, SeniorityDimension, SkillGap } from "@/lib/api";

export function SkillGapSection({ report }: { report: GapReport }) {
  const topGaps = sortSkillGaps(report.skills.skill_gaps).slice(0, 3);
  const readiness = percent(report.overall_readiness || report.readiness_score);
  const readinessText = readinessCopy(readiness);

  return (
    <>
      <ModalBlock className="mb-6">
        <p className="mb-1 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Readiness</p>
        <p className="font-display text-4xl tracking-tight text-[color:var(--brand-deep)]">
          {readiness}%
        </p>
        <p className="mt-1 text-[14px] font-medium text-foreground/80">{readinessText.title}</p>
        <p className="mt-2 text-[13px] leading-relaxed text-foreground/70">{readinessText.body}</p>
      </ModalBlock>

      <SkillRadar report={report} />
      <GapList title="Top skill gaps" gaps={topGaps} />
      <SeniorityGap seniority={report.seniority} />
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

function SkillRadar({ report }: { report: GapReport }) {
  const axes = buildSkillRadarAxes(report);
  const domains = domainLabels(report.domain_tags);

  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Skill map</p>
      {axes.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
          <RadarSvg axes={axes} />
          <div className="space-y-3">
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
            <div className="grid gap-2 sm:grid-cols-2">
              {axes.map((axis) => (
                <div
                  key={axis.label}
                  className="rounded-2xl border border-foreground/10 bg-white/60 p-3"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="text-[12.5px] font-medium leading-snug text-foreground/80">
                      {axis.label}
                    </p>
                    <span className="text-[11px] text-foreground/45">{percent(axis.value)}%</span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-foreground/[0.08]">
                    <div
                      className="h-full rounded-full bg-[color:var(--brand)]"
                      style={{ width: `${percent(axis.value)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <p className="text-[12.5px] text-foreground/55">No skill comparison is available yet.</p>
      )}
    </ModalBlock>
  );
}

function RadarSvg({ axes }: { axes: SkillRadarAxis[] }) {
  const center = 120;
  const radius = 78;
  const grid = [0.33, 0.66, 1].map((scale) => radarPoints(axes.length, radius * scale, center));
  const valuePoints = axes
    .map((axis, index) => pointFor(index, axes.length, radius * axis.value, center))
    .map((point) => `${point.x},${point.y}`)
    .join(" ");

  return (
    <svg
      viewBox="0 0 240 240"
      role="img"
      aria-label="Skill gap radar chart"
      className="mx-auto h-64 w-64"
    >
      {grid.map((points) => (
        <polygon
          key={points}
          points={points}
          fill="none"
          stroke="color-mix(in oklab, var(--brand) 20%, white)"
          strokeWidth="1"
        />
      ))}
      {axes.map((axis, index) => {
        const edge = pointFor(index, axes.length, radius, center);
        const label = pointFor(index, axes.length, radius + 24, center);
        const lines = labelLines(axis.label);
        return (
          <g key={axis.label}>
            <line
              x1={center}
              y1={center}
              x2={edge.x}
              y2={edge.y}
              stroke="color-mix(in oklab, var(--brand) 18%, white)"
              strokeWidth="1"
            />
            <text
              x={label.x}
              y={label.y}
              textAnchor="middle"
              dominantBaseline="middle"
              className="fill-foreground/60 text-[10px]"
            >
              {lines.map((line, lineIndex) => (
                <tspan
                  key={line}
                  x={label.x}
                  dy={lines.length === 1 ? 0 : lineIndex === 0 ? "-0.45em" : "1.1em"}
                >
                  {line}
                </tspan>
              ))}
            </text>
          </g>
        );
      })}
      <polygon
        points={valuePoints}
        fill="color-mix(in oklab, var(--brand) 22%, transparent)"
        stroke="var(--brand)"
        strokeWidth="2"
      />
    </svg>
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

function readinessCopy(readiness: number): { title: string; body: string } {
  if (readiness >= 70) {
    return {
      title: "Strong starting point",
      body: "You already show much of what this role needs. A few targeted proof points can make the path clearer.",
    };
  }
  if (readiness >= 40) {
    return {
      title: "Reachable with focused gaps",
      body: "This path looks realistic if you focus on the highest-impact gaps first.",
    };
  }
  return {
    title: "Stretch path",
    body: "This role needs a bigger bridge. Start with the core gaps before adding extra credentials.",
  };
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

function radarPoints(count: number, radius: number, center: number): string {
  return Array.from({ length: count }, (_, index) => {
    const point = pointFor(index, count, radius, center);
    return `${point.x},${point.y}`;
  }).join(" ");
}

function pointFor(index: number, count: number, radius: number, center: number) {
  const angle = -Math.PI / 2 + (index * 2 * Math.PI) / count;
  return {
    x: center + Math.cos(angle) * radius,
    y: center + Math.sin(angle) * radius,
  };
}

function labelLines(label: string): string[] {
  const words = label.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return [label];

  const lines = [""];
  for (const word of words) {
    const last = lines.length - 1;
    const next = lines[last] ? `${lines[last]} ${word}` : word;
    if (next.length <= 16 || lines.length === 2) {
      lines[last] = next;
    } else {
      lines.push(word);
    }
  }
  return lines;
}
