import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { useStageStore } from "@/state/useStageStore";
import { AmbientBackdrop } from "./AmbientBackdrop";
import { TopBar } from "./TopBar";
import { EntryStage } from "./stages/EntryStage";
import { RecapStage } from "./stages/RecapStage";
import { MatchingStage } from "./stages/MatchingStage";
import { DirectionsStage } from "./stages/DirectionsStage";
import { PreparingPathsStage } from "./stages/PreparingPathsStage";
import { FocusStage } from "./stages/FocusStage";

export function CareerCompassApp() {
  const stage = useStageStore((s) => s.stage);
  const loadDemo = useStageStore((s) => s.loadDemo);

  useEffect(() => {
    const demo = new URLSearchParams(window.location.search).get("demo");
    if (demo === "1") {
      loadDemo("roles");
      return;
    }
    if (demo === "recap" || demo === "roles" || demo === "focus") {
      loadDemo(demo);
    }
  }, [loadDemo]);

  return (
    <div
      className="relative w-full overflow-x-hidden"
      style={{
        minHeight: "100dvh",
        paddingTop: "env(safe-area-inset-top)",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      <AmbientBackdrop />
      <TopBar />
      <AnimatePresence mode="wait">
        <motion.div
          key={stage}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="relative w-full"
        >
          {stage === "entry" && <EntryStage />}
          {stage === "recap" && <RecapStage />}
          {stage === "matching" && <MatchingStage />}
          {stage === "directions" && <DirectionsStage />}
          {stage === "preparing_paths" && <PreparingPathsStage />}
          {stage === "focus" && <FocusStage />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
