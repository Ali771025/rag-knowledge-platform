interface NetworkErrorProps {
  title?: string;
  message?: string;
  retryLabel?: string;
  onRetry?: () => void;
}

export function NetworkError({
  title = "Connection issue",
  message = "We could not reach the server. Please check your connection and try again.",
  retryLabel = "Try again",
  onRetry
}: NetworkErrorProps) {
  return (
    <section className="w-full rounded-xl border border-warning/40 bg-warning/10 p-3 text-foreground" role="status" aria-live="polite">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      {onRetry ? (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 min-h-10 rounded-full border border-warning/40 bg-background px-4 text-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {retryLabel}
        </button>
      ) : null}
    </section>
  );
}
