import { memo, useMemo } from "react";
import type { AgentMessage } from "@/types";
import { ChatMessage } from "./chat-message";
import { ScrollAnchor } from "./scroll-anchor";

interface ChatMessageListProps {
  messages: AgentMessage[];
  bottomAnchorRef?: React.RefObject<HTMLDivElement>;
  showSystemMessages?: boolean;
}

export const ChatMessageList = memo(function ChatMessageList({
  messages,
  bottomAnchorRef,
  showSystemMessages = false
}: ChatMessageListProps) {
  const renderedMessages = useMemo(() => messages, [messages]);

  return (
    <ul className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-1 pb-5" aria-label="Conversation messages" role="list">
      {renderedMessages.map((message) => (
        <li key={message.id}>
          <ChatMessage message={message} showSystemMessages={showSystemMessages} />
        </li>
      ))}
      <li>
        <ScrollAnchor ref={bottomAnchorRef} />
      </li>
    </ul>
  );
});
