import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import type { CertificationGap, GapReport, SeniorityDimension, SkillGap } from "@/lib/api";
import type { RoleView } from "@/types";

/**
 * Real role detail built entirely from backend RoleMatch data:
 * essential/optional skills + knowledge, plus the matching analysis text.
 */
export function RoleDetailModal({
  role,
  analysis,
  gapReport,
  gapLoading,
  gapError,
  open,
  onClose,
}: {
  role: RoleView;
  analysis: string | null;
  gapReport: GapReport | null;
  gapLoading: boolean;
  gapError: string | null;
  open: boolean;
  onClose: () => void;
}) {
  return (
    <DeepDiveModal open={open} onClose={onClose} title={role.title} subtitle={role.trackLabel}>
      {role.summary && (
        <ModalBlock className="mb-6">
          <p className="text-[13.5px] leading-relaxed text-foreground/75">{role.summary}</p>
        </ModalBlock>
      )}

      {(role.escoTitle || role.escoUri) && (
        <ModalBlock className="mb-6">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            ESCO reference
          </p>
          {role.escoUri ? (
            <a
              href={role.escoUri}
              target="_blank"
              rel="noreferrer"
              className="text-[13px] font-medium text-[color:var(--brand-deep)] underline-offset-4 hover:underline"
            >
              {role.escoTitle || role.escoUri}
            </a>
          ) : (
            <p className="text-[13px] leading-relaxed text-foreground/75">{role.escoTitle}</p>
          )}
        </ModalBlock>
      )}

      {analysis && (
        <ModalBlock className="mb-6">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            Why this fits you
          </p>
          <p className="text-[13px] leading-relaxed text-foreground/75">{analysis}</p>
        </ModalBlock>
      )}

      {gapLoading && (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing gap report...</p>
        </ModalBlock>
      )}

      {gapError && (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{gapError}</p>
        </ModalBlock>
      )}

      {gapReport ? (
        <GapReportContent report={gapReport} />
      ) : (
        <>
          <SkillSection title="Matched skills" items={role.matchedSkills} highlight />
          <SkillSection title="Missing skills" items={role.missingSkills} />
          <SkillSection title="Matched domains" items={role.essentialKnowledge} highlight />
          <SkillSection title="Matched certifications" items={role.optionalKnowledge} />
        </>
      )}
    </DeepDiveModal>
  );
}

