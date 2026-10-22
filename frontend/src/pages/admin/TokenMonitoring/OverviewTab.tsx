import { Activity, Coins, Gauge, Timer } from "lucide-react";
import { CostChart } from "@/components/token-monitoring/CostChart";
import { CostForecast } from "@/components/token-monitoring/CostForecast";
import { KPICard } from "@/components/token-monitoring/KPICard";
import { ProviderDonut } from "@/components/token-monitoring/ProviderDonut";
import { RealTimeCounter } from "@/components/token-monitoring/RealTimeCounter";
import { TopModelsChart } from "@/components/token-monitoring/TopModelsChart";
import type { ModelUsageMetrics, TimeGranularity } from "@/types/tokenMonitoring";
import type { CostForecastResponse, TokenUsageRealtimeEvent, TokenUsageSummaryResponse } from "@/types/tokenMonitoring";
import { formatInteger, formatPercentFromRatio, formatUsd } from "@/utils/tokenFormatters";

interface OverviewTabProps {
  summary: TokenUsageSummaryResponse;
  previousSummary: TokenUsageSummaryResponse | null;
  byModelItems: ModelUsageMetrics[];
  forecast: CostForecastResponse;
  selectedGranularity: TimeGranularity;
  onGranularityChange: (granularity: TimeGranularity) => void;
  datePresetLabel: string;
  latestRealtimeEvent: TokenUsageRealtimeEvent | null;
  heartbeatAt: string | null;
  realtimeErrors: number;
  budgetMonthlyUsd: string | null;
  liveDeltas: {
    costUsd: number;
    totalTokens: number;
    requestCount: number;
  };
}

function summarize(summaryData: TokenUsageSummaryResponse) {
  const totalCost = summaryData.points.reduce((sum, point) => sum + Number(point.total_cost_usd ?? 0), 0);
  const totalRequests = summaryData.points.reduce((sum, point) => sum + Number(point.request_count ?? 0), 0);
  const totalTokens = summaryData.points.reduce((sum, point) => sum + Number(point.total_tokens ?? 0), 0);
  const avgLatency =
    totalRequests > 0
      ? summaryData.points.reduce((sum, point) => sum + point.avg_latency_ms * point.request_count, 0) / totalRequests
      : 0;
  const cacheHitRate =
    totalRequests > 0
      ? summaryData.points.reduce((sum, point) => sum + point.cache_hit_rate * point.request_count, 0) / totalRequests
      : 0;
  return { totalCost, totalRequests, totalTokens, avgLatency, cacheHitRate };
}

export function OverviewTab({
  summary,
  previousSummary,
  byModelItems,
  forecast,
  selectedGranularity,
  onGranularityChange,
  datePresetLabel,
  latestRealtimeEvent,
  heartbeatAt,
  realtimeErrors,
  budgetMonthlyUsd,
  liveDeltas
}: OverviewTabProps) {
  const base = summarize(summary);
  const previous = previousSummary ? summarize(previousSummary) : null;
  const liveCost = base.totalCost + liveDeltas.costUsd;
  const liveTokens = base.totalTokens + liveDeltas.totalTokens;
  const liveRequests = base.totalRequests + liveDeltas.requestCount;

  return (
    <section className="space-y-4">
      <article className="rounded-2xl border border-border bg-background p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-medium">Overview range: {datePresetLabel}</p>
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Granularity
            <select
              value={selectedGranularity}
              onChange={(event) => onGranularityChange(event.currentTarget.value as TimeGranularity)}
              className="ms-2 rounded-md border border-border bg-muted px-2 py-1 text-xs text-foreground"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </label>
        </div>
      </article>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          title="Today's Cost"
          value={liveCost}
          valueFormatter={(value) => formatUsd(value)}
          previousValue={previous?.totalCost}
          hint="Live updates enabled"
          icon={<Coins className="size-4" />}
        />
        <KPICard
          title="Today's Total Tokens"
          value={liveTokens}
          valueFormatter={(value) => formatInteger(value)}
          previousValue={previous?.totalTokens}
          hint="Prompt + completion"
          icon={<Gauge className="size-4" />}
        />
        <KPICard
          title="Average Latency"
          value={base.avgLatency}
          valueFormatter={(value) => `${Math.round(value)} ms`}
          previousValue={previous?.avgLatency}
          hint={`${formatInteger(liveRequests)} requests`}
          icon={<Timer className="size-4" />}
        />
        <KPICard
          title="Cache Hit Rate"
          value={base.cacheHitRate}
          valueFormatter={(value) => formatPercentFromRatio(value)}
          previousValue={previous?.cacheHitRate}
          hint="Lower is an optimization signal"
          icon={<Activity className="size-4" />}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-border bg-background p-4">
          <h3 className="text-sm font-semibold">Cost Trend</h3>
          <div className="mt-3">
            <CostChart points={summary.points} granularity={selectedGranularity} />
          </div>
        </article>

        <article className="rounded-2xl border border-border bg-background p-4">
          <h3 className="text-sm font-semibold">Provider Cost Split</h3>
          <div className="mt-3">
            <ProviderDonut data={summary.provider_cost_breakdown} />
          </div>
        </article>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <CostForecast forecast={forecast} />
        <RealTimeCounter latestEvent={latestRealtimeEvent} heartbeatAt={heartbeatAt} errorCount={realtimeErrors} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <article className="rounded-2xl border border-border bg-background p-4">
          <h3 className="text-sm font-semibold">Top 5 Expensive Models</h3>
          <p className="mt-1 text-xs text-muted-foreground">Based on total cost in the selected range.</p>
          <div className="mt-3">
            <TopModelsChart items={byModelItems} topN={5} />
          </div>
        </article>
        <article className="rounded-2xl border border-border bg-background p-4">
          <h3 className="text-sm font-semibold">Forecast & Budget</h3>
          <CostForecast forecast={forecast} />
          <div className="mt-3 rounded-xl border border-border bg-muted/50 p-3 text-xs">
            <p>Current spend: {formatUsd(forecast.current_spend_usd)}</p>
            <p>Projected spend: {formatUsd(forecast.projected_spend_usd)}</p>
            <p>Configured budget: {budgetMonthlyUsd ? formatUsd(budgetMonthlyUsd) : "Not set"}</p>
            {budgetMonthlyUsd && Number(forecast.projected_spend_usd) > Number(budgetMonthlyUsd) ? (
              <p className="mt-1 font-medium text-warning">Projected spend exceeds configured budget.</p>
            ) : null}
          </div>
        </article>
      </div>
    </section>
  );
}
