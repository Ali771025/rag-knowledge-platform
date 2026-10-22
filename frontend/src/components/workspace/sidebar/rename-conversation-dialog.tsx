import { useEffect, useRef, useState, type FormEvent, type RefObject } from "react";
import { ConversationDialogShell } from "./conversation-dialog-shell";

interface RenameConversationDialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  onConfirm: (nextTitle: string) => void;
  restoreFocusRef?: RefObject<HTMLElement>;
}

export function RenameConversationDialog({ open, title, onClose, onConfirm, restoreFocusRef }: RenameConversationDialogProps) {
  const [value, setValue] = useState(title);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setValue(title);
    setError(null);
  }, [open, title]);

  if (!open) return null;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Title cannot be empty.");
      return;
    }
    onConfirm(trimmed);
  };

  return (
    <ConversationDialogShell
      title="Rename conversation"
      description="Choose a concise title so this conversation is easy to find later."
      onClose={onClose}
      initialFocusRef={inputRef}
      restoreFocusRef={restoreFocusRef}
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <label htmlFor="rename-conversation-input" className="sr-only">
          Conversation title
        </label>
        <input
          id="rename-conversation-input"
          ref={inputRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          className="h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60"
        />
        {error ? <p className="text-xs text-rose-300">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 rounded-lg border border-slate-700 px-3 text-sm text-slate-300 hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
          >
            Cancel
          </button>
          <button
            type="submit"
            className="min-h-10 rounded-lg bg-cyan-500 px-3 text-sm font-medium text-slate-950 hover:bg-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70"
          >
            Save
          </button>
        </div>
      </form>
    </ConversationDialogShell>
  );
}
