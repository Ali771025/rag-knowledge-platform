import type { ReactNode } from "react";

interface ComposerActionButtonProps {
  label: string;
  onClick: () => void;
  disabled?: boolean;
  icon?: ReactNode;
}

export function ComposerActionButton({ label, onClick, disabled = false, icon }: ComposerActionButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-700/80 bg-slate-900/70 px-2.5 text-xs text-slate-300 transition hover:border-slate-600 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/60 disabled:cursor-not-allowed disabled:opacity-45"
      aria-label={label}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}
