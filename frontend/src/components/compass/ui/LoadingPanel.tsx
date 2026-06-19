import { motion } from "framer-motion";
import { Check } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * Shared loading panel used by EntryStage (parsing CV) and MatchingStage
 * (finding roles). Consistent position, sizing, and motion so transitions
 * across screens feel like one continuous moment.
 */
export function LoadingPanel({
  icon: Icon,
  title,
  doneTitle,
  step,
  steps,
  done,
}: {
  icon: LucideIcon;
  title: string;
  doneTitle: string;
  step: number;
  steps: string[];
  done: boolean;
}) {
  const pct = done ? 100 : Math.min(95, ((step + 1) / steps.length) * 95);
  return (
    <motion.div
      layoutId="loading-panel"
      initial={{ opacity: 0, y: 14, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -6, scale: 0.98 }}
      transition={{ type: "spring", stiffness: 220, damping: 28, mass: 0.7 }}
      className="liquid-glass mx-auto flex w-full max-w-xl items-center gap-4 rounded-3xl p-6"
      style={{ willChange: "transform, opacity" }}
    >
      <motion.div
        animate={{ rotate: done ? 0 : [0, 6, -4, 0] }}
        transition={{ duration: 2.2, repeat: done ? 0 : Infinity, ease: "easeInOut" }}
        className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl text-white"
        style={{ background: "var(--gradient-warm)" }}
      >
        {done ? <Check size={20} /> : <Icon size={20} />}
      </motion.div>
      <div className="min-w-0 flex-1">
        <p className="text-[15px] font-medium">{done ? doneTitle : title}</p>
        <motion.p
          key={done ? "done" : steps[step]}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="mt-0.5 text-[13px] text-foreground/60"
        >
          {done ? "Ready" : steps[step]}
        </motion.p>
        <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-foreground/[0.08]">
          <motion.div
            initial={{ width: "5%" }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
            className="h-full rounded-full"
            style={{ background: "var(--gradient-warm)" }}
          />
        </div>
      </div>
    </motion.div>
  );
}
