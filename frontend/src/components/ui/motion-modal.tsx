import type { PropsWithChildren } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionModalProps extends PropsWithChildren {
  open: boolean;
  className?: string;
  backdropClassName?: string;
}

export function MotionModal({ open, children, className = "", backdropClassName = "" }: MotionModalProps) {
  return (
    <AnimatePresence>
      {open ? (
        <motion.div className={backdropClassName} variants={dsMotionVariants.modalBackdrop} initial="hidden" animate="visible" exit="exit">
          <motion.div className={className} variants={dsMotionVariants.modalCard}>
            {children}
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
