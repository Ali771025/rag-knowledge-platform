import { memo } from "react";
import { motion, useReducedMotion } from "framer-motion";
import type { AgentMessage } from "@/types";
import { getMessageAlignment } from "@/features/chat";
import { dsMotionVariants } from "@/design-system";
import { MessageBubble } from "./message-bubble";

interface MessageRowProps {
  message: AgentMessage;
}

export const MessageRow = memo(function MessageRow({ message }: MessageRowProps) {
  const alignment = getMessageAlignment(message.role);
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.article
      className={`flex w-full ${alignment === "end" ? "justify-end" : "justify-start"}`}
      initial={shouldReduceMotion ? false : "hidden"}
      animate="visible"
      variants={dsMotionVariants.messageEntry}
      transition={shouldReduceMotion ? { duration: 0 } : undefined}
      layout="position"
    >
      <MessageBubble message={message} />
    </motion.article>
  );
});
