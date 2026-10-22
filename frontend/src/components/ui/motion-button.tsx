import { motion } from "framer-motion";
import type { HTMLMotionProps } from "framer-motion";
import { dsMotionVariants } from "@/design-system";

interface MotionButtonProps extends HTMLMotionProps<"button"> {
  className?: string;
}

export function MotionButton({ children, className = "", type = "button", ...props }: MotionButtonProps) {
  return (
    <motion.button
      type={type}
      className={className}
      variants={dsMotionVariants.card}
      whileHover="hover"
      whileTap="tap"
      {...props}
    >
      {children}
    </motion.button>
  );
}
