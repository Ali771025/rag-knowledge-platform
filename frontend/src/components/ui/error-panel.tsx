import { Button } from "./button";

interface ErrorPanelProps {
  title: string;
  message: string;
  retryLabel?: string;
  onRetry?: () => void;
}

export function ErrorPanel({ title, message, retryLabel = "Retry", onRetry }: ErrorPanelProps) {
  return (
    <section className="w-full rounded-xl border border-error/35 bg-error/10 p-3 text-foreground" role="alert" aria-live="assertive">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      {onRetry ? (
        <div className="mt-3">
          <Button onClick={onRetry} variant="secondary" size="sm">
            {retryLabel}
          </Button>
        </div>
      ) : null}
    </section>
  );
}

