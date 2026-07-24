import { motion } from "framer-motion";
import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { ArrowLeft, ChevronRight, Clock, Wallet } from "lucide-react";
import { buildRoadmapPreviewNodes, type RoadmapPreviewNode } from "@/lib/roadmapPreview";
import { bucketScoreLabel, bucketTone, roleMatchesToViews } from "@/lib/roleView";
import { useStageStore } from "@/state/useStageStore";
import type { CareerPathReport } from "@/lib/api";
import type { RoleView } from "@/types";
import { RoadmapNodeIcon } from "../RoadmapNodeIcon";
import { FullPlanModal } from "../modals/FullPlanModal";

export function FocusStage() {
  const setStage = useStageStore((s) => s.setStage);
  const selectedIds = useStageStore((s) => s.selectedRoleIds);
  const roleMatches = useStageStore((s) => s.roleMatches);
  const cvData = useStageStore((s) => s.cvData);
  const identity = useStageStore((s) => s.identity);
  const careerPathReports = useStageStore((s) => s.careerPathReports);
  const careerPathLoading = useStageStore((s) => s.careerPathLoading);
  const careerPathErrors = useStageStore((s) => s.careerPathErrors);
  const loadCareerPath = useStageStore((s) => s.loadCareerPath);
  const [planRole, setPlanRole] = useState<RoleView | null>(null);

  const startRole =
    identity?.archetype?.trim() || cvData?.personal_info.current_role?.trim() || "Current profile";

  const paths = useMemo(() => {
    const views = roleMatchesToViews(roleMatches);
    if (selectedIds.length === 0) return views.slice(0, 3);
    return views.filter((r) => selectedIds.includes(r.id));
  }, [roleMatches, selectedIds]);

  useEffect(() => {
    paths.forEach((role) => void loadCareerPath(role.id));
  }, [loadCareerPath, paths]);

  return (
    <div className="relative flex w-full flex-col px-6 pb-8 pt-[max(5.5rem,calc(env(safe-area-inset-top)+4.5rem))] sm:px-10 lg:px-16 lg:pt-24">
      <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col gap-4 lg:min-h-0">
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <h2 className="h-stage">
              Your target roles, and{" "}
              <span
                className="italic"
                style={{
                  background: "var(--gradient-warm)",
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                  color: "transparent",
                }}
              >
                how to get there.
              </span>
            </h2>
            <p className="mt-1 max-w-[76ch] text-[13px] leading-relaxed text-foreground/65">
              Open a role for the roadmap and skills gap.
            </p>
          </div>
          <button
            onClick={() => setStage("directions")}
            className="liquid-glass inline-flex w-fit items-center gap-1.5 self-start rounded-full px-3.5 py-2 text-[12.5px] text-foreground/75 transition hover:text-foreground"
          >
            <ArrowLeft size={12} /> back to matches
          </button>
        </motion.div>

        <div
          className="grid flex-1 gap-3 lg:min-h-0"
          style={{ gridTemplateRows: `repeat(${Math.max(paths.length, 1)}, minmax(0, 1fr))` }}
        >
          {paths.map((role, i) => (
            <PathCard
              key={role.id}
              role={role}
              index={i}
              currentRole={startRole}
              report={careerPathReports[role.id] ?? null}
              loading={!!careerPathLoading[role.id]}
              error={careerPathErrors[role.id] ?? null}
              onFullPlan={() => setPlanRole(role)}
            />
          ))}
        </div>
      </div>

      {planRole && (
        <FullPlanModal
          role={planRole}
          currentRole={startRole}
          report={careerPathReports[planRole.id] ?? null}
          loading={!!careerPathLoading[planRole.id]}
          error={careerPathErrors[planRole.id] ?? null}
          open={!!planRole}
          onClose={() => setPlanRole(null)}
        />
      )}
    </div>
  );
}

