import { LoadingDots } from "@/components/ui";

interface ThinkingIndicatorProps {
  visible: boolean;
}

export function ThinkingIndicator({ visible }: ThinkingIndicatorProps) {
  if (!visible) {
    return null;
  }

  return (
    <div className="mx-auto flex w-full max-w-4xl items-start gap-3 px-1" role="status" aria-live="polite" aria-atomic="true">
      <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-cyan-400/25 bg-cyan-500/15 text-cyan-200">
        <LoadingDots label="Assistant is thinking" />
      </span>
      <div className="rounded-3xl border border-slate-700/70 bg-slate-900/65 px-4 py-3 text-xs text-slate-300">
        Assistant is thinking...
      </div>
    </div>
  );
}
