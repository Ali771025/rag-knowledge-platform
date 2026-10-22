import type { RefObject } from "react";
import { ConversationDialogShell } from "./conversation-dialog-shell";

interface DeleteConversationDialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  onConfirm: () => void;
  restoreFocusRef?: RefObject<HTMLElement>;
}

export function DeleteConversationDialog({ open, title, onClose, onConfirm, restoreFocusRef }: DeleteConversationDialogProps) {
  if (!open) return null;

  return (
    <ConversationDialogShell
      title="Delete conversation"
      description={`Delete "${title}" permanently? This action cannot be undone.`}
      onClose={onClose}
      restoreFocusRef={restoreFocusRef}
    >
      <div className="space-y-4">
        <p className="text-sm text-slate-300">Your messages in this conversation will be removed from the workspace list.</p>
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 rounded-lg border border-slate-700 px-3 text-sm text-slate-300 hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="min-h-10 rounded-lg bg-rose-500 px-3 text-sm font-medium text-white hover:bg-rose-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/70"
          >
            Delete
          </button>
        </div>
      </div>
    </ConversationDialogShell>
  );
}
