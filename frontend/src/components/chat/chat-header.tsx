interface ChatHeaderProps {
  title: string;
  subtitle: string;
  status?: "ready" | "thinking" | "streaming" | "sending" | "error";
}

function getStatusMeta(status: NonNullable<ChatHeaderProps["status"]>) {
  if (status === "sending") return { label: "Sending", className: "bg-amber-500/15 text-amber-300 border-amber-400/25" };
  if (status === "thinking") return { label: "Thinking", className: "bg-sky-500/15 text-sky-300 border-sky-400/25" };
  if (status === "streaming") return { label: "Streaming", className: "bg-cyan-500/15 text-cyan-300 border-cyan-400/25" };
  if (status === "error") return { label: "Error", className: "bg-rose-500/15 text-rose-300 border-rose-400/25" };
  return { label: "Ready", className: "bg-emerald-500/15 text-emerald-300 border-emerald-400/25" };
}

export function ChatHeader({ title, subtitle, status = "ready" }: ChatHeaderProps) {
  const statusMeta = getStatusMeta(status);

  return (
    <header className="border-b border-transparent bg-slate-950/55 px-4 py-3 backdrop-blur sm:px-6">
      <div className="mx-auto flex w-full max-w-3xl items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-base font-semibold text-foreground sm:text-lg">{title}</h1>
          <p className="mt-1 text-xs text-muted-foreground sm:text-sm">{subtitle}</p>
        </div>
        <span
          className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-[11px] font-medium ${statusMeta.className}`}
          aria-live="polite"
        >
          {statusMeta.label}
        </span>
      </div>
    </header>
  );
}
