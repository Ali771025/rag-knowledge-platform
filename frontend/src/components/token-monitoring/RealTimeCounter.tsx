import type { TokenUsageRealtimeEvent } from "@/types/tokenMonitoring";
import { formatDateTime, formatUsd } from "@/utils/tokenFormatters";

interface RealTimeCounterProps {
  latestEvent: TokenUsageRealtimeEvent | null;
  heartbeatAt: string | null;
  errorCount: number;
}

export function RealTimeCounter({ latestEvent, heartbeatAt, errorCount }: RealTimeCounterProps) {
  return (
    <section className="rounded-2xl border border-border bg-background p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">Realtime Feed</p>
      {latestEvent ? (
        <div className="mt-2 space-y-1 text-sm">
          <p className="font-medium">
            {latestEvent.provider} / {latestEvent.model_name}
          </p>
          <p className="text-muted-foreground">
            +{latestEvent.tokens_delta} tokens | {formatUsd(latestEvent.cost_delta)}
          </p>
          <p className="text-xs text-muted-foreground">Last usage event: {formatDateTime(latestEvent.timestamp)}</p>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">Waiting for live events...</p>
      )}
      <p className="mt-2 text-xs text-muted-foreground">Heartbeat: {formatDateTime(heartbeatAt)}</p>
      {errorCount > 0 ? <p className="mt-1 text-xs text-warning">Stream parse warnings: {errorCount}</p> : null}
    </section>
  );
}
