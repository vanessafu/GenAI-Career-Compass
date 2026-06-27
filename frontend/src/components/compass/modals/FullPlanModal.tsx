import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import { SkillGapSection } from "./SkillGapSection";
import { ArrowRight } from "lucide-react";
import type { CareerPathMilestone, CareerPathReport, GapReport } from "@/lib/api";
import type { RoadmapNodeKind } from "@/lib/roadmapPreview";
import type { RoleView } from "@/types";
import { RoadmapNodeIcon } from "../RoadmapNodeIcon";

export function FullPlanModal({
  role,
  currentRole,
  report,
  loading,
  error,
  gapReport,
  gapLoading,
  gapError,
  open,
  onClose,
}: {
  role: RoleView;
  currentRole: string;
  report: CareerPathReport | null;
  loading: boolean;
  error: string | null;
  gapReport: GapReport | null;
  gapLoading: boolean;
  gapError: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const fallbackGapReport = gapReport ?? report?.requirement_breakdown ?? null;
  const targetRole = report?.target_role ?? role.title;

  return (
    <DeepDiveModal
      open={open}
      onClose={onClose}
      title={<PlanTitle currentRole={currentRole} targetRole={targetRole} />}
      subtitle="Full plan"
      wide
    >
      {loading && !report && (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing full plan...</p>
        </ModalBlock>
      )}

      {error && !report && (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{error}</p>
        </ModalBlock>
      )}

      {report && <FullPlanContent report={report} currentRole={currentRole} />}

      <ModalBlock className="mb-4 mt-7 border-t border-foreground/10 pt-6">
        <p className="mb-3 text-[10px] uppercase tracking-[0.18em] text-foreground/45">
          Skills gap
        </p>
      </ModalBlock>

      {gapError && !fallbackGapReport ? (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{gapError}</p>
        </ModalBlock>
      ) : gapLoading && !fallbackGapReport ? (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing skills gap...</p>
        </ModalBlock>
      ) : fallbackGapReport ? (
        <SkillGapSection report={fallbackGapReport} />
      ) : (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">
            No skills gap report is available yet.
          </p>
        </ModalBlock>
      )}

      <ModalBlock className="mt-2 border-t border-foreground/10 pt-4">
        <p className="text-[11.5px] leading-relaxed text-foreground/45">
          Based on role requirements, certifications, seniority, and your confirmed profile.
        </p>
      </ModalBlock>
    </DeepDiveModal>
  );
}

function PlanTitle({ currentRole, targetRole }: { currentRole: string; targetRole: string }) {
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
      <span>{currentRole}</span>
      <ArrowRight
        aria-hidden
        className="mt-1 shrink-0 text-[color:var(--brand)]"
        size={22}
        strokeWidth={1.8}
      />
      <span>{targetRole}</span>
    </span>
  );
}

function FullPlanContent({
  report,
  currentRole,
}: {
  report: CareerPathReport;
  currentRole: string;
}) {
  const readiness = percent(
    report.readiness_score || report.requirement_breakdown.overall_readiness,
  );
  const milestones = [...report.milestones].sort((a, b) => a.order - b.order);
  const profileSummary = cleanProfileSummary(report.current_profile_summary);

  return (
    <>
      <ModalBlock className="mb-5">
        <div className="grid gap-4 border-b border-foreground/10 pb-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <div className="min-w-0">
            <p className="mt-1 line-clamp-2 text-[13px] leading-relaxed text-foreground/70">
              {profileSummary}
            </p>
          </div>
          <div className="flex flex-wrap gap-6 sm:justify-end">
            <Stat label="Readiness" value={`${readiness}%`} />
            {report.estimated_timeline && (
              <Stat label="Timeline" value={report.estimated_timeline} />
            )}
          </div>
        </div>
      </ModalBlock>

      <ModalBlock className="mb-6">
        <p className="mb-3 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Roadmap</p>
        <div className="overflow-x-auto pb-2">
          <div
            className="grid gap-3"
            style={{
              gridTemplateColumns: `130px repeat(${milestones.length}, minmax(180px, 1fr)) 130px`,
              minWidth: `${260 + milestones.length * 180}px`,
            }}
          >
            <PathNode label="Start" title={currentRole} kind="start" active />
            {milestones.map((milestone) => (
              <PathNode
                key={`${milestone.order}-${milestone.title}`}
                label={milestoneKindLabel(milestone.kind)}
                title={milestone.title}
                kind={milestone.kind}
                meta={milestone.timeline}
                detail={milestone.rationale}
              />
            ))}
            <PathNode label="Target role" title={report.target_role} kind="target" active terminal />
          </div>
        </div>
      </ModalBlock>
    </>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[118px] text-left sm:text-right">
      <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">{label}</p>
      <p className="mt-1 whitespace-nowrap font-display text-[2.3rem] leading-none tracking-tight text-[color:var(--brand-deep)]">
        {value}
      </p>
    </div>
  );
}

