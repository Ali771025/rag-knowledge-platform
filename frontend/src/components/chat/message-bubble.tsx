import { memo } from "react";
import { BookOpen, Bot, Sparkles, UserRound } from "lucide-react";
import type { AgentMessage } from "@/types";
import { getMessageVisualVariant } from "@/features/chat";
import { StructuredMessageContent } from "./message-content/structured-message-content";

interface MessageBubbleProps {
  message: AgentMessage;
}

const BUBBLE_CLASS_BY_VARIANT = {
  agent:
    "border border-sky-400/20 bg-slate-900/65 text-slate-100 before:absolute before:inset-y-3 before:start-0 before:w-1 before:rounded-full before:bg-gradient-to-b before:from-cyan-300 before:to-blue-500",
  user: "border border-indigo-400/25 bg-slate-900/70 text-slate-100 shadow-[0_0_0_1px_rgba(34,211,238,0.2)]",
  system: "border border-slate-700/80 bg-slate-900 text-slate-100"
} as const;

function formatMessageTime(createdAt: string): string {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

function getSourceCount(message: AgentMessage): number | null {
  const maybeSources = message.metadata?.sources;
  if (!Array.isArray(maybeSources)) return null;
  return maybeSources.length;
}

export const MessageBubble = memo(function MessageBubble({ message }: MessageBubbleProps) {
  const variant = getMessageVisualVariant(message.role);
  const isUser = variant === "user";
  const sourceCount = getSourceCount(message);
  const timeLabel = formatMessageTime(message.createdAt);

  return (
    <div
      dir="auto"
      className={`relative max-w-[min(85ch,100%)] rounded-3xl px-4 py-3 text-left shadow-sm ${
        BUBBLE_CLASS_BY_VARIANT[variant]
      }`}
      data-role={message.role}
    >
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/15 bg-white/5 text-cyan-200">
          {isUser ? <UserRound className="h-4 w-4" aria-hidden="true" /> : <Bot className="h-4 w-4" aria-hidden="true" />}
        </span>
        <span className="flex items-center gap-2 text-[11px] text-slate-400">
          {timeLabel ? (
            <span className="inline-flex items-center gap-1">
              <Sparkles className="h-3 w-3" aria-hidden="true" />
              {timeLabel}
            </span>
          ) : null}
          {sourceCount !== null ? (
            <span className="inline-flex items-center gap-1">
              <BookOpen className="h-3 w-3" aria-hidden="true" />
              {sourceCount}
            </span>
          ) : null}
        </span>
      </div>
      <StructuredMessageContent message={message} />
    </div>
  );
});
