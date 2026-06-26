import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import { SkillGapSection } from "./SkillGapSection";
import type { CareerPathMilestone, CareerPathReport, GapReport } from "@/lib/api";
import type { RoleView } from "@/types";

export function FullPlanModal({
  role,
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

  return (
    <DeepDiveModal open={open} onClose={onClose} title={role.title} subtitle="Full plan" wide>
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

      {report && <FullPlanContent report={report} />}

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

function FullPlanContent({ report }: { report: CareerPathReport }) {
  const readiness = percent(
    report.readiness_score || report.requirement_breakdown.overall_readiness,
  );
  const milestones = [...report.milestones].sort((a, b) => a.order - b.order);

  return (
    <>
      <ModalBlock className="mb-5">
        <div className="grid gap-3 border-b border-foreground/10 pb-4 sm:grid-cols-[1fr_auto_auto] sm:items-end">
          <div className="min-w-0">
            <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">
              Current profile {"->"} target role
            </p>
            <p className="mt-1 line-clamp-2 text-[13px] leading-relaxed text-foreground/70">
              {report.current_profile_summary}
            </p>
          </div>
          <Stat label="Readiness" value={`${readiness}%`} large />
          {report.estimated_timeline && <Stat label="Timeline" value={report.estimated_timeline} />}
        </div>
      </ModalBlock>

      <ModalBlock className="mb-6">
        <p className="mb-3 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Roadmap</p>
        <div className="overflow-x-auto pb-2">
          <div
            className="grid min-w-[720px] gap-3"
            style={{ gridTemplateColumns: `repeat(${milestones.length + 2}, minmax(140px, 1fr))` }}
          >
            <PathNode
              label="Start"
              title="Current profile"
              body={report.current_profile_summary}
              active
            />
            {milestones.map((milestone) => (
              <PathNode
                key={`${milestone.order}-${milestone.title}`}
                label={milestoneLabel(milestone)}
                title={milestone.title}
                body={milestone.rationale}
                meta={milestone.timeline}
              />
            ))}
            <PathNode label="Target role" title={report.target_role} active terminal />
          </div>
        </div>
      </ModalBlock>
    </>
  );
}

function Stat({ label, value, large = false }: { label: string; value: string; large?: boolean }) {
  return (
    <div className="text-left sm:text-right">
      <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">{label}</p>
      <p
        className={
          large
            ? "font-display text-4xl tracking-tight text-[color:var(--brand-deep)]"
            : "text-[13px] font-medium text-foreground/80"
        }
      >
        {value}
      </p>
    </div>
  );
}

function PathNode({
  label,
  title,
  body,
  meta,
  active = false,
  terminal = false,
}: {
  label: string;
  title: string;
  body?: string;
  meta?: string;
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
        <span className="h-2 w-2 rounded-full bg-current" />
      </span>
      <p className="mt-2 text-[10px] uppercase tracking-[0.16em] text-foreground/45">{label}</p>
      <h4 className="mt-1 text-[13px] font-medium leading-snug text-foreground/85">{title}</h4>
      {meta && <p className="mt-1 text-[11px] text-foreground/50">{meta}</p>}
      {body && (
        <p className="mt-2 line-clamp-3 text-[12px] leading-relaxed text-foreground/60">{body}</p>
      )}
    </div>
  );
}

function milestoneLabel(milestone: CareerPathMilestone): string {
  return milestone.timeline || `Step ${milestone.order}`;
}

function percent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const normalized = value > 1 ? value / 100 : value;
  return Math.round(Math.max(0, Math.min(1, normalized)) * 100);
}
