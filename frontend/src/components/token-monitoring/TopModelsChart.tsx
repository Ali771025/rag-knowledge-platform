import { useMemo } from "react";
import type { ModelUsageMetrics } from "@/types/tokenMonitoring";
import { formatUsd } from "@/utils/tokenFormatters";

interface TopModelsChartProps {
  items: ModelUsageMetrics[];
  topN?: number;
}

export function TopModelsChart({ items, topN = 5 }: TopModelsChartProps) {
  const top = useMemo(
    () => [...items].sort((a, b) => Number(b.total_cost_usd) - Number(a.total_cost_usd)).slice(0, topN),
    [items, topN]
  );

  if (top.length === 0) {
    return <p className="text-sm text-muted-foreground">No model cost data available.</p>;
  }

  const maxCost = Math.max(...top.map((item) => Number(item.total_cost_usd ?? 0)), 0.0001);

  return (
    <div className="space-y-2">
      {top.map((item) => {
        const cost = Number(item.total_cost_usd ?? 0);
        return (
          <div key={`${item.provider}-${item.model_name}`} className="space-y-1">
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>{item.model_name}</span>
              <span>{formatUsd(cost)}</span>
            </div>
            <div className="h-2 rounded-full border border-border bg-muted">
              <div className="h-full rounded-full bg-accent" style={{ width: `${Math.max((cost / maxCost) * 100, 4)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
