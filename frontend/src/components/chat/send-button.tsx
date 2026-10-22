import { Loader2, SendHorizontal } from "lucide-react";

interface SendButtonProps {
  disabled: boolean;
  isSending: boolean;
  onClick: () => void;
}

export function SendButton({ disabled, isSending, onClick }: SendButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 transition hover:bg-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/70 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
      aria-label="Send message"
    >
      {isSending ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <SendHorizontal className="h-4 w-4" aria-hidden="true" />}
    </button>
  );
}
