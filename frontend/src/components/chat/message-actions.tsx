import { useMemo, useState } from "react";
import type { AgentMessage } from "@/types";
import { useAnalytics } from "@/hooks/use-analytics";
import { useToast } from "@/hooks/use-toast";
import { useActiveWorkspaceConversation } from "@/state";

interface MessageActionsProps {
  message: AgentMessage;
  onRetry?: (message: AgentMessage) => void;
  onEdit?: (message: AgentMessage) => void;
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-3.5 w-3.5" aria-hidden="true">
      <rect x="9" y="9" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.7" />
      <path d="M6 15H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v1" stroke="currentColor" strokeWidth="1.7" />
    </svg>
  );
}

function canUseClipboardApi(): boolean {
  return typeof navigator !== "undefined" && Boolean(navigator.clipboard?.writeText);
}

export function MessageActions({ message, onRetry, onEdit }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const { success, error } = useToast();
  const activeConversation = useActiveWorkspaceConversation();
  const { trackMessageCopied, trackMessageRegenerated, trackUserMessageEdited } = useAnalytics();

  const actionLabel = useMemo(() => (copied ? "Copied" : "Copy"), [copied]);

  const handleCopy = async () => {
    const text = message.text.trim();
    if (!text) return;

    try {
      if (canUseClipboardApi()) {
        await navigator.clipboard.writeText(text);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-9999px";
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand("copy");
        document.body.removeChild(textArea);
      }
      setCopied(true);
      trackMessageCopied(message.id, message.role, activeConversation?.id);
      success("Message copied");
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
      error("Copy failed", "Could not copy this message.");
    }
  };

  return (
    <div className="mt-2 flex items-center gap-1.5 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100">
      <button
        type="button"
        onClick={() => {
          void handleCopy();
        }}
        className="inline-flex h-7 items-center gap-1.5 rounded-md border border-slate-700/70 bg-slate-900/60 px-2 text-[11px] text-slate-300 hover:border-slate-600 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50"
        aria-label="Copy message"
      >
        <CopyIcon />
        {actionLabel}
      </button>

      {onRetry ? (
        <button
          type="button"
          onClick={() => {
            trackMessageRegenerated(message.id, activeConversation?.id);
            onRetry(message);
          }}
          className="inline-flex h-7 items-center rounded-md border border-slate-700/70 bg-slate-900/60 px-2 text-[11px] text-slate-300 hover:border-slate-600 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50"
          aria-label="Retry message"
        >
          Retry
        </button>
      ) : null}

      {onEdit && message.role === "user" ? (
        <button
          type="button"
          onClick={() => {
            trackUserMessageEdited(message.id, activeConversation?.id);
            onEdit(message);
          }}
          className="inline-flex h-7 items-center rounded-md border border-slate-700/70 bg-slate-900/60 px-2 text-[11px] text-slate-300 hover:border-slate-600 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/50"
          aria-label="Edit message"
        >
          Edit
        </button>
      ) : null}
    </div>
  );
}
