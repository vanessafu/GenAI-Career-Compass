import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";
import { forwardRef } from "react";

type Variant = "primary" | "ghost";
type Size = "sm" | "md" | "lg";

type Props = Omit<HTMLMotionProps<"button">, "children"> & {
  variant?: Variant;
  size?: Size;
  shimmer?: boolean;
  children?: React.ReactNode;
};

const sizeMap: Record<Size, string> = {
  sm: "h-9 px-4 text-sm min-w-[44px]",
  md: "h-11 px-6 text-sm min-w-[44px]",
  lg: "h-12 px-7 text-base min-w-[44px]",
};

export const PillButton = forwardRef<HTMLButtonElement, Props>(function PillButton(
  { className, variant = "primary", size = "md", shimmer, children, disabled, ...rest },
  ref,
) {
  const base =
    "relative pill inline-flex items-center justify-center gap-2 font-medium tracking-tight overflow-hidden select-none transition";
  const styles =
    variant === "primary"
      ? "text-[color:var(--primary-foreground)] shadow-[0_1px_0_rgba(255,255,255,0.4)_inset,0_-2px_4px_rgba(0,0,0,0.06)_inset,0_14px_30px_-14px_color-mix(in_oklab,var(--sage)_55%,transparent)] hover:brightness-[1.04]"
      : "soft-card text-foreground hover:bg-foreground/[0.04]";
  return (
    <motion.button
      ref={ref}
      whileHover={disabled ? undefined : { y: -1 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={{ type: "spring", stiffness: 400, damping: 24 }}
      style={variant === "primary" ? { background: "var(--gradient-accent)" } : undefined}
      className={cn(
        base,
        styles,
        sizeMap[size],
        disabled && "opacity-60 cursor-not-allowed",
        className,
      )}
      disabled={disabled}
      {...rest}
    >
      <span className="relative z-10 inline-flex items-center gap-2">{children}</span>
      {shimmer && (
        <motion.span
          aria-hidden
          initial={{ x: "-120%" }}
          animate={{ x: "120%" }}
          transition={{ duration: 0.9, ease: "easeInOut" }}
          className="absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/55 to-transparent"
        />
      )}
    </motion.button>
  );
});
