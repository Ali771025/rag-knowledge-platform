import { motion } from "framer-motion";
import { LoadingDots } from "@/components/ui";
import { dsMotionVariants } from "@/design-system";

interface TypingIndicatorProps {
  isTyping?: boolean;
  isStreaming?: boolean;
}

export function TypingIndicator({ isTyping = false, isStreaming = false }: TypingIndicatorProps) {
  if (!isTyping && !isStreaming) {
    return null;
  }

  const label = isStreaming ? "Agent is responding..." : "Agent is typing...";

  return (
    <motion.div
      className="flex items-center gap-2 px-1 text-xs text-muted-foreground"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      variants={dsMotionVariants.typingIndicator}
      initial="idle"
      animate="active"
    >
      <LoadingDots label={label} />
      <span>{label}</span>
    </motion.div>
  );
}
