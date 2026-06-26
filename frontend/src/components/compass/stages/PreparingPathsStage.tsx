import { motion } from "framer-motion";
import { Compass } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { PATH_PREP_PROGRESS, getLoadingProgressState } from "@/lib/loadingProgress";
import { useStageStore } from "@/state/useStageStore";
import { LoadingPanel } from "../ui/LoadingPanel";

const STEPS = ["Building roadmap milestones", "Checking skill gaps", "Putting your plans together"];

export function PreparingPathsStage() {
  const selectedRoleIds = useStageStore((s) => s.selectedRoleIds);
  const setStage = useStageStore((s) => s.setStage);
  const loadCareerPath = useStageStore((s) => s.loadCareerPath);
  const loadRoleGapAnalysis = useStageStore((s) => s.loadRoleGapAnalysis);
  const [step, setStep] = useState(0);
  const [progress, setProgress] = useState(8);
  const [done, setDone] = useState(false);
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let active = true;
    const startedAt = Date.now();

    if (selectedRoleIds.length === 0) {
      setStage("directions");
      return () => {
        active = false;
      };
    }

    const tickProgress = () => {
      const state = getLoadingProgressState(PATH_PREP_PROGRESS, Date.now() - startedAt);
      setStep(state.step);
      setProgress(state.progress);
    };

    tickProgress();
    progressTimerRef.current = setInterval(tickProgress, 250);

    Promise.allSettled(
      selectedRoleIds.flatMap((roleId) => [loadCareerPath(roleId), loadRoleGapAnalysis(roleId)]),
    ).then(() => {
      if (!active) return;
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
      setProgress(100);
      setDone(true);
      window.setTimeout(() => {
        if (active) setStage("focus");
      }, 600);
    });

    return () => {
      active = false;
      if (progressTimerRef.current) {
        clearInterval(progressTimerRef.current);
        progressTimerRef.current = null;
      }
    };
  }, [loadCareerPath, loadRoleGapAnalysis, selectedRoleIds, setStage]);

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
            Preparing your{" "}
            <span
              className="italic"
              style={{
                background: "var(--gradient-warm)",
                WebkitBackgroundClip: "text",
                backgroundClip: "text",
                color: "transparent",
              }}
            >
              career plans.
            </span>
          </h1>
        </motion.div>

        <LoadingPanel
          icon={Compass}
          title="Preparing your career plans"
          doneTitle="Your plans are ready"
          step={step}
          steps={STEPS}
          done={done}
          progress={progress}
        />

        <button
          onClick={() => setStage("directions")}
          className="liquid-glass mx-auto inline-flex w-fit items-center rounded-full px-4 py-2 text-[13px] text-foreground/70 transition hover:text-foreground"
        >
          back to role selection
        </button>
      </div>
    </div>
  );
}
