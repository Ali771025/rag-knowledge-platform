import type { ConnectionStatusModel } from "@/core/websocket";

interface ConnectionStatusBannerProps {
  statusModel: ConnectionStatusModel;
  onReconnect?: () => void;
  onDismissRecovered?: () => void;
}

function getBannerCopy(statusModel: ConnectionStatusModel): { title: string; message: string; showRetry: boolean } | null {
  if (statusModel.banner === "none") {
    return null;
  }

  if (statusModel.banner === "reconnecting") {
    return {
      title: "Reconnecting",
      message: `Trying to recover live updates (${statusModel.reconnectAttempts}/${Math.max(1, statusModel.maxReconnectAttempts)}).`,
      showRetry: false
    };
  }

  if (statusModel.banner === "offline") {
    return {
      title: "Offline",
      message: "Live updates are disconnected. You can continue and retry when ready.",
      showRetry: true
    };
  }

  if (statusModel.banner === "temporarily_unavailable") {
    return {
      title: "Temporarily unavailable",
      message: "Realtime channel is unstable right now. Chat remains available with reduced live behavior.",
      showRetry: true
    };
  }

  return {
    title: "Recovered",
    message: "Live updates are back online.",
    showRetry: false
  };
}

export function ConnectionStatusBanner({ statusModel, onReconnect, onDismissRecovered }: ConnectionStatusBannerProps) {
  const copy = getBannerCopy(statusModel);
  if (!copy) {
    return null;
  }

  const toneClass =
    statusModel.banner === "recovered"
      ? "border-emerald-500/35 bg-emerald-500/10"
      : statusModel.banner === "reconnecting"
        ? "border-primary/35 bg-primary/10"
        : "border-warning/40 bg-warning/10";

  return (
    <section className={`w-full rounded-xl border p-3 text-foreground ${toneClass}`} role="status" aria-live="polite">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">{copy.title}</h3>
          <p className="mt-1 text-sm text-muted-foreground">{copy.message}</p>
        </div>
        {copy.showRetry && onReconnect ? (
          <button
            type="button"
            onClick={onReconnect}
            className="min-h-9 shrink-0 rounded-full border border-current/30 bg-background px-3 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Reconnect
          </button>
        ) : null}
      </div>

      {statusModel.banner === "recovered" && onDismissRecovered ? (
        <button
          type="button"
          onClick={onDismissRecovered}
          className="mt-2 min-h-8 rounded-full border border-current/30 bg-background px-3 text-xs font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          Dismiss
        </button>
      ) : null}
    </section>
  );
}
