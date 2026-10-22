import { useEffect, useRef, useState, type FormEvent, type RefObject } from "react";
import { ConversationDialogShell } from "./conversation-dialog-shell";

interface RenameProjectDialogProps {
  open: boolean;
  name: string;
  existingNames: string[];
  onClose: () => void;
  onConfirm: (nextName: string) => void;
  restoreFocusRef?: RefObject<HTMLElement>;
}

export function RenameProjectDialog({
  open,
  name,
  existingNames,
  onClose,
  onConfirm,
  restoreFocusRef,
}: RenameProjectDialogProps) {
  const [value, setValue] = useState(name);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setValue(name);
    setError(null);
  }, [name, open]);

  if (!open) return null;

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed) {
      setError("Project name cannot be empty.");
      return;
    }

    const isDuplicate = existingNames.some((item) => item.trim().toLowerCase() === trimmed.toLowerCase());
    if (isDuplicate && trimmed.toLowerCase() !== name.trim().toLowerCase()) {
      setError("A project with this name already exists.");
      return;
    }

    onConfirm(trimmed);
  };

  return (
    <ConversationDialogShell
      title="Rename project"
      description="Set a clear project name for easier organization."
      onClose={onClose}
      initialFocusRef={inputRef}
      restoreFocusRef={restoreFocusRef}
    >
      <form onSubmit={handleSubmit} className="space-y-3">
        <label htmlFor="rename-project-input" className="sr-only">
          Project name
        </label>
        <input
          id="rename-project-input"
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
