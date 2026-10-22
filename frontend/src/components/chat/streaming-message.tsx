import { motion } from "framer-motion";
import { LoadingDots } from "@/components/ui";
import { dsMotionVariants } from "@/design-system";

interface StreamingMessageProps {
  hasContent: boolean;
}

export function StreamingMessage({ hasContent }: StreamingMessageProps) {
  return (
    <motion.div
      className={`mt-2 inline-flex items-center gap-2 text-xs text-slate-400 ${hasContent ? "" : "min-h-6"}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
      variants={dsMotionVariants.streamingReveal}
      initial="hidden"
      animate="visible"
    >
      <LoadingDots label="Streaming response" />
      <span>{hasContent ? "Streaming..." : "Thinking..."}</span>
    </motion.div>
  );
}
