import { useStageStore, type Stage } from "@/state/useStageStore";
import { CompassMark } from "./ui/CompassMark";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

const STAGES: { key: Stage; label: string }[] = [
  { key: "entry", label: "Input" },
  { key: "recap", label: "Analysis" },
  { key: "directions", label: "Jobs" },
  { key: "focus", label: "Paths" },
];

export function TopBar() {
  const stage = useStageStore((s) => s.stage);
  const setStage = useStageStore((s) => s.setStage);
  const reset = useStageStore((s) => s.reset);
  const hasCv = useStageStore((s) => s.cvData !== null);

  const visibleStage = stage === "preparing_paths" ? "focus" : stage;
  const currentIdx = STAGES.findIndex((s) => s.key === visibleStage);
  const currentLabel = STAGES[currentIdx]?.label ?? "";

  return (
    <div className="pointer-events-none fixed left-1/2 top-3 z-40 -translate-x-1/2 px-3 sm:top-4">
      <div className="soft-card-elevated pill pointer-events-auto flex items-center gap-2 px-2 py-1.5 pr-3 sm:gap-3">
        <button
          onClick={reset}
          className="group flex items-center gap-2 rounded-full px-2 py-1 transition hover:bg-foreground/[0.04]"
          aria-label="Career Compass home"
        >
          <CompassMark size={22} />
          <span className="font-display text-[13px] tracking-tight sm:text-sm">
            Career <span className="italic text-[color:var(--teal)]">Compass</span>
          </span>
        </button>

        <div className="mx-1 h-5 w-px bg-foreground/10" />
        {/* Mobile: show current stage chip only */}
        <div className="flex items-center gap-1.5 sm:hidden">
          <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--sage)]" />
          <span className="text-[11px] tracking-wide text-foreground/70">{currentLabel}</span>
        </div>
        {/* Desktop: full stage rail */}
        <nav className="hidden items-center gap-1 sm:flex">
          {STAGES.map((s, i) => {
            const reachable = i === 0 || hasCv;
            const active = s.key === visibleStage;
            const visited = i < currentIdx;
            return (
              <button
                key={s.key}
                disabled={!reachable}
                onClick={() => reachable && setStage(s.key)}
                className={cn(
                  "relative rounded-full px-3 py-1.5 text-xs tracking-wide transition",
                  active ? "text-foreground" : "text-foreground/55 hover:text-foreground/85",
                  !reachable && "cursor-not-allowed opacity-40",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="topbar-pill"
                    className="absolute inset-0 rounded-full bg-foreground/[0.06] ring-1 ring-foreground/10"
                    transition={{ type: "spring", stiffness: 380, damping: 30 }}
                  />
                )}
                <span className="relative inline-flex items-center gap-1.5">
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      active
                        ? "bg-[color:var(--sage)]"
                        : visited
                          ? "bg-[color:var(--teal)]"
                          : "bg-foreground/20",
                    )}
                  />
                  {s.label}
                </span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
