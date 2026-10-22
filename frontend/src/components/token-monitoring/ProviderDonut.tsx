import { useMemo } from "react";
import type { ProviderCostBreakdown } from "@/types/tokenMonitoring";
import { formatPercentFromRatio, formatUsd } from "@/utils/tokenFormatters";

const providerColor: Record<string, string> = {
  openai: "#22d3ee",
  anthropic: "#34d399",
  deepseek: "#fbbf24"
};

interface ProviderDonutProps {
  data: ProviderCostBreakdown[];
}

export function ProviderDonut({ data }: ProviderDonutProps) {
  const chart = useMemo(() => {
    const total = data.reduce((sum, item) => sum + Number(item.total_cost_usd ?? 0), 0);
    let cursor = 0;
    const segments = data.map((item) => {
      const value = Number(item.total_cost_usd ?? 0);
      const ratio = total > 0 ? value / total : 0;
      const angle = ratio * 360;
      const start = cursor;
      cursor += angle;
      return {
        provider: item.provider,
        value,
        ratio,
        start,
        end: cursor,
        color: providerColor[item.provider] ?? "#64748b"
      };
    });
    return { total, segments };
  }, [data]);

  if (chart.total <= 0 || chart.segments.length === 0) {
    return <p className="text-sm text-muted-foreground">No provider distribution available.</p>;
  }

  return (
    <div className="grid gap-4 sm:grid-cols-[160px,1fr] sm:items-center">
      <div className="mx-auto size-40 rounded-full" style={{
        background: `conic-gradient(${chart.segments
          .map((segment) => `${segment.color} ${segment.start}deg ${segment.end}deg`)
          .join(",")})`
      }}>
        <div className="mx-auto mt-5 grid size-30 place-items-center rounded-full border border-border bg-background text-center">
          <p className="text-xs text-muted-foreground">Total Cost</p>
          <p className="text-sm font-semibold">{formatUsd(chart.total)}</p>
        </div>
      </div>

      <div className="space-y-2">
        {chart.segments.map((segment) => (
          <div key={segment.provider} className="flex items-center justify-between rounded-xl border border-border bg-background p-3 text-xs">
            <span className="inline-flex items-center gap-2 font-medium uppercase tracking-wide">
              <span className="size-2 rounded-full" style={{ backgroundColor: segment.color }} />
              {segment.provider}
            </span>
            <span>{formatUsd(segment.value)} ({formatPercentFromRatio(segment.ratio)})</span>
          </div>
        ))}
      </div>
    </div>
  );
}
