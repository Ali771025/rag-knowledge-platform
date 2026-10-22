import { NetworkError } from "@/components/ui";

interface ChatFallbackProps {
  onRetry?: () => void;
}

export function ChatFallback({ onRetry }: ChatFallbackProps) {
  return (
    <section className="rounded-2xl border border-border bg-background p-4" aria-label="Chat fallback">
      <NetworkError
        title="Chat area had an issue"
        message="The chat panel failed to render, but you can recover it without reloading the full app."
        retryLabel="Reload chat panel"
        onRetry={onRetry}
      />
    </section>
  );
}
