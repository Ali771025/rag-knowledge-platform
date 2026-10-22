import type { ModelUsageMetrics } from "@/types/tokenMonitoring";
import { formatUsd } from "@/utils/tokenFormatters";

interface ModelCostBarChartProps {
  rows: ModelUsageMetrics[];
}

export function ModelCostBarChart({ rows }: ModelCostBarChartProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No bar chart data available.</p>;
  }

  const max = Math.max(...rows.map((row) => Number(row.total_cost_usd ?? 0)), 0.0001);

  return (
    <section className="space-y-2">
      {rows.map((row) => {
        const cost = Number(row.total_cost_usd ?? 0);
        return (
          <div key={`${row.provider}-${row.model_name}`} className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{row.model_name}</span>
              <span>{formatUsd(cost)}</span>
            </div>
            <div className="h-2 rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max((cost / max) * 100, 3)}%` }} />
            </div>
          </div>
        );
      })}
    </section>
  );
}
