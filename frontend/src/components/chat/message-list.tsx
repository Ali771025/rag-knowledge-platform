import { memo, useMemo } from "react";
import type { AgentMessage } from "@/types";
import { MessageRow } from "./message-row";
import { ScrollAnchor } from "./scroll-anchor";

interface MessageListProps {
  messages: AgentMessage[];
  bottomAnchorRef?: React.RefObject<HTMLDivElement>;
}

export const MessageList = memo(function MessageList({ messages, bottomAnchorRef }: MessageListProps) {
  // Keep a stable rendered array reference so token-level updates only patch changed rows.
  const renderedMessages = useMemo(() => messages, [messages]);

  return (
    <ul
      className="flex w-full min-w-full flex-1 flex-col gap-4 px-2 pb-4 sm:px-3 lg:px-4"
      data-virtualization-ready="true"
      aria-label="Conversation messages"
      role="list"
    >
      {renderedMessages.map((message) => (
        <li key={message.id} className="w-full">
          <MessageRow message={message} />
        </li>
      ))}
      <li className="w-full">
        <ScrollAnchor ref={bottomAnchorRef} />
      </li>
    </ul>
  );
});
