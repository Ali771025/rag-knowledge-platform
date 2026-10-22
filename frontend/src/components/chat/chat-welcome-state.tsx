import { QuickStartActions } from "./quick-start-actions";
import { SuggestedPromptGrid, type WelcomePrompt } from "./suggested-prompt-grid";

interface ChatWelcomeStateProps {
  prompts: WelcomePrompt[];
  disabled?: boolean;
  onSelectPrompt: (prompt: WelcomePrompt) => void;
}

function BrandMark() {
  return (
    <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/35 bg-cyan-500/15 text-cyan-200">
      <svg viewBox="0 0 24 24" fill="none" className="h-6 w-6" aria-hidden="true">
        <path d="M4 12h16M12 4v16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    </div>
  );
}

export function ChatWelcomeState({ prompts, disabled = false, onSelectPrompt }: ChatWelcomeStateProps) {
  return (
    <section className="mx-auto flex min-h-[60vh] w-full max-w-4xl items-center justify-center px-1 py-4">
      <div className="w-full space-y-6">
        <div className="space-y-3 text-center">
          <BrandMark />
          <h2 className="text-2xl font-semibold tracking-tight text-slate-100">Start a conversation</h2>
          <p className="mx-auto max-w-2xl text-sm leading-7 text-slate-400">
            Ask for onboarding help, summarize user context, or draft your next response. Pick a prompt below or type your own.
          </p>
          <QuickStartActions prompts={prompts} disabled={disabled} onSelectPrompt={onSelectPrompt} />
        </div>

        <SuggestedPromptGrid prompts={prompts} disabled={disabled} onSelectPrompt={onSelectPrompt} />
      </div>
    </section>
  );
}
