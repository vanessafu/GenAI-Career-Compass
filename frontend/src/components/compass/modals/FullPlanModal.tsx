import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import { SkillGapSection } from "./SkillGapSection";
import { ArrowRight } from "lucide-react";
import type { CareerPathMilestone, CareerPathReport, GapReport } from "@/lib/api";
import type { RoadmapNodeKind } from "@/lib/roadmapPreview";
import type { RoleView } from "@/types";
import { RoadmapNodeIcon } from "../RoadmapNodeIcon";

type PlanNode = {
  label: string;
  title: string;
  kind: RoadmapNodeKind;
  meta?: string;
  detail?: string;
  active?: boolean;
};

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
  const readiness = report
    ? percent(report.readiness_score || report.requirement_breakdown.overall_readiness)
    : null;
  const profileSummary = report ? cleanProfileSummary(report.current_profile_summary) : "";

  return (
    <DeepDiveModal
      open={open}
      onClose={onClose}
      title={<PlanTitle currentRole={currentRole} targetRole={targetRole} />}
      subtitle="Full plan"
      headerAside={
        readiness !== null ? (
          <PlanStats readiness={`${readiness}%`} timeline={report?.estimated_timeline} />
        ) : undefined
      }
      headerDescription={
        report ? <PlanHeaderDescription summary={profileSummary} role={role} /> : undefined
      }
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

      <ModalBlock className="mb-4 mt-1 border-t border-foreground/10 pt-4">
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

function PlanStats({ readiness, timeline }: { readiness: string; timeline?: string }) {
  return (
    <div className="flex min-w-[150px] flex-col items-end gap-3 pt-3 text-right">
      <Stat label="Readiness" value={readiness} />
      {timeline && <Stat label="Timeline" value={timeline} />}
    </div>
  );
}

function PlanHeaderDescription({ summary, role }: { summary: string; role: RoleView }) {
  return (
    <div className="max-w-[72rem]">
      <p className="text-[13px] leading-relaxed text-foreground/70">{summary}</p>
      <EscoReference title={role.escoTitle} uri={role.escoUri} />
    </div>
  );
}

function FullPlanContent({
  report,
  currentRole,
}: {
  report: CareerPathReport;
  currentRole: string;
}) {
  const milestones = [...report.milestones].sort((a, b) => a.order - b.order);
  const roadmapNodes: PlanNode[] = [
    { label: "Start", title: currentRole, kind: "start", active: true },
    ...milestones.map((milestone) => ({
      label: milestoneKindLabel(milestone.kind),
      title: milestone.title,
      kind: milestone.kind,
      meta: milestone.timeline,
      detail: milestone.rationale,
    })),
    { label: "Target role", title: report.target_role, kind: "target", active: true },
  ];

  return (
    <>
      <ModalBlock className="mb-1 border-t border-foreground/10 pt-6">
        <p className="mb-3 text-[10px] uppercase tracking-[0.18em] text-foreground/45">Roadmap</p>
        <div className="hidden md:block">
          <RoadmapCanvas roadmapNodes={roadmapNodes} />
        </div>
        <div className="flex flex-col gap-4 md:hidden">
          {roadmapNodes.map((node, index) => (
            <StackedPathNode
              key={`${node.label}-${node.title}-${index}`}
              node={node}
              terminal={index === roadmapNodes.length - 1}
            />
          ))}
        </div>
      </ModalBlock>
    </>
  );
}

function RoadmapCanvas({ roadmapNodes }: { roadmapNodes: PlanNode[] }) {
  const canvasWidth = 1000;
  const lineTop = 38;
  const iconTop = 18;
  const connectorTop = 126;
  const durationTop = 178;
  const descriptionTop = 222;
  const nodeRemWidth = Math.max(7.5, Math.min(13, 74 / roadmapNodes.length));
  const nodePercentWidth = Math.min(16, (84 / Math.max(roadmapNodes.length - 1, 1)) * 0.9);
  const nodeWidth = `min(${nodeRemWidth}rem, ${nodePercentWidth}%)`;
  const positionedNodes = roadmapNodes.map((node, index) => ({
    ...node,
    index,
    x: canvasX(index, roadmapNodes.length),
  }));
  const rawDetailNodes = positionedNodes.filter(
    (node): node is PlanNode & { index: number; x: number; detail: string } => Boolean(node.detail),
  );
  const detailNodes = rawDetailNodes.map((node, detailIndex) => ({
    ...node,
    detailIndex,
    descriptionX: descriptionCenterX(detailIndex, rawDetailNodes.length),
  }));
  const startX = canvasX(0, roadmapNodes.length);
  const endX = canvasX(roadmapNodes.length - 1, roadmapNodes.length);

  return (
    <div className="relative h-[280px] overflow-x-hidden">
      <span
        className="absolute h-px border-t border-dashed border-[color:var(--brand)]/45"
        style={{
          top: lineTop,
          left: `${(startX / canvasWidth) * 100}%`,
          right: `${100 - (endX / canvasWidth) * 100}%`,
        }}
      />
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox="0 0 1000 280"
        preserveAspectRatio="none"
        aria-hidden
      >
        {detailNodes.map((node) => (
          <path
            key={`${node.title}-connector-${node.index}`}
            d={canvasConnectorPath(
              node.x,
              node.descriptionX,
              connectorTop,
              durationTop,
              descriptionTop,
            )}
            fill="none"
            stroke="var(--brand)"
            strokeDasharray="4 7"
            strokeLinecap="butt"
            strokeOpacity="0.55"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      </svg>
      {positionedNodes.map((node, index) => (
        <PathNode
          key={`${node.label}-${node.title}-${index}`}
          {...node}
          terminal={index === roadmapNodes.length - 1}
          style={{
            left: `${(node.x / canvasWidth) * 100}%`,
            top: iconTop,
            width: nodeWidth,
          }}
        />
      ))}
      {detailNodes.map((node) => (
        <div
          key={`${node.title}-meta-${node.index}`}
          className="absolute -translate-x-1/2 whitespace-nowrap rounded-full bg-white/85 px-2 py-0.5 text-[11px] font-medium text-foreground/45"
          style={{ left: `${(node.descriptionX / canvasWidth) * 100}%`, top: durationTop - 14 }}
        >
          {node.meta}
        </div>
      ))}
      {detailNodes.length > 0 && (
        <div className="absolute left-0 right-0" style={{ top: descriptionTop }}>
          <div
            className="grid"
            style={{
              gridTemplateColumns: `repeat(${detailNodes.length}, minmax(0, 1fr))`,
            }}
          >
            {detailNodes.map((node) => (
              <div key={`${node.title}-detail-${node.index}`} className="min-w-0 px-4 text-center">
                <p className="break-words text-[13px] leading-relaxed text-foreground/65">
                  {node.detail}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function descriptionCenterX(index: number, total: number): number {
  const canvasWidth = 1000;
  return ((index + 0.5) / Math.max(total, 1)) * canvasWidth;
}

function canvasConnectorPath(
  fromX: number,
  toX: number,
  startY: number,
  pillY: number,
  endY: number,
): string {
  const bend = Math.min(80, Math.max(-80, (toX - fromX) * 0.25));
  return [
    `M ${fromX} ${startY}`,
    `C ${fromX} ${startY + 28} ${toX - bend} ${pillY - 28} ${toX} ${pillY}`,
    `L ${toX} ${endY}`,
  ].join(" ");
}

function canvasX(index: number, total: number): number {
  const canvasWidth = 1000;
  if (total <= 1) return canvasWidth / 2;
  const inset = 8;
  const percent = inset + ((100 - inset * 2) * index) / (total - 1);
  return (percent / 100) * canvasWidth;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.18em] text-foreground/45">{label}</p>
      <p className="mt-1 whitespace-nowrap font-display text-[2rem] leading-none tracking-tight text-[color:var(--brand-deep)]">
        {value}
      </p>
    </div>
  );
}

function EscoReference({ title, uri }: { title: string; uri: string }) {
  const label = title || uri;
  if (!label) return null;

  return (
    <p className="mt-3 text-[12px] leading-relaxed text-foreground/50">
      <span className="mr-1 uppercase tracking-[0.14em]">ESCO reference</span>
      {uri ? (
        <a
          href={uri}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[color:var(--brand-deep)] underline-offset-4 hover:underline"
        >
          {label}
        </a>
      ) : (
        <span className="font-medium text-foreground/70">{label}</span>
      )}
    </p>
  );
}

function PathNode({
  label,
  title,
  kind,
  active = false,
  terminal = false,
  style,
}: {
  label: string;
  title: string;
  kind: RoadmapNodeKind;
  active?: boolean;
  terminal?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <div
      className={
        style
          ? "absolute flex min-w-0 -translate-x-1/2 flex-col items-center text-center"
          : "relative flex min-w-0 flex-col items-center text-center"
      }
      style={style}
    >
      {!terminal && (
        <span
          className={
            style
              ? "hidden"
              : "absolute left-1/2 right-[-50%] top-5 h-px border-t border-dashed border-[color:var(--brand)]/45"
          }
        />
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
      <h4 className="mt-1 break-words text-[13px] font-medium leading-snug text-foreground/85">
        {title}
      </h4>
    </div>
  );
}

function StackedPathNode({ node, terminal }: { node: PlanNode; terminal: boolean }) {
  return (
    <div className="relative grid grid-cols-[44px_minmax(0,1fr)] gap-3">
      {!terminal && (
        <span className="absolute bottom-[-1rem] left-5 top-10 border-l border-dotted border-[color:var(--brand)]/45" />
      )}
      <span
        className={
          node.active
            ? "relative z-10 grid h-10 w-10 place-items-center rounded-full bg-[color:var(--brand)] text-white shadow-[0_12px_24px_-14px_color-mix(in_oklab,var(--brand-deep)_70%,transparent)]"
            : "relative z-10 grid h-10 w-10 place-items-center rounded-full border border-[color:var(--brand)]/20 bg-white text-[color:var(--brand-deep)]"
        }
      >
        <RoadmapNodeIcon kind={node.kind} size={16} />
      </span>
      <div className="min-w-0 pb-1">
        <p className="text-[10px] uppercase tracking-[0.16em] text-foreground/45">{node.label}</p>
        <h4 className="mt-1 text-[13px] font-medium leading-snug text-foreground/85">
          {node.title}
        </h4>
        {node.detail && (
          <div className="mt-3 text-left">
            {node.meta && (
              <span className="mb-2 inline-flex rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-medium text-foreground/45">
                {node.meta}
              </span>
            )}
            <p className="text-[13px] leading-loose text-foreground/65">{node.detail}</p>
          </div>
        )}
      </div>
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
