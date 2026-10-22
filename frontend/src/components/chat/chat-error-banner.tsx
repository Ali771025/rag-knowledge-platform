import { NetworkError } from "@/components/ui";

interface ChatErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function ChatErrorBanner({ message, onRetry, onDismiss }: ChatErrorBannerProps) {
  return (
    <div className="space-y-2">
      <NetworkError title="Chat is temporarily unavailable" message={message} retryLabel="Retry" onRetry={onRetry} />
      {onDismiss ? (
        <button
          type="button"
          onClick={onDismiss}
          className="min-h-9 rounded-full border border-border px-3 text-xs font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Dismiss
        </button>
      ) : null}
    </div>
  );
}
