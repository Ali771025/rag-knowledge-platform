import type { PropsWithChildren } from "react";
import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionPageProps extends PropsWithChildren {
  className?: string;
}

export function MotionPage({ children, className = "" }: MotionPageProps) {
  return (
    <motion.div className={className} variants={dsMotionVariants.pageEnter} initial="hidden" animate="visible" exit="exit">
      {children}
    </motion.div>
  );
}
