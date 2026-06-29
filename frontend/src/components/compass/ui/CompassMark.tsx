import { motion } from "framer-motion";

export function CompassMark({ size = 28 }: { size?: number }) {
  return (
    <span
      className="inline-flex shrink-0 rotate-[-45deg] transition-transform duration-300 ease-out group-hover:rotate-45 group-focus-visible:rotate-45 motion-reduce:transition-none"
      style={{ width: size, height: size, willChange: "transform" }}
      aria-hidden
    >
      <motion.svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        animate={{ rotate: 360 }}
        transition={{ duration: 80, repeat: Infinity, ease: "linear" }}
        style={{ willChange: "transform" }}
      >
        <defs>
          <radialGradient id="cm-bg" cx="50%" cy="40%" r="60%">
            <stop offset="0%" stopColor="oklch(0.97 0.02 200)" />
            <stop offset="100%" stopColor="oklch(0.78 0.10 200)" />
          </radialGradient>
        </defs>
        <circle
          cx="20"
          cy="20"
          r="18"
          fill="url(#cm-bg)"
          stroke="oklch(0.22 0.045 220 / 0.18)"
          strokeWidth="0.6"
        />
        <polygon points="20,5 23,20 20,35 17,20" fill="oklch(0.45 0.13 215)" opacity="0.95" />
        <polygon points="5,20 20,17 35,20 20,23" fill="oklch(0.28 0.06 220)" opacity="0.7" />
        <circle cx="20" cy="20" r="2" fill="white" />
      </motion.svg>
    </span>
  );
}
