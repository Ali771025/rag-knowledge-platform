import { motion, useReducedMotion } from "framer-motion";
import { dsLoading, dsMotionVariants } from "@/design-system";

interface LoadingDotsProps {
  label?: string;
}

export function LoadingDots({ label }: LoadingDotsProps) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <span className="inline-flex items-center gap-1" role="status" aria-label={label ?? "Loading"}>
      {[0, 1, 2].map((index) => (
        <motion.span
          key={index}
          className="rounded-full bg-muted-foreground"
          style={{ width: dsLoading.dotSizeMd, height: dsLoading.dotSizeMd }}
          variants={dsMotionVariants.loadingPulse}
          initial="idle"
          animate={shouldReduceMotion ? "idle" : "active"}
          transition={shouldReduceMotion ? { duration: 0 } : { delay: index * 0.12 }}
          aria-hidden="true"
        />
      ))}
    </span>
  );
}