function GapReportContent({ report }: { report: GapReport }) {
  const missing = sortSkillGaps(report.skills.skill_gaps.filter((gap) => gap.transferability <= 0));
  const partial = sortSkillGaps(report.skills.skill_gaps.filter((gap) => gap.transferability > 0));
  const optional = report.skills.optional_missing_skills;
  const certGaps = uniqueCertGaps([
    ...report.certifications.missing,
    ...report.certifications.missing_certifications,
  ]);
  const readiness = percent(report.overall_readiness || report.readiness_score);

  return (
    <>
      <ModalBlock className="mb-6">
        <div className="grid gap-4 border-b border-foreground/10 pb-5 sm:grid-cols-[1fr_160px]">
          <div>
            <p className="mb-1 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
              Readiness
            </p>
            <p className="font-display text-4xl tracking-tight text-[color:var(--brand-deep)]">
              {readiness}%
            </p>
            <p className="mt-2 text-[13px] leading-relaxed text-foreground/70">
              {report.narrative?.readiness_summary || readinessCopy(readiness)}
            </p>
          </div>
          <GapRadar
            skills={report.skills.coverage}
            certifications={report.certifications.coverage}
            seniority={seniorityScore(report.seniority)}
          />
        </div>
      </ModalBlock>

      {report.narrative?.main_gaps && (
        <ModalBlock className="mb-5">
          <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
            Main gaps
          </p>
          <p className="text-[13px] leading-relaxed text-foreground/75">
            {report.narrative.main_gaps}
          </p>
        </ModalBlock>
      )}

      <SkillSection title="Matched skills" items={report.skills.matched_skills} highlight />
      <GapList title="Missing required skills" gaps={missing} />
      <GapList title="Partially transferable skills" gaps={partial} />
      <SkillSection title="Optional skills" items={optional} />
      <CertificationGapList gaps={certGaps} />
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

function GapRadar({
  skills,
  certifications,
  seniority,
}: {
  skills: number;
  certifications: number;
  seniority: number;
}) {
  const axes = [
    { label: "Skills", value: skills, angle: -90 },
    { label: "Certs", value: certifications, angle: 30 },
    { label: "Level", value: seniority, angle: 150 },
  ];
  const points = axes.map((axis) => radarPoint(clamp01(axis.value), axis.angle)).join(" ");
  const grid = [1, 0.66, 0.33].map((scale) =>
    axes.map((axis) => radarPoint(scale, axis.angle)).join(" "),
  );

  return (
    <div className="flex items-center justify-center">
      <svg viewBox="0 0 120 120" className="h-36 w-36" aria-label="Gap comparison radar">
        {grid.map((poly) => (
          <polygon key={poly} points={poly} fill="none" stroke="rgba(36, 32, 25, 0.12)" />
        ))}
        {axes.map((axis) => {
          const end = radarPoint(1, axis.angle);
          const label = radarPoint(1.18, axis.angle);
          const [x, y] = label.split(",").map(Number);
          return (
            <g key={axis.label}>
              <line
                x1="60"
                y1="60"
                x2={end.split(",")[0]}
                y2={end.split(",")[1]}
                stroke="rgba(36, 32, 25, 0.12)"
              />
              <text
                x={x}
                y={y}
                textAnchor="middle"
                dominantBaseline="middle"
                className="fill-foreground/55 text-[8px]"
              >
                {axis.label}
              </text>
            </g>
          );
        })}
        <polygon
          points={points}
          fill="color-mix(in oklab, var(--brand) 22%, transparent)"
          stroke="var(--brand)"
          strokeWidth="2"
        />
      </svg>
    </div>
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

function CertificationGapList({ gaps }: { gaps: CertificationGap[] }) {
  if (gaps.length === 0) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
        Certification gaps
      </p>
      <div className="space-y-2">
        {gaps.map((gap) => (
          <GapRow
            key={certName(gap)}
            title={certName(gap)}
            meta={gap.priority || gap.status || "recommended"}
            body={`${certName(gap)} is listed for this role and was not found in your profile.`}
          />
        ))}
      </div>
    </ModalBlock>
  );
}

function SeniorityGap({ seniority }: { seniority: SeniorityDimension }) {
  const body = seniority.note || seniorityCopy(seniority);
  if (!body) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
        Seniority gap
      </p>
      <GapRow
        title={seniority.gap === "match" ? "Seniority aligned" : "Seniority check"}
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

function SkillSection({
  title,
  items,
  highlight = false,
}: {
  title: string;
  items: string[];
  highlight?: boolean;
}) {
  if (items.length === 0) return null;
  return (
    <ModalBlock className="mb-5">
      <p className="mb-2 text-[10px] uppercase tracking-[0.18em] text-foreground/45">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {items.map((item) => (
          <span
            key={item}
            className={
              highlight
                ? "rounded-full bg-[color:var(--brand)]/10 px-2.5 py-1 text-[12px] text-[color:var(--brand-deep)]"
                : "rounded-full border border-foreground/10 bg-foreground/[0.03] px-2.5 py-1 text-[12px] text-foreground/70"
            }
          >
            {item}
          </span>
        ))}
      </div>
    </ModalBlock>
  );
}

function clamp01(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(1, value));
}

function percent(value: number): number {
  return Math.round(clamp01(value > 1 ? value / 100 : value) * 100);
}

function radarPoint(scale: number, angle: number): string {
  const radians = (Math.PI / 180) * angle;
  const radius = 38 * scale;
  return `${60 + Math.cos(radians) * radius},${60 + Math.sin(radians) * radius}`;
}

function seniorityScore(seniority: SeniorityDimension): number {
  if (seniority.gap === "match") return 1;
  if (seniority.gap === "over") return 0.8;
  if (seniority.gap === "under") return 0.5;
  return 0.7;
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

function certName(gap: CertificationGap): string {
  return gap.required_certification || gap.name || gap.normalized_name || "Certification";
}

function uniqueCertGaps(gaps: CertificationGap[]): CertificationGap[] {
  const byName = new Map<string, CertificationGap>();
  for (const gap of gaps) byName.set(certName(gap).toLowerCase(), gap);
  return [...byName.values()];
}

function seniorityCopy(seniority: SeniorityDimension): string {
  if (seniority.gap === "match") return "Your current level appears aligned with this role.";
  if (seniority.gap === "over") return "Your profile may be above the level implied by this role.";
  if (seniority.gap === "under")
    return "This role appears to require more seniority than your profile shows.";
  return "There is not enough seniority signal to compare levels confidently.";
}
