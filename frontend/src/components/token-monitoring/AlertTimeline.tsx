import type { ActiveBudgetAlertItem } from "@/types/tokenMonitoring";
import { formatDateTime, formatUsd } from "@/utils/tokenFormatters";

interface AlertTimelineProps {
  alerts: ActiveBudgetAlertItem[];
}

export function AlertTimeline({ alerts }: AlertTimelineProps) {
  if (alerts.length === 0) {
    return <p className="text-sm text-muted-foreground">No active alerts right now.</p>;
  }

  return (
    <ol className="space-y-3">
      {alerts.map((alert) => (
        <li key={alert.id} className="rounded-2xl border border-border bg-background p-4">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="text-sm font-medium">{alert.key_alias ?? alert.api_key_id}</p>
              <p className="text-xs text-muted-foreground">{alert.provider} | {alert.threshold_percent}% threshold crossed</p>
            </div>
            <div className="text-end">
              <p className="text-xs text-muted-foreground">{formatDateTime(alert.triggered_at)}</p>
              <p className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">{alert.status}</p>
            </div>
          </div>
          <div className="mt-2 grid gap-1 text-xs text-muted-foreground sm:grid-cols-2">
            <p>Current spend: {formatUsd(alert.current_spend_usd)}</p>
            <p>Budget: {alert.budget_usd ? formatUsd(alert.budget_usd) : "Not set"}</p>
            <p>Threshold amount: {formatUsd(alert.threshold_usd)}</p>
            <p>Cycle: {alert.cycle_start ?? "-"} to {alert.cycle_end ?? "-"}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
