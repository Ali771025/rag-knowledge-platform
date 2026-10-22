import { useMemo } from "react";
import type { APIKeyUsageDetailsResponse } from "@/types/tokenMonitoring";
import { formatDateTime, formatInteger, formatPercentFromRatio, formatUsd } from "@/utils/tokenFormatters";

interface KeyDetailPanelProps {
  data: APIKeyUsageDetailsResponse;
  onOpenBudgetSettings: () => void;
}
export function KeyDetailPanel({ data, onOpenBudgetSettings }: KeyDetailPanelProps) {

  const usageTotalCost = useMemo(
    () => data.time_series.reduce((sum, point) => sum + Number(point.total_cost_usd ?? 0), 0),
    [data.time_series]
  );

  return (
    <section className="space-y-4">
      <article className="rounded-2xl border border-border bg-muted/50 p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-foreground">{data.api_key.display_name}</h3>
            <p className="text-xs text-muted-foreground">
              Provider: {data.api_key.provider} | Alias: {data.api_key.key_alias ?? "Not set"}
            </p>
          </div>
          <div className="text-end">
            <p className="text-xs text-muted-foreground">Selected Window Cost</p>
            <p className="text-lg font-semibold">{formatUsd(usageTotalCost)}</p>
          </div>
        </div>
      </article>

      <article className="rounded-2xl border border-border bg-background p-4">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h4 className="text-sm font-semibold">Budget Settings</h4>
            <p className="mt-1 text-xs text-muted-foreground">Current monthly budget and alert thresholds for this key.</p>
          </div>
          <button
            type="button"
            onClick={onOpenBudgetSettings}
            className="rounded-md border border-border bg-muted px-3 py-2 text-sm font-medium text-foreground"
          >
            Edit Budget
          </button>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <div className="rounded-xl border border-border bg-muted/50 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Current Spend</p>
            <p className="mt-1 text-sm font-semibold">{formatUsd(data.budget?.current_spend_usd ?? 0)}</p>
          </div>
          <div className="rounded-xl border border-border bg-muted/50 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Monthly Budget</p>
            <p className="mt-1 text-sm font-semibold">
              {data.budget?.monthly_budget_usd ? formatUsd(data.budget.monthly_budget_usd) : "Not Set"}
            </p>
          </div>
          <div className="rounded-xl border border-border bg-muted/50 p-3">
            <p className="text-xs uppercase tracking-wide text-muted-foreground">Thresholds</p>
            <p className="mt-1 text-sm font-semibold">
              {(data.budget?.alert_thresholds ?? []).length > 0
                ? `${(data.budget?.alert_thresholds ?? []).join("%, ")}%`
                : "Not Set"}
            </p>
          </div>
        </div>
      </article>

      <article className="rounded-2xl border border-border bg-background p-4">
        <h4 className="text-sm font-semibold">Recent Requests</h4>
        {data.recent_requests.items.length === 0 ? (
          <p className="mt-2 text-sm text-muted-foreground">No recent requests for this key in the selected range.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-2 py-1 text-start">Time</th>
                  <th className="px-2 py-1 text-start">Model</th>
                  <th className="px-2 py-1 text-end">Tokens</th>
                  <th className="px-2 py-1 text-end">Prompt</th>
                  <th className="px-2 py-1 text-end">Completion</th>
                  <th className="px-2 py-1 text-end">Latency</th>
                  <th className="px-2 py-1 text-start">Endpoint</th>
                  <th className="px-2 py-1 text-end">Cache</th>
                  <th className="px-2 py-1 text-end">Cost</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_requests.items.map((item) => (
                  <tr key={item.id} className="border-t border-border/70">
                    <td className="px-2 py-1">{formatDateTime(item.created_at)}</td>
                    <td className="px-2 py-1">{item.model_name}</td>
                    <td className="px-2 py-1 text-end">{formatInteger(item.total_tokens)}</td>
                    <td className="px-2 py-1 text-end">{formatInteger(item.prompt_tokens)}</td>
                    <td className="px-2 py-1 text-end">{formatInteger(item.completion_tokens)}</td>
                    <td className="px-2 py-1 text-end">{item.latency_ms} ms</td>
                    <td className="px-2 py-1 text-start">{item.endpoint ?? "-"}</td>
                    <td className="px-2 py-1 text-end">{formatPercentFromRatio(item.cache_hit ? 1 : 0)}</td>
                    <td className="px-2 py-1 text-end">{formatUsd(item.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          Showing {data.recent_requests.items.length} of {data.recent_requests.total} recent requests.
        </p>
      </article>
    </section>
  );
}