function PathCard({
  role,
  index,
  currentRole,
  report,
  loading,
  error,
  onFullPlan,
}: {
  role: RoleView;
  index: number;
  currentRole: string;
  report: CareerPathReport | null;
  loading: boolean;
  error: string | null;
  onFullPlan: () => void;
}) {
  const nodes = buildRoadmapPreviewNodes({
    currentRole,
    targetRole: report?.target_role ?? role.title,
    milestones: report?.milestones ?? [],
  });
  const tone = bucketTone(role.bucket);

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.07, ease: [0.22, 1, 0.36, 1] }}
      className="liquid-glass relative grid grid-cols-1 gap-4 overflow-hidden rounded-3xl p-5 lg:grid-cols-[250px_minmax(0,1fr)_auto] lg:items-center lg:gap-7 lg:p-6"
    >
      <div className="flex min-w-0 flex-col gap-2">
        <span
          className="inline-flex w-fit items-center gap-1.5 rounded-full px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-[0.16em]"
          style={{ backgroundColor: tone.background, color: tone.text }}
        >
          <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tone.dot }} />
          {role.trackLabel}
        </span>
        <h3
          className="font-display tracking-tight text-balance"
          style={{ fontSize: "clamp(1.18rem, 1.5vw, 1.45rem)", lineHeight: 1.15 }}
        >
          {role.title}
        </h3>
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-foreground/58">
          {report?.estimated_timeline && (
            <MetaItem icon={<Clock size={13} />} label={report.estimated_timeline} />
          )}
          {role.salary && <MetaItem icon={<Wallet size={13} />} label={role.salary} />}
          <span
            className="font-medium"
            style={{
              background: "var(--gradient-warm)",
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
            }}
          >
            {Math.round(role.fit * 100)}% {bucketScoreLabel(role.bucket)}
          </span>
        </div>
      </div>

      {error && !report ? (
        <div className="rounded-2xl border border-red-200 bg-red-50/70 px-3 py-2 text-[12.5px] text-red-700">
          Roadmap unavailable. Open the full plan for details.
        </div>
      ) : (
        <RoadmapPreview nodes={nodes} loading={loading && !report} />
      )}

      <motion.button
        onClick={onFullPlan}
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.97 }}
        className="inline-flex w-fit items-center gap-1.5 rounded-full px-4 py-2 text-[12.5px] font-medium text-white lg:justify-self-end"
        style={{
          background: "var(--gradient-warm)",
          boxShadow: "0 10px 24px -14px color-mix(in oklab, var(--brand-deep) 60%, transparent)",
        }}
      >
        View full plan <ChevronRight size={13} />
      </motion.button>
    </motion.div>
  );
}

function RoadmapPreview({ nodes, loading }: { nodes: RoadmapPreviewNode[]; loading: boolean }) {
  return (
    <div className="min-w-0 pb-1 sm:overflow-x-auto" aria-busy={loading}>
      <div className="grid grid-cols-1 gap-2 sm:min-w-[520px] sm:grid-cols-4 sm:gap-3">
        {nodes.map((node, index) => (
          <div
            key={`${node.label}-${index}`}
            className="relative flex min-w-0 items-start gap-3 text-left sm:flex-col sm:items-center sm:gap-0 sm:text-center"
          >
            {index < nodes.length - 1 && (
              <span className="absolute left-5 top-10 h-[calc(100%+0.5rem)] border-l border-dotted border-[color:var(--brand)]/45 sm:left-1/2 sm:top-5 sm:h-px sm:w-full sm:translate-x-5 sm:border-l-0 sm:border-t sm:border-[color:var(--brand)]/50" />
            )}
            <span
              className={
                index === 0 || index === nodes.length - 1
                  ? "relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[color:var(--brand)] text-white shadow-[0_12px_24px_-14px_color-mix(in_oklab,var(--brand-deep)_70%,transparent)]"
                  : "relative z-10 grid h-10 w-10 shrink-0 place-items-center rounded-full border border-[color:var(--brand)]/20 bg-white text-[color:var(--brand-deep)]"
              }
            >
              <RoadmapNodeIcon kind={node.kind} size={15} />
            </span>
            <div className="min-w-0 flex-1 sm:flex-none">
              <p className="text-[10px] uppercase tracking-[0.16em] text-foreground/45 sm:mt-2">
                {node.label}
              </p>
              <p className="mt-1 line-clamp-2 break-words text-[12.5px] font-medium leading-snug text-foreground/82">
                {loading && index > 0 && index < nodes.length - 1 ? "Preparing..." : node.title}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MetaItem({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="text-foreground/42">{icon}</span>
      {label}
    </span>
  );
}
