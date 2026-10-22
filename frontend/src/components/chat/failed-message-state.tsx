import { RetryMessageButton } from "./retry-message-button";

interface FailedMessageStateProps {
  message: string;
  canRetry: boolean;
  onRetry: () => void;
}

export function FailedMessageState({ message, canRetry, onRetry }: FailedMessageStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-3 rounded-2xl border border-rose-400/35 bg-rose-500/10 px-3 py-2 text-sm">
      <p className="text-rose-200">{message}</p>
      {canRetry ? <RetryMessageButton onRetry={onRetry} /> : null}
    </div>
  );
}
