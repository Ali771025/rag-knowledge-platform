import type { ElementType, PropsWithChildren } from "react";
import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionListProps extends PropsWithChildren {
  as?: "div" | "ul" | "ol";
  className?: string;
}

const motionElements: Record<NonNullable<MotionListProps["as"]>, ElementType> = {
  div: motion.div,
  ul: motion.ul,
  ol: motion.ol
};

export function MotionList({ as = "div", children, className = "" }: MotionListProps) {
  const Component = motionElements[as];
  return (
    <Component className={className} variants={dsMotionVariants.cardList} initial="hidden" animate="visible" exit="exit">
      {children}
    </Component>
  );
}
