import type { ElementType, PropsWithChildren } from "react";
import { motion } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionListItemProps extends PropsWithChildren {
  as?: "div" | "li";
  className?: string;
}

const motionElements: Record<NonNullable<MotionListItemProps["as"]>, ElementType> = {
  div: motion.div,
  li: motion.li
};

export function MotionListItem({ as = "div", children, className = "" }: MotionListItemProps) {
  const Component = motionElements[as];
  return (
    <Component className={className} variants={dsMotionVariants.listItem}>
      {children}
    </Component>
  );
}
