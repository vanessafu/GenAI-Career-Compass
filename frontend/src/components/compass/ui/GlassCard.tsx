import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";

type Props = HTMLMotionProps<"div"> & { strong?: boolean };

/** Soft editorial card — hairline border + paper highlight. */
export const GlassCard = forwardRef<HTMLDivElement, Props>(function GlassCard(
  { className, strong, children, ...rest },
  ref,
) {
  return (
    <motion.div
      ref={ref}
      className={cn("relative rounded-3xl", strong ? "soft-card-elevated" : "soft-card", className)}
      {...rest}
    >
      {children}
    </motion.div>
  );
});
