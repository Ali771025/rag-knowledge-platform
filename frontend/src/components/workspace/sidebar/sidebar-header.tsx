import { Bot, PanelLeftClose, PanelLeftOpen, X } from "lucide-react";

interface SidebarHeaderProps {
  compact: boolean;
  showClose: boolean;
  onToggleCompact?: () => void;
  onClose?: () => void;
}

export function SidebarHeader({ compact, showClose, onToggleCompact, onClose }: SidebarHeaderProps) {
  return (
    <div className="flex h-14 items-center justify-between border-b border-border/70 px-3">
      <div className="flex items-center gap-2">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-md bg-slate-700" aria-hidden="true">
          <Bot className="h-4 w-4 text-slate-100" />
        </span>
        {!compact ? <span className="text-sm font-semibold text-slate-100">RAGAi Workspace</span> : null}
      </div>

      <div className="flex items-center gap-2">
        {onToggleCompact ? (
          <button
            type="button"
            onClick={onToggleCompact}
            className="inline-flex min-h-9 items-center justify-center rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            aria-label={compact ? "Expand sidebar" : "Collapse sidebar"}
          >
            {compact ? <PanelLeftOpen className="h-4 w-4" aria-hidden="true" /> : <PanelLeftClose className="h-4 w-4" aria-hidden="true" />}
          </button>
        ) : null}
        {showClose ? (
          <button
            type="button"
            onClick={onClose}
            className="inline-flex min-h-9 items-center justify-center rounded-md px-2 py-1 text-xs text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            aria-label="Close sidebar"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        ) : null}
      </div>
    </div>
  );
}
