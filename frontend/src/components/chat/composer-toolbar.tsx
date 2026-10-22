import { Paperclip, X } from "lucide-react";
import { ComposerActionButton } from "./composer-action-button";

interface ComposerToolbarProps {
  currentLength: number;
  maxLength: number;
  disabled: boolean;
  canClear: boolean;
  onClear: () => void;
  attachmentsCount: number;
  canAttach: boolean;
  onAttach: () => void;
  onClearAttachments: () => void;
}

export function ComposerToolbar({
  currentLength,
  maxLength,
  disabled,
  canClear,
  onClear,
  attachmentsCount,
  canAttach,
  onAttach,
  onClearAttachments,
}: ComposerToolbarProps) {
  return (
    <div className="mt-2 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2">
        <ComposerActionButton
          label={attachmentsCount > 0 ? `Files (${attachmentsCount})` : "Attach"}
          onClick={onAttach}
          disabled={!canAttach}
          icon={<Paperclip className="h-3.5 w-3.5" aria-hidden="true" />}
        />
        {attachmentsCount > 0 ? (
          <ComposerActionButton
            label="Clear files"
            onClick={onClearAttachments}
            disabled={disabled}
            icon={<X className="h-3.5 w-3.5" aria-hidden="true" />}
          />
        ) : null}
        <ComposerActionButton
          label="Clear"
          onClick={onClear}
          disabled={disabled || !canClear}
          icon={<X className="h-3.5 w-3.5" aria-hidden="true" />}
        />
      </div>
      <div className="flex items-center gap-3">
        <p className="text-[11px] text-slate-400">{currentLength}/{maxLength}</p>
        <p className="text-[11px] text-slate-500">Enter to send, Shift+Enter for newline</p>
      </div>
    </div>
  );
}
