import { NetworkError } from "@/components/ui";

interface ConversationIntelligenceFallbackProps {
  onRetry?: () => void;
}

export function ConversationIntelligenceFallback({ onRetry }: ConversationIntelligenceFallbackProps) {
  return (
    <section className="rounded-2xl border border-border bg-background p-3" aria-label="Conversation intelligence fallback">
      <NetworkError
        title="Workflow insights unavailable"
        message="Guidance widgets failed to load. Chat can continue while this panel recovers."
        retryLabel="Reload insights"
        onRetry={onRetry}
      />
    </section>
  );
}
