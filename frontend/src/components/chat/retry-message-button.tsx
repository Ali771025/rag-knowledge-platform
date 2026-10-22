interface RetryMessageButtonProps {
  disabled?: boolean;
  onRetry: () => void;
}

export function RetryMessageButton({ disabled = false, onRetry }: RetryMessageButtonProps) {
  return (
    <button
      type="button"
      onClick={onRetry}
      disabled={disabled}
      className="inline-flex h-8 items-center rounded-md border border-rose-400/45 bg-rose-500/10 px-2.5 text-xs text-rose-200 transition hover:bg-rose-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/55 disabled:cursor-not-allowed disabled:opacity-45"
      aria-label="Retry sending message"
    >
      Retry
    </button>
  );
}
