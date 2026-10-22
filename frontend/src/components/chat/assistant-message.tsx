import type { AgentMessage } from "@/types";
import { MessageActions } from "./message-actions";
import { MessageAvatar } from "./message-avatar";
import { MessageContent } from "./message-content";
import { StreamingMessage } from "./streaming-message";
import { StreamingCursor } from "./streaming-cursor";

interface AssistantMessageProps {
  message: AgentMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const hasContent = message.text.trim().length > 0;

  return (
    <article className="group flex w-full justify-start">
      <div className="flex w-full max-w-[min(92ch,100%)] items-start gap-3">
        <MessageAvatar role="agent" />
        <div className="min-w-0 flex-1">
          <div className="rounded-3xl border border-slate-700/70 bg-slate-900/65 px-4 py-3 shadow-[0_8px_22px_rgba(2,6,23,0.2)]">
            {hasContent ? <MessageContent message={message} /> : null}
            {message.isStreaming && hasContent ? <StreamingCursor /> : null}
            {message.isStreaming ? <StreamingMessage hasContent={hasContent} /> : null}
          </div>
          <MessageActions message={message} />
        </div>
      </div>
    </article>
  );
}
