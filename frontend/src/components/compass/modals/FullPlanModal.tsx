import { DeepDiveModal, ModalBlock } from "./DeepDiveModal";
import { SkillGapSection } from "./SkillGapSection";
import { AnimatedPercent } from "./AnimatedPercent";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowRight, ChevronDown } from "lucide-react";
import { useId, useLayoutEffect, useRef, useState } from "react";
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

type RoadmapDetailNode = PlanNode & {
  index: number;
  x: number;
  connectorStartY: number;
  detail: string;
  detailIndex: number;
  descriptionX: number;
};

const DEFAULT_ROADMAP_CANVAS_HEIGHT = 148;
const DEFAULT_EXPANDED_ROADMAP_CANVAS_HEIGHT = 280;
const DEFAULT_DETAIL_LAYER_HEIGHT = 148;
const ROADMAP_HEIGHT_PADDING = 16;
const SINGLE_TIMELINE_RE = /^\s*(\d+)\s*(weeks?|months?)\s*$/i;

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
  const [showStepDetails, setShowStepDetails] = useState(false);
  const fallbackGapReport = report?.requirement_breakdown ?? gapReport ?? null;
  const targetRole = report?.target_role ?? role.title;
  const readiness = report
    ? percent(report.readiness_score ?? report.requirement_breakdown.overall_readiness)
    : null;
  const planSummary = report ? reportPlanSummary(report) : "";
  const visibleMilestones = report ? displayMilestones(report.milestones) : [];

  return (
    <DeepDiveModal
      open={open}
      onClose={onClose}
      title={<PlanTitle currentRole={currentRole} targetRole={targetRole} />}
      subtitle="Full plan"
      headerAside={
        readiness !== null ? (
          <PlanStats
            readiness={readiness}
            timeline={report ? displayTimeline(report) : undefined}
          />
        ) : undefined
      }
      headerDescription={
        report ? <PlanHeaderDescription summary={planSummary} role={role} /> : undefined
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

      {report && (
        <FullPlanContent
          report={report}
          milestones={visibleMilestones}
          currentRole={currentRole}
          showStepDetails={showStepDetails}
          onToggleStepDetails={() => setShowStepDetails((shown) => !shown)}
        />
      )}

      {gapError && !fallbackGapReport ? (
        <ModalBlock className="mb-6 border-l-2 border-red-300 pl-3">
          <p className="text-[13px] leading-relaxed text-red-700">{gapError}</p>
        </ModalBlock>
      ) : gapLoading && !fallbackGapReport ? (
        <ModalBlock className="mb-6">
          <p className="text-[13px] leading-relaxed text-foreground/60">Preparing skills gap...</p>
        </ModalBlock>
      ) : fallbackGapReport ? (
        <SkillGapSection report={fallbackGapReport} milestones={visibleMilestones} />
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

function PlanStats({ readiness, timeline }: { readiness: number; timeline?: string }) {
  return (
    <div className="flex w-full min-w-0 items-end justify-between gap-3 pt-3 text-left md:min-w-[150px] md:flex-col md:items-end md:text-right">
      <Stat label="Readiness" value={<AnimatedPercent value={readiness} />} />
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
  milestones,
  currentRole,
  showStepDetails,
  onToggleStepDetails,
}: {
  report: CareerPathReport;
  milestones: CareerPathMilestone[];
  currentRole: string;
  showStepDetails: boolean;
  onToggleStepDetails: () => void;
}) {
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
          <RoadmapCanvas roadmapNodes={roadmapNodes} showStepDetails={showStepDetails} />
        </div>
        <div className="flex flex-col gap-4 md:hidden">
          {roadmapNodes.map((node, index) => (
            <StackedPathNode
              key={`${node.label}-${node.title}-${index}`}
              node={node}
              terminal={index === roadmapNodes.length - 1}
              showStepDetails={showStepDetails}
            />
          ))}
        </div>
        <RoadmapDetailsToggle expanded={showStepDetails} onToggle={onToggleStepDetails} />
      </ModalBlock>
    </>
  );
}

function RoadmapCanvas({
  roadmapNodes,
  showStepDetails,
}: {
  roadmapNodes: PlanNode[];
  showStepDetails: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const canvasRef = useRef<HTMLDivElement>(null);
  const [roadmapHeights, setRoadmapHeights] = useState({
    compact: DEFAULT_ROADMAP_CANVAS_HEIGHT,
    expanded: DEFAULT_EXPANDED_ROADMAP_CANVAS_HEIGHT,
  });
  const [nodeBottoms, setNodeBottoms] = useState<Record<number, number>>({});
  const canvasWidth = 1000;
  const lineTop = 38;
  const iconTop = 18;
  const detailLayerTop = 132;
  const detailLayerHeight = Math.max(
    DEFAULT_DETAIL_LAYER_HEIGHT,
    roadmapHeights.expanded - detailLayerTop,
  );
  const nodeRemWidth = Math.max(7.5, Math.min(13, 74 / roadmapNodes.length));
  const nodePercentWidth = Math.min(16, (84 / Math.max(roadmapNodes.length - 1, 1)) * 0.9);
  const nodeWidth = `min(${nodeRemWidth}rem, ${nodePercentWidth}%)`;
  const positionedNodes = roadmapNodes.map((node, index) => ({
    ...node,
    index,
    x: canvasX(index, roadmapNodes.length),
    connectorStartY: nodeBottoms[index] ? Math.max(0, nodeBottoms[index] - detailLayerTop + 10) : 0,
  }));
  const rawDetailNodes = positionedNodes.filter(
    (
      node,
    ): node is PlanNode & {
      index: number;
      x: number;
      connectorStartY: number;
      detail: string;
    } => Boolean(node.detail),
  );
  const detailNodes = rawDetailNodes.map((node, detailIndex) => ({
    ...node,
    detailIndex,
    descriptionX: descriptionCenterX(detailIndex, rawDetailNodes.length),
  }));
  const startX = canvasX(0, roadmapNodes.length);
  const endX = canvasX(roadmapNodes.length - 1, roadmapNodes.length);
  const heightTransition = reduceMotion
    ? { duration: 0 }
    : { type: "spring" as const, stiffness: 220, damping: 30, mass: 0.8 };

  useLayoutEffect(() => {
    const root = canvasRef.current;
    if (!root) return;

    const measure = () => {
      const rootTop = root.getBoundingClientRect().top;
      const nodeBottom = measuredBottom(root, "[data-roadmap-node]", rootTop);
      const detailBottom = measuredBottom(root, "[data-roadmap-detail]", rootTop);
      const nextNodeBottoms = Object.fromEntries(
        Array.from(root.querySelectorAll<HTMLElement>("[data-roadmap-node]")).map((element) => [
          Number(element.dataset.roadmapIndex),
          element.getBoundingClientRect().bottom - rootTop,
        ]),
      ) as Record<number, number>;
      const compact = Math.max(
        DEFAULT_ROADMAP_CANVAS_HEIGHT,
        Math.ceil(nodeBottom + ROADMAP_HEIGHT_PADDING),
      );
      const expanded = Math.max(
        DEFAULT_EXPANDED_ROADMAP_CANVAS_HEIGHT,
        Math.ceil(Math.max(nodeBottom, detailBottom) + ROADMAP_HEIGHT_PADDING),
      );

      setRoadmapHeights((current) =>
        current.compact === compact && current.expanded === expanded
          ? current
          : { compact, expanded },
      );
      setNodeBottoms((current) =>
        sameNumberRecord(current, nextNodeBottoms) ? current : nextNodeBottoms,
      );
    };

    const frame = window.requestAnimationFrame(measure);
    const observer = new ResizeObserver(measure);
    root
      .querySelectorAll<HTMLElement>("[data-roadmap-node],[data-roadmap-detail]")
      .forEach((node) => observer.observe(node));

    return () => {
      window.cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [roadmapNodes, showStepDetails]);

  return (
    <motion.div
      ref={canvasRef}
      className="relative overflow-hidden"
      animate={{ height: showStepDetails ? roadmapHeights.expanded : roadmapHeights.compact }}
      transition={heightTransition}
    >
      <span
        className="absolute h-px border-t border-dashed border-[color:var(--brand)]/45"
        style={{
          top: lineTop,
          left: `${(startX / canvasWidth) * 100}%`,
          right: `${100 - (endX / canvasWidth) * 100}%`,
        }}
      />
      <RoadmapDetailLayer
        canvasWidth={canvasWidth}
        detailLayerHeight={detailLayerHeight}
        detailLayerTop={detailLayerTop}
        detailNodes={detailNodes}
        reduceMotion={reduceMotion}
        showStepDetails={showStepDetails}
      />
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
    </motion.div>
  );
}

function measuredBottom(root: HTMLElement, selector: string, rootTop: number): number {
  return Array.from(root.querySelectorAll<HTMLElement>(selector)).reduce((bottom, element) => {
    const rect = element.getBoundingClientRect();
    return Math.max(bottom, rect.bottom - rootTop);
  }, 0);
}

function sameNumberRecord(left: Record<number, number>, right: Record<number, number>): boolean {
  const keys = new Set([...Object.keys(left), ...Object.keys(right)]);
  return Array.from(keys).every((key) => left[Number(key)] === right[Number(key)]);
}

function RoadmapDetailLayer({
  canvasWidth,
  detailLayerHeight,
  detailLayerTop,
  detailNodes,
  reduceMotion,
  showStepDetails,
}: {
  canvasWidth: number;
  detailLayerHeight: number;
  detailLayerTop: number;
  detailNodes: RoadmapDetailNode[];
  reduceMotion: boolean | null;
  showStepDetails: boolean;
}) {
  const clipBaseId = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const pillTop = 58;
  const descriptionTop = 102;
  const lineEndTop = descriptionTop;
  const detailStepDelay = 0.18;
  const layerTransition = reduceMotion
    ? { duration: 0 }
    : { type: "spring" as const, stiffness: 220, damping: 30, mass: 0.8 };
  const drawTransition = (delay: number) =>
    reduceMotion
      ? { duration: 0 }
      : showStepDetails
        ? { duration: 0.42, ease: [0.22, 1, 0.36, 1] as const, delay }
        : { duration: 0.14, ease: [0.4, 0, 1, 1] as const };
  const fadeTransition = (delay: number) =>
    reduceMotion
      ? { duration: 0 }
      : showStepDetails
        ? { type: "spring" as const, stiffness: 260, damping: 28, mass: 0.72, delay }
        : { duration: 0.1, ease: [0.4, 0, 1, 1] as const };

  return (
    <motion.div
      className="absolute left-0 right-0 overflow-hidden"
      aria-hidden={!showStepDetails}
      style={{ top: detailLayerTop }}
      initial={false}
      animate={{ height: showStepDetails ? detailLayerHeight : 0 }}
      transition={layerTransition}
    >
      <svg
        className="pointer-events-none absolute inset-0 h-full w-full"
        viewBox={`0 0 ${canvasWidth} ${detailLayerHeight}`}
        preserveAspectRatio="none"
        aria-hidden
      >
        <defs>
          {detailNodes.map((node) => {
            const lineDelay = showStepDetails ? node.detailIndex * detailStepDelay + 0.06 : 0;

            return (
              <clipPath
                key={`${node.title}-clip-${node.index}`}
                id={`${clipBaseId}-${node.index}`}
                clipPathUnits="userSpaceOnUse"
              >
                <motion.rect
                  x={0}
                  y={0}
                  width={canvasWidth}
                  initial={false}
                  animate={{ height: showStepDetails ? detailLayerHeight : 0 }}
                  transition={drawTransition(lineDelay)}
                />
              </clipPath>
            );
          })}
        </defs>
        {detailNodes.map((node) => (
          <path
            key={`${node.title}-connector-${node.index}`}
            clipPath={`url(#${clipBaseId}-${node.index})`}
            d={canvasConnectorPath(
              node.x,
              node.descriptionX,
              node.connectorStartY,
              pillTop,
              lineEndTop,
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
      {detailNodes.length > 0 && (
        <div className="absolute left-0 right-0" style={{ top: descriptionTop }}>
          <div
            className="grid"
            style={{
              gridTemplateColumns: `repeat(${detailNodes.length}, minmax(0, 1fr))`,
            }}
          >
            {detailNodes.map((node) => {
              const lineDelay = showStepDetails ? node.detailIndex * detailStepDelay + 0.06 : 0;
              const descriptionDelay = lineDelay + 0.3;

              return (
                <motion.div
                  key={`${node.title}-detail-${node.index}`}
                  data-roadmap-detail
                  className="min-w-0 px-4 text-center"
                  initial={false}
                  animate={{ opacity: showStepDetails ? 1 : 0, y: showStepDetails ? 0 : -5 }}
                  transition={fadeTransition(descriptionDelay)}
                >
                  <p className="break-words text-[13px] leading-relaxed text-foreground/65">
                    {node.detail}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
      {detailNodes.map((node) => {
        const lineDelay = showStepDetails ? node.detailIndex * detailStepDelay + 0.06 : 0;
        const pillDelay = lineDelay + 0.44;

        return (
          <motion.div
            key={`${node.title}-meta-${node.index}`}
            data-roadmap-detail
            className="absolute -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-full bg-white/85 px-2 py-0.5 text-[11px] font-medium text-foreground/45"
            initial={false}
            animate={{ opacity: showStepDetails ? 1 : 0, scale: showStepDetails ? 1 : 0.96 }}
            transition={fadeTransition(pillDelay)}
            style={{
              left: `${(node.descriptionX / canvasWidth) * 100}%`,
              top: pillTop,
            }}
          >
            {node.meta}
          </motion.div>
        );
      })}
    </motion.div>
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

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
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
  index,
  label,
  title,
  kind,
  active = false,
  terminal = false,
  style,
}: {
  index?: number;
  label: string;
  title: string;
  kind: RoadmapNodeKind;
  active?: boolean;
  terminal?: boolean;
  style?: React.CSSProperties;
}) {
  return (
    <div
      data-roadmap-node
      data-roadmap-index={index}
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

function RoadmapDetailsToggle({ expanded, onToggle }: { expanded: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={expanded}
      className="mx-auto mt-3 flex w-fit items-center gap-1.5 text-[12px] font-medium text-[color:var(--brand-deep)] outline-none transition hover:text-[color:var(--brand)] focus-visible:text-[color:var(--brand)] focus-visible:underline focus-visible:underline-offset-4"
    >
      {expanded ? "Hide details" : "Show details"}
      <ChevronDown
        aria-hidden
        size={13}
        className={expanded ? "rotate-180 transition-transform" : "transition-transform"}
      />
    </button>
  );
}

function StackedPathNode({
  node,
  terminal,
  showStepDetails,
}: {
  node: PlanNode;
  terminal: boolean;
  showStepDetails: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const transition = reduceMotion
    ? { duration: 0 }
    : { type: "spring" as const, stiffness: 240, damping: 28, mass: 0.75 };

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
        <AnimatePresence initial={false}>
          {showStepDetails && node.detail && (
            <motion.div
              key="mobile-step-details"
              className="overflow-hidden"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={transition}
            >
              <div className="mt-3 text-left">
                {node.meta && (
                  <span className="mb-2 inline-flex rounded-full bg-white/80 px-2 py-0.5 text-[11px] font-medium text-foreground/45">
                    {node.meta}
                  </span>
                )}
                <p className="text-[13px] leading-loose text-foreground/65">{node.detail}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
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

function displayMilestones(milestones: CareerPathMilestone[]): CareerPathMilestone[] {
  return [...milestones]
    .sort((a, b) => a.order - b.order)
    .map((milestone) => ({ ...milestone, timeline: formatTimeline(milestone.timeline) }));
}

function displayTimeline(report: CareerPathReport): string {
  return (
    totalTimeline(displayMilestones(report.milestones)) || formatTimeline(report.estimated_timeline)
  );
}

function totalTimeline(milestones: CareerPathMilestone[]): string {
  const durations = milestones.map((milestone) => durationWeeks(milestone.timeline));
  if (durations.some((duration) => duration === null)) return "";

  return formatDurationWeeks((durations as number[]).reduce((total, weeks) => total + weeks, 0));
}

function formatTimeline(timeline: string): string {
  const weeks = durationWeeks(timeline);
  return weeks === null ? timeline.trim() : formatDurationWeeks(weeks);
}

function durationWeeks(timeline: string): number | null {
  const single = SINGLE_TIMELINE_RE.exec(timeline);
  if (!single) return null;
  const value = Number(single[1]);
  const unit = single[2].toLowerCase();
  return unit.startsWith("month") ? value * 4 : value;
}

function formatDurationWeeks(weeks: number): string {
  const amount = Math.max(0, Math.round(weeks));
  if (amount <= 4) return `${amount} ${amount === 1 ? "week" : "weeks"}`;
  const months = Math.ceil(amount / 4);
  return `${months} ${months === 1 ? "month" : "months"}`;
}

function reportPlanSummary(report: CareerPathReport): string {
  const summary = (report.plan_summary ?? "").trim();
  if (summary && !summaryMatchesProfile(summary, report.current_profile_summary)) return summary;

  const gaps = report.top_gaps.filter(Boolean).slice(0, 3);
  const matched = report.requirement_breakdown.skills.matched_skills.filter(Boolean).slice(0, 3);
  const readiness = percent(
    report.readiness_score ?? report.requirement_breakdown.overall_readiness,
  );
  const closeness =
    readiness >= 75
      ? "You're already close"
      : readiness >= 55
        ? "You're within reach"
        : "This is a stretch, but there is a path";
  const matchedText = matched.length
    ? `Your strongest overlap is ${formatList(matched)}.`
    : "You already have some useful overlap with the role.";
  const gapText = gaps.length
    ? `The main thing to strengthen next is ${formatList(gaps)}.`
    : "What remains is mostly making your fit easier to recognize.";

  return `${closeness} for ${report.target_role}: about ${readiness}% of the role signals are already there. ${matchedText} ${gapText}`;
}

function summaryMatchesProfile(summary: string, profileSummary: string): boolean {
  const summaryKey = summary.trim().replace(/\s+/g, " ").toLowerCase();
  const profileKey = profileSummary.trim().replace(/\s+/g, " ").toLowerCase();
  return Boolean(profileKey && (summaryKey === profileKey || summaryKey.startsWith(profileKey)));
}

function formatList(values: string[]): string {
  if (values.length <= 1) return values[0] ?? "";
  if (values.length === 2) return `${values[0]} and ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
}

function percent(value: number): number {
  if (!Number.isFinite(value)) return 0;
  const normalized = value > 1 ? value / 100 : value;
  return Math.round(Math.max(0, Math.min(1, normalized)) * 100);
}
