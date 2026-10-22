import type { PropsWithChildren } from "react";
import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionCardProps extends PropsWithChildren {
  className?: string;
  hover?: boolean;
  layout?: boolean | "position" | "size" | "preserve-aspect";
}

export function MotionCard({ children, className = "", hover = true, layout }: MotionCardProps) {
  return (
    <motion.div
      className={className}
      variants={dsMotionVariants.card}
      initial="hidden"
      animate="visible"
      exit="exit"
      whileHover={hover ? "hover" : undefined}
      whileTap={hover ? "tap" : undefined}
      layout={layout}
    >
      {children}
    </motion.div>
  );
}