function PathNode({
  label,
  title,
  kind,
  meta,
  detail,
  active = false,
  terminal = false,
}: {
  label: string;
  title: string;
  kind: RoadmapNodeKind;
  meta?: string;
  detail?: string;
  active?: boolean;
  terminal?: boolean;
}) {
  return (
    <div className="relative flex min-w-0 flex-col items-center text-center">
      {!terminal && (
        <span className="absolute left-1/2 top-5 h-px w-full translate-x-5 border-t border-dotted border-[color:var(--brand)]/45" />
      )}
      <span
        className={
          active
            ? "relative z-10 grid h-10 w-10 place-items-center rounded-full bg-[color:var(--brand)] text-white shadow-[0_12px_24px_-14px_color-mix(in_oklab,var(--brand-deep)_70%,transparent)]"
            : "relative z-10 grid h-10 w-10 place-items-center rounded-full border border-[color:var(--brand)]/20 bg-white text-[color:var(--brand-deep)]"
        }
      >
        <RoadmapNodeIcon kind={kind} size={16} />
      </span>
      <p className="mt-2 text-[10px] uppercase tracking-[0.16em] text-foreground/45">{label}</p>
      <h4 className="mt-1 text-[13px] font-medium leading-snug text-foreground/85">{title}</h4>
      {meta && <p className="mt-1 text-[11px] text-foreground/50">{meta}</p>}
      {detail && (
        <div className="relative mt-5 flex min-h-[124px] w-full flex-col justify-center rounded-2xl border border-foreground/10 bg-white/60 p-3 text-left">
          <svg
            className="pointer-events-none absolute -top-7 left-1/2 h-7 w-12 -translate-x-1/2 overflow-visible"
            viewBox="0 0 48 28"
            aria-hidden
          >
            <path
              d="M24 0 C24 10 13 12 13 26"
              fill="none"
              stroke="var(--brand)"
              strokeDasharray="2 4"
              strokeLinecap="round"
              strokeOpacity="0.45"
              strokeWidth="1.2"
            />
          </svg>
          <p className="text-[12.5px] leading-relaxed text-foreground/65">{detail}</p>
        </div>
      )}
    </div>
  );
}

function milestoneKindLabel(kind: CareerPathMilestone["kind"]): string {
  switch (kind) {
    case "role":
      return "Intermediate role";
    case "project":
      return "Project";
    case "certification":
      return "Certification";
    case "experience":
      return "Experience";
    case "skill":
    default:
      return "Skill";
  }
}

function cleanProfileSummary(summary: string): string {
  const cleaned = summary.trim();
  return cleaned.replace(/^[^:\n]{1,80}:\s*/, "") || "Your confirmed profile starts this plan.";
}

function percent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const normalized = value > 1 ? value / 100 : value;
  return Math.round(Math.max(0, Math.min(1, normalized)) * 100);
}
