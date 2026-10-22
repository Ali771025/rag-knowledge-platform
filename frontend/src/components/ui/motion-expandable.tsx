import type { PropsWithChildren } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionExpandableProps extends PropsWithChildren {
  open: boolean;
  className?: string;
}

export function MotionExpandable({ open, children, className = "" }: MotionExpandableProps) {
  return (
    <AnimatePresence initial={false}>
      {open ? (
        <motion.div className={className} variants={dsMotionVariants.expandable} initial="hidden" animate="visible" exit="exit">
          {children}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
