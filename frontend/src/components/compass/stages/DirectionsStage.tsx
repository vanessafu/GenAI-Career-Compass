import { motion } from "framer-motion";
import { useMemo } from "react";
import { useStageStore, MAX_PICKS } from "@/state/useStageStore";
import { roleMatchesToViews } from "@/lib/roleView";
import type { RoleView } from "@/types";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { cn } from "@/lib/utils";

export function DirectionsStage() {
  const setStage = useStageStore((s) => s.setStage);
  const roleMatches = useStageStore((s) => s.roleMatches);
  const selected = useStageStore((s) => s.selectedRoleIds);
  const toggle = useStageStore((s) => s.toggleSelectedRole);
  const ranked = useMemo(() => roleMatchesToViews(roleMatches), [roleMatches]);

  const canProceed = selected.length > 0;

  return (
    <div className="relative flex w-full flex-col px-6 pb-8 pt-[max(6rem,calc(env(safe-area-inset-top)+5rem))] sm:px-10 lg:px-16 lg:pt-24">
      <div className="mx-auto flex w-full max-w-[1280px] flex-1 flex-col gap-4 lg:min-h-0">
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
          className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between"
        >
          <h2 className="h-stage">Pick up to 3 roles to explore further.</h2>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setStage("recap")}
              className="liquid-glass inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[12.5px] text-foreground/75 transition hover:text-foreground"
            >
              <ArrowLeft size={12} /> back
            </button>
            <motion.button
              whileHover={canProceed ? { y: -1 } : undefined}
              whileTap={canProceed ? { scale: 0.98 } : undefined}
              disabled={!canProceed}
              onClick={() => canProceed && setStage("focus")}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-medium text-white transition",
                !canProceed && "cursor-not-allowed opacity-40",
              )}
              style={{
                background: "var(--gradient-warm)",
                boxShadow: canProceed
                  ? "0 10px 24px -12px color-mix(in oklab, var(--brand-deep) 60%, transparent)"
                  : undefined,
              }}
            >
              See {selected.length || ""} path{selected.length === 1 ? "" : "s"}
              <ArrowRight size={13} />
            </motion.button>
          </div>
        </motion.div>

        {ranked.length === 0 ? (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-[14px] text-foreground/60">
              No matching roles were returned. Go back and adjust your profile.
            </p>
          </div>
        ) : (
          <div className="grid flex-1 grid-cols-1 gap-3 sm:grid-cols-2 lg:min-h-0 lg:grid-cols-3 lg:grid-rows-3">
            {ranked.map((role, i) => (
              <RoleCard
                key={role.id}
                role={role}
                index={i}
                selected={selected.includes(role.id)}
                onToggle={() => toggle(role.id)}
                picksFull={selected.length >= MAX_PICKS && !selected.includes(role.id)}
              />
            ))}
          </div>
        )}

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center gap-1.5 text-[12px] text-foreground/60"
        >
          {Array.from({ length: MAX_PICKS }).map((_, i) => (
            <span
              key={i}
              className={cn(
                "h-1.5 w-7 rounded-full transition-all",
                i < selected.length ? "bg-[color:var(--brand)]" : "bg-foreground/15",
              )}
            />
          ))}
          <span className="ml-2">
            {selected.length}/{MAX_PICKS} selected
          </span>
        </motion.div>
      </div>
    </div>
  );
}

function RoleCard({
  role,
  index,
  selected,
  onToggle,
  picksFull,
}: {
  role: RoleView;
  index: number;
  selected: boolean;
  onToggle: () => void;
  picksFull: boolean;
}) {
  const topSkills = role.matchedSkills.slice(0, 3);
  const tone = bucketTone(role.bucket);

  return (
    <motion.button
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: [0.22, 1, 0.36, 1] }}
      whileHover={!picksFull ? { y: -3 } : undefined}
      whileTap={!picksFull ? { scale: 0.99 } : undefined}
      onClick={onToggle}
      disabled={picksFull}
      className={cn(
        "liquid-glass group relative flex min-h-[172px] flex-col gap-2 overflow-hidden rounded-3xl p-4 text-left transition-shadow duration-300",
        selected &&
          "ring-2 ring-[color:var(--brand)]/45 shadow-[0_18px_50px_-22px_color-mix(in_oklab,var(--brand-deep)_55%,transparent)]",
        picksFull && "cursor-not-allowed opacity-50",
      )}
      style={
        selected
          ? {
              background:
                "linear-gradient(155deg, color-mix(in oklab, var(--brand) 9%, white) 0%, white 55%, color-mix(in oklab, var(--brand) 4%, white) 100%)",
            }
          : undefined
      }
    >
      <motion.span
        aria-hidden
        animate={{ opacity: selected ? 1 : 0, scale: selected ? 1 : 0.6 }}
        transition={{ type: "spring", stiffness: 240, damping: 24 }}
        className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full blur-2xl"
        style={{ background: "var(--gradient-warm)", opacity: 0.18 }}
      />

      <motion.span
        aria-hidden
        animate={{ opacity: selected ? 1 : 0, scale: selected ? 1 : 0.7, y: selected ? 0 : -4 }}
        transition={{ type: "spring", stiffness: 360, damping: 26 }}
        className="absolute right-4 top-4 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-white"
        style={{ background: "var(--gradient-warm)" }}
      >
        Selected
      </motion.span>

      <span
        className="inline-flex w-fit items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.16em]"
        style={{ backgroundColor: tone.background, color: tone.text }}
      >
        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: tone.dot }} />
        {role.bucketLabel}
      </span>

      <div className="flex items-start justify-between gap-3">
        <h3
          className="font-display tracking-tight text-balance"
          style={{ fontSize: "clamp(1.08rem, 1.45vw, 1.25rem)", lineHeight: 1.15 }}
        >
          {role.title}
        </h3>
        <span
          className="shrink-0 font-display leading-none tracking-tight"
          style={{
            fontSize: "clamp(1.55rem, 2.1vw, 2rem)",
            background: "var(--gradient-warm)",
            WebkitBackgroundClip: "text",
            backgroundClip: "text",
            color: "transparent",
          }}
        >
          {Math.round(role.fit * 100)}%
        </span>
      </div>

      {(role.salary || role.escoTitle) && (
        <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11.5px] text-foreground/55">
          {role.salary && <span>{role.salary}</span>}
          {role.escoTitle && <span>ESCO: {role.escoTitle}</span>}
        </div>
      )}

      {role.summary && (
        <p className="line-clamp-2 text-[12.5px] leading-snug text-foreground/65">{role.summary}</p>
      )}

      {topSkills.length > 0 && (
        <div className="mt-auto flex flex-wrap gap-1.5 pt-2">
          {topSkills.map((skill) => (
            <span
              key={skill}
              className="line-clamp-1 max-w-full rounded-full bg-foreground/[0.05] px-2 py-0.5 text-[11px] text-foreground/70"
            >
              {skill}
            </span>
          ))}
        </div>
      )}
    </motion.button>
  );
}

function bucketTone(bucket: string) {
  switch (bucket) {
    case "ready_now":
      return { background: "#e7f6ee", text: "#17633f", dot: "#20a162" };
    case "next_step":
      return { background: "#e8f0fb", text: "#225a9d", dot: "#2f79d1" };
    case "aspirational":
      return { background: "#fff1d6", text: "#875400", dot: "#d99000" };
    default:
      return {
        background: "color-mix(in oklab, var(--brand) 10%, white)",
        text: "var(--brand-deep)",
        dot: "var(--brand)",
      };
  }
}
