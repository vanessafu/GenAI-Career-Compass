import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";

export function AnimatedPercent({
  value,
  className,
  duration = 0.85,
  delay = 0,
}: {
  value: number;
  className?: string;
  duration?: number;
  delay?: number;
}) {
  const reduceMotion = useReducedMotion();
  const target = Math.max(0, Math.min(100, Math.round(value)));
  const [current, setCurrent] = useState(reduceMotion ? target : 0);

  useEffect(() => {
    if (reduceMotion) {
      setCurrent(target);
      return;
    }

    setCurrent(0);
    const controls = animate(0, target, {
      duration,
      delay,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (latest) => setCurrent(Math.round(latest)),
    });

    return () => controls.stop();
  }, [delay, duration, reduceMotion, target]);

  return <span className={className}>{current}%</span>;
}
