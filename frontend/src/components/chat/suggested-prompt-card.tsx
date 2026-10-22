interface SuggestedPromptCardProps {
  title: string;
  prompt: string;
  description?: string;
  disabled?: boolean;
  onSelect: (prompt: string) => void;
}

export function SuggestedPromptCard({
  title,
  prompt,
  description,
  disabled = false,
  onSelect
}: SuggestedPromptCardProps) {
  return (
    <button
      type="button"
      onClick={() => onSelect(prompt)}
      disabled={disabled}
      className="group flex min-h-28 w-full flex-col items-start rounded-2xl border border-slate-700/70 bg-slate-900/60 p-4 text-left transition hover:border-slate-600 hover:bg-slate-900/80 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55 disabled:cursor-not-allowed disabled:opacity-50"
      aria-label={`Use prompt: ${title}`}
    >
      <span className="text-sm font-semibold text-slate-100">{title}</span>
      {description ? <span className="mt-1.5 text-xs leading-5 text-slate-400">{description}</span> : null}
      <span className="mt-3 line-clamp-2 text-[13px] leading-6 text-slate-300 group-hover:text-slate-200">{prompt}</span>
    </button>
  );
}
