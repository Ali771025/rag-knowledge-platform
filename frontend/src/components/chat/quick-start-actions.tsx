import type { WelcomePrompt } from "./suggested-prompt-grid";

interface QuickStartActionsProps {
  prompts: WelcomePrompt[];
  disabled?: boolean;
  onSelectPrompt: (prompt: WelcomePrompt) => void;
}

export function QuickStartActions({ prompts, disabled = false, onSelectPrompt }: QuickStartActionsProps) {
  const compactPrompts = prompts.slice(0, 3);

  if (compactPrompts.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {compactPrompts.map((prompt) => (
        <button
          key={prompt.id}
          type="button"
          onClick={() => onSelectPrompt(prompt)}
          disabled={disabled}
          className="rounded-full border border-slate-700/80 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300 transition hover:border-slate-600 hover:text-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400/55 disabled:cursor-not-allowed disabled:opacity-50"
          aria-label={`Quick start: ${prompt.title}`}
        >
          {prompt.title}
        </button>
      ))}
    </div>
  );
}
