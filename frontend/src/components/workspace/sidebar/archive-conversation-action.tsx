interface ArchiveConversationActionProps {
  archived: boolean;
  onArchive: () => void;
  onRestore: () => void;
}

export function ArchiveConversationAction({ archived, onArchive, onRestore }: ArchiveConversationActionProps) {
  return (
    <button
      type="button"
      role="menuitem"
      onClick={archived ? onRestore : onArchive}
      className="min-h-9 w-full rounded-md px-2 py-1.5 text-left text-xs text-slate-200 hover:bg-slate-800 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55"
    >
      {archived ? "Restore" : "Archive"}
    </button>
  );
}
