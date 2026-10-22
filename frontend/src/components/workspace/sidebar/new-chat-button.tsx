import { Plus } from "lucide-react";

interface NewChatButtonProps {
  compact: boolean;
  onClick: () => void;
}

export function NewChatButton({ compact, onClick }: NewChatButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-slate-700 bg-slate-900 px-3 text-sm font-medium text-slate-100 hover:bg-slate-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
      aria-label="Start a new chat"
    >
      <Plus className="h-4 w-4" aria-hidden="true" />
      {compact ? null : "New chat"}
    </button>
  );
}
