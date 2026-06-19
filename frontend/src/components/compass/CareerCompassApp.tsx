import { AnimatePresence, motion } from "framer-motion";
import { useStageStore } from "@/state/useStageStore";
import { AmbientBackdrop } from "./AmbientBackdrop";
import { TopBar } from "./TopBar";
import { EntryStage } from "./stages/EntryStage";
import { RecapStage } from "./stages/RecapStage";
import { MatchingStage } from "./stages/MatchingStage";
import { DirectionsStage } from "./stages/DirectionsStage";
import { FocusStage } from "./stages/FocusStage";

export function CareerCompassApp() {
  const stage = useStageStore((s) => s.stage);

  return (
    <div
      className="relative w-full overflow-x-hidden lg:h-screen lg:overflow-hidden"
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
          className="relative w-full lg:absolute lg:inset-0 lg:overflow-hidden"
        >
          {stage === "entry" && <EntryStage />}
          {stage === "recap" && <RecapStage />}
          {stage === "matching" && <MatchingStage />}
          {stage === "directions" && <DirectionsStage />}
          {stage === "focus" && <FocusStage />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
