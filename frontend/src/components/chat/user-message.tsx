import type { AgentMessage } from "@/types";
import { MessageActions } from "./message-actions";
import { MessageAvatar } from "./message-avatar";
import { MessageContent } from "./message-content";

interface UserMessageProps {
  message: AgentMessage;
}

export function UserMessage({ message }: UserMessageProps) {
  return (
    <article className="group flex w-full justify-end">
      <div className="flex w-full max-w-[min(85ch,100%)] justify-end gap-3">
        <div className="min-w-0 text-right">
          <div className="rounded-3xl border border-slate-600/70 bg-slate-800/85 px-4 py-3 text-left shadow-[0_6px_18px_rgba(2,6,23,0.22)]">
            <MessageContent message={message} />
          </div>
          <div className="flex justify-end">
            <MessageActions message={message} />
          </div>
        </div>
        <MessageAvatar role="user" />
      </div>
    </article>
  );
}
