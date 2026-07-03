import { ModalBlock } from "./DeepDiveModal";
import { AnimatedPercent } from "./AnimatedPercent";
import { motion, useReducedMotion } from "framer-motion";
import { buildSkillRadarAxes, type SkillRadarAxis } from "@/lib/gapRadar";
import { skillGapCopy } from "@/lib/skillGapCoverage";
import type { CareerPathMilestone, GapReport, SeniorityDimension, SkillGap } from "@/lib/api";

export function SkillGapSection({
  report,
  milestones = [],
}: {
  report: GapReport;
  milestones?: CareerPathMilestone[];
}) {
  const topGaps = sortSkillGaps(report.skills.skill_gaps).slice(0, 3);

  return (
    <>
      <SkillRadar report={report} />
      <GapList title="Top skill gaps" gaps={topGaps} milestones={milestones} />
      <SeniorityGap seniority={report.seniority} />
    </>
  );
}

function SkillRadar({ report }: { report: GapReport }) {
  const axes = buildSkillRadarAxes(report);
  const reduceMotion = useReducedMotion();
  const progressTransition = reduceMotion
    ? { duration: 0 }
    : { duration: 0.8, ease: [0.22, 1, 0.36, 1] as const };

  return (
    <ModalBlock className="mb-5 mt-1 border-t border-foreground/10 pt-4">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Skill map</p>
      {axes.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[260px_minmax(0,1fr)] lg:items-center">
          <RadarSvg axes={axes} />
          <div className="grid gap-2 sm:grid-cols-2">
            {axes.map((axis) => {
              const axisPercent = percent(axis.value);

              return (
                <div
                  key={axis.label}
                  className="rounded-2xl border border-foreground/10 bg-white/60 p-3"
                >
                  <div className="mb-1 flex items-center justify-between gap-2">
                    <p className="text-[12.5px] font-medium leading-snug text-foreground/80">
                      {axis.label}
                    </p>
                    <AnimatedPercent
                      value={axisPercent}
                      className="text-[11px] text-foreground/45"
                    />
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-foreground/[0.08]">
                    <motion.div
                      className="h-full rounded-full bg-[color:var(--brand)]"
                      initial={{ width: "0%" }}
                      animate={{ width: `${axisPercent}%` }}
                      transition={progressTransition}
                    />
                  </div>
                  {axis.skills.length > 0 && (
                    <p className="mt-1.5 line-clamp-2 text-[11px] leading-snug text-foreground/45">
                      {axis.skills.join(", ")}
                    </p>
                  )}
                </div>
              );
            })}
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
  const centerPoints = axes.map(() => `${center},${center}`).join(" ");
  const reduceMotion = useReducedMotion();

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
      <motion.polygon
        points={valuePoints}
        initial={{ points: centerPoints }}
        animate={{ points: valuePoints }}
        transition={reduceMotion ? { duration: 0 } : { duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
        fill="color-mix(in oklab, var(--brand) 22%, transparent)"
        stroke="var(--brand)"
        strokeWidth="2"
      />
    </svg>
  );
}

function GapList({
  title,
  gaps,
  milestones,
}: {
  title: string;
  gaps: SkillGap[];
  milestones: CareerPathMilestone[];
}) {
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
            body={skillGapCopy(gap, milestones)}
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
      <p className="mt-1 whitespace-pre-line text-[12.5px] leading-relaxed text-foreground/65">
        {body}
      </p>
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

function seniorityCopy(seniority: SeniorityDimension): string {
  if (seniority.gap === "match") return "Your current level appears aligned with this role.";
  if (seniority.gap === "over") return "Your profile may be above the level implied by this role.";
  if (seniority.gap === "under")
    return "This role appears to require more seniority than your profile shows.";
  return "There is not enough seniority signal to compare levels confidently.";
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
