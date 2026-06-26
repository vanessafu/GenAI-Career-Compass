import { motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { Compass } from "lucide-react";
import { useStageStore } from "@/state/useStageStore";
import { MATCHING_PROGRESS, getLoadingProgressState } from "@/lib/loadingProgress";
import { LoadingPanel } from "../ui/LoadingPanel";

const STEPS = [
  "Scanning ESCO occupations",
  "Calibrating fit against your profile",
  "Aligning your compass",
];

export function MatchingStage() {
  const setStage = useStageStore((s) => s.setStage);
  const runMatching = useStageStore((s) => s.runMatching);
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(8);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stepTimersRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let active = true;
    const timers = stepTimersRef.current;
    const startedAt = Date.now();
    const tickProgress = () => {
      const state = getLoadingProgressState(MATCHING_PROGRESS, Date.now() - startedAt);
      setStep(state.step);
      setProgress(state.progress);
    };

    tickProgress();
    progressTimerRef.current = setInterval(tickProgress, 250);

    runMatching().then((ok) => {
      if (!active) return;
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      if (ok) {
        setProgress(100);
        setDone(true);
        timers.push(setTimeout(() => setStage("directions"), 600));
      } else {
        setError(useStageStore.getState().error);
      }
    });

    return () => {
      active = false;
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      timers.forEach(clearTimeout);
    };
  }, [runMatching, setStage]);

  if (error) {
    return (
      <div className="relative flex w-full flex-col items-center justify-center px-6 pb-10 pt-[max(6rem,calc(env(safe-area-inset-top)+5rem))] sm:px-10 lg:px-16 lg:pt-24">
        <div className="liquid-glass mx-auto flex w-full max-w-xl flex-col items-start gap-3 rounded-3xl p-6">
          <h2 className="font-display text-[22px] tracking-tight">Matching is unavailable</h2>
          <p className="text-[14px] leading-relaxed text-foreground/65">{error}</p>
          <button
            onClick={() => setStage("recap")}
            className="mt-1 inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-[13px] font-medium text-white"
            style={{ background: "var(--gradient-warm)" }}
          >
            Back to profile
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex w-full flex-col items-stretch px-6 pb-10 pt-[max(6rem,calc(env(safe-area-inset-top)+5rem))] sm:px-10 lg:px-16 lg:pt-24">
      <div className="mx-auto flex w-full max-w-[1180px] flex-col gap-7">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ type: "spring", stiffness: 260, damping: 28, mass: 0.6 }}
          className="flex flex-col items-center text-center"
        >
          <h1 className="h-hero">
            Finding the best{" "}
            <span
              className="italic"
              style={{
                background: "var(--gradient-warm)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              nine roles for you.
            </span>
          </h1>
        </motion.div>

        <LoadingPanel
          icon={Compass}
          title="Aligning your compass"
          doneTitle="Routes ready"
          step={step}
          steps={STEPS}
          done={done}
          progress={progress}
        />
      </div>
    </div>
  );
}
