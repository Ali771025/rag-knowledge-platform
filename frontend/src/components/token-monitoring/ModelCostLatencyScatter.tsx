import type { ModelUsageMetrics } from "@/types/tokenMonitoring";
import { formatInteger, formatUsd } from "@/utils/tokenFormatters";

interface ModelCostLatencyScatterProps {
  rows: ModelUsageMetrics[];
}

export function ModelCostLatencyScatter({ rows }: ModelCostLatencyScatterProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No scatter chart data available.</p>;
  }

  const maxCost = Math.max(...rows.map((row) => Number(row.total_cost_usd ?? 0)), 0.0001);
  const maxLatency = Math.max(...rows.map((row) => Number(row.avg_latency_ms ?? 0)), 1);
  const maxRequests = Math.max(...rows.map((row) => Number(row.request_count ?? 0)), 1);

  return (
    <div className="space-y-3">
      <div className="relative h-72 rounded-2xl border border-border bg-background">
        {rows.map((row) => {
          const xRatio = Number(row.total_cost_usd ?? 0) / maxCost;
          const yRatio = Number(row.avg_latency_ms ?? 0) / maxLatency;
          const size = 10 + (Number(row.request_count ?? 0) / maxRequests) * 22;

          return (
            <div
              key={`${row.provider}-${row.model_name}`}
              className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-border/70 bg-primary/65"
              style={{
                left: `${Math.max(8, xRatio * 100)}%`,
                top: `${Math.min(92, 100 - yRatio * 100)}%`,
                width: `${size}px`,
                height: `${size}px`
              }}
              title={`${row.model_name} | Cost ${formatUsd(row.total_cost_usd)} | Latency ${Math.round(row.avg_latency_ms)} ms | Requests ${formatInteger(row.request_count)}`}
            />
          );
        })}

        <div className="absolute inset-x-3 bottom-2 flex justify-between text-[10px] text-muted-foreground">
          <span>Low Cost</span>
          <span>High Cost</span>
        </div>
        <div className="absolute inset-y-3 left-2 flex rotate-180 flex-col justify-between text-[10px] text-muted-foreground [writing-mode:vertical-rl]">
          <span>High Latency</span>
          <span>Low Latency</span>
        </div>
      </div>
      <p className="text-xs text-muted-foreground">Bubble size represents request count.</p>
    </div>
  );
}
