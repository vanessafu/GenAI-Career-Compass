import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { useStageStore } from "@/state/useStageStore";
import { roleMatchesToViews } from "@/lib/roleView";
import type { RoleView } from "@/types";
import { RoleDetailModal } from "../modals/RoleDetailModal";
import { ArrowLeft, ChevronRight, Sparkles, BookOpen } from "lucide-react";

/**
 * Your paths — each picked role becomes a detail card built from the backend
 * RoleMatch: the essential skills and knowledge the role demands. "View full
 * plan" opens the complete breakdown (incl. optional skills + analysis).
 */
export function FocusStage() {
  const setStage = useStageStore((s) => s.setStage);
  const selectedIds = useStageStore((s) => s.selectedRoleIds);
  const roleMatches = useStageStore((s) => s.roleMatches);
  const matchAnalysis = useStageStore((s) => s.matchAnalysis);
  const cvData = useStageStore((s) => s.cvData);
  const [detailRole, setDetailRole] = useState<RoleView | null>(null);

  const startRole = cvData?.personal_info.current_role?.trim() || "your current profile";

  const paths = useMemo(() => {
    const views = roleMatchesToViews(roleMatches);
    if (selectedIds.length === 0) return views.slice(0, 3);
    return views.filter((r) => selectedIds.includes(r.id));
  }, [roleMatches, selectedIds]);

  return (
    <div className="relative flex w-full flex-col px-6 pb-8 pt-[max(5.5rem,calc(env(safe-area-inset-top)+4.5rem))] sm:px-10 lg:h-full lg:overflow-hidden lg:px-16 lg:pt-24">
      <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col gap-4 lg:min-h-0">
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"
        >
          <div>
            <p className="text-[11px] uppercase tracking-[0.22em] text-foreground/55">
              Stage 04 · Your paths
            </p>
            <h2 className="h-stage mt-1">
              What these roles{" "}
              <span
                className="italic"
                style={{
                  background: "var(--gradient-warm)",
                  WebkitBackgroundClip: "text",
                  backgroundClip: "text",
                  color: "transparent",
                }}
              >
                ask of you.
              </span>
            </h2>
            <p className="mt-1 max-w-[60ch] text-[13px] leading-relaxed text-foreground/65">
              Starting from <span className="font-medium text-foreground/85">{startRole}</span>.
              Open a role for the full skill and knowledge breakdown.
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
            <PathCard key={role.id} role={role} index={i} onDetails={() => setDetailRole(role)} />
          ))}
        </div>
      </div>

      {detailRole && (
        <RoleDetailModal
          role={detailRole}
          analysis={matchAnalysis}
          open={!!detailRole}
          onClose={() => setDetailRole(null)}
        />
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */

function PathCard({
  role,
  index,
  onDetails,
}: {
  role: RoleView;
  index: number;
  onDetails: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: index * 0.07, ease: [0.22, 1, 0.36, 1] }}
      className="liquid-glass relative grid grid-cols-1 gap-4 overflow-hidden rounded-3xl p-5 lg:grid-cols-[240px_1fr_auto] lg:items-center lg:gap-6 lg:p-6"
    >
      <div className="flex flex-col gap-2">
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-[color:var(--brand)]/10 px-2 py-0.5 text-[10.5px] font-medium uppercase tracking-[0.16em] text-[color:var(--brand-deep)]">
          <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--brand)]" />
          {role.trackLabel}
        </span>
        <h3
          className="font-display tracking-tight"
          style={{ fontSize: "clamp(1.2rem, 1.6vw, 1.45rem)", lineHeight: 1.15 }}
        >
          {role.title}
        </h3>
        <span
          className="w-fit font-medium text-[12px]"
          style={{
            background: "var(--gradient-warm)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          {Math.round(role.fit * 100)}% fit
        </span>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <SkillPreview
          icon={<Sparkles size={12} />}
          label="Essential skills"
          items={role.essentialSkills}
        />
        <SkillPreview
          icon={<BookOpen size={12} />}
          label="Essential knowledge"
          items={role.essentialKnowledge}
        />
      </div>

      <motion.button
        onClick={onDetails}
        whileHover={{ y: -1 }}
        whileTap={{ scale: 0.97 }}
        className="inline-flex w-fit items-center gap-1.5 self-end rounded-full px-4 py-2 text-[12.5px] font-medium text-white lg:self-center"
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

function SkillPreview({
  icon,
  label,
  items,
}: {
  icon: React.ReactNode;
  label: string;
  items: string[];
}) {
  const shown = items.slice(0, 4);
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <p className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-[0.16em] text-foreground/45">
        <span className="text-[color:var(--brand)]">{icon}</span>
        {label}
      </p>
      {shown.length === 0 ? (
        <p className="text-[12px] text-foreground/45">—</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {shown.map((item) => (
            <span
              key={item}
              className="line-clamp-1 max-w-full rounded-full border border-foreground/10 bg-white/70 px-2 py-0.5 text-[11.5px] text-foreground/75"
            >
              {item}
            </span>
          ))}
          {items.length > shown.length && (
            <span className="rounded-full px-1.5 py-0.5 text-[11.5px] text-foreground/45">
              +{items.length - shown.length}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
