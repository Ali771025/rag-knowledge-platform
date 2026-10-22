import { memo } from "react";
import type { AgentMessage } from "@/types";
import { AssistantMessage } from "./assistant-message";
import { UserMessage } from "./user-message";

interface ChatMessageProps {
  message: AgentMessage;
  showSystemMessages?: boolean;
}

export const ChatMessage = memo(function ChatMessage({ message, showSystemMessages = false }: ChatMessageProps) {
  if (message.role === "system" && !showSystemMessages) {
    return null;
  }

  return (
    <article>
      {message.role === "user" ? <UserMessage message={message} /> : <AssistantMessage message={message} />}
    </article>
  );
});
