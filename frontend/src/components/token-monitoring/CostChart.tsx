import { useMemo } from "react";
import type { TimeGranularity, TokenUsageSummaryPoint } from "@/types/tokenMonitoring";
import { formatUsd } from "@/utils/tokenFormatters";

const PROVIDER_STYLES: Record<string, string> = {
  openai: "bg-cyan-400/80",
  anthropic: "bg-emerald-400/80",
  deepseek: "bg-amber-400/80"
};

interface CostChartProps {
  points: TokenUsageSummaryPoint[];
  granularity: TimeGranularity;
}

interface BucketRow {
  key: string;
  label: string;
  providerCosts: Record<string, number>;
  total: number;
}

function bucketLabel(dateIso: string, granularity: TimeGranularity): string {
  const date = new Date(dateIso);
  if (Number.isNaN(date.getTime())) {
    return "-";
  }

  if (granularity === "monthly") {
    return date.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
  }
  if (granularity === "weekly") {
    return `Wk ${date.toLocaleDateString("en-US", { month: "short", day: "2-digit" })}`;
  }
  return date.toLocaleDateString("en-US", { month: "short", day: "2-digit" });
}

export function CostChart({ points, granularity }: CostChartProps) {
  const buckets = useMemo<BucketRow[]>(() => {
    const map = new Map<string, BucketRow>();
    for (const point of points) {
      const key = point.bucket_start;
      const existing = map.get(key) ?? {
        key,
        label: bucketLabel(point.bucket_start, granularity),
        providerCosts: {},
        total: 0
      };
      const value = Number(point.total_cost_usd ?? 0);
      existing.providerCosts[point.provider] = (existing.providerCosts[point.provider] ?? 0) + value;
      existing.total += value;
      map.set(key, existing);
    }

    return Array.from(map.values()).sort((a, b) => a.key.localeCompare(b.key));
  }, [granularity, points]);

  if (buckets.length === 0) {
    return <p className="text-sm text-muted-foreground">No cost-over-time data for this range.</p>;
  }

  const maxTotal = Math.max(...buckets.map((item) => item.total), 0.0001);

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-3 text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-cyan-400" />OpenAI</span>
        <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-emerald-400" />Anthropic</span>
        <span className="inline-flex items-center gap-1"><span className="size-2 rounded-full bg-amber-400" />DeepSeek</span>
      </div>

      <div className="grid gap-2">
        {buckets.map((bucket) => {
          return (
            <div key={bucket.key} className="space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{bucket.label}</span>
                <span>{formatUsd(bucket.total)}</span>
              </div>
              <div className="h-3 overflow-hidden rounded-full border border-border bg-background">
                <div className="flex h-full" style={{ width: `${Math.max((bucket.total / maxTotal) * 100, 2)}%` }}>
                  {Object.entries(bucket.providerCosts).map(([provider, cost]) => {
                    const width = bucket.total > 0 ? `${(cost / bucket.total) * 100}%` : "0%";
                    return (
                      <div
                        key={`${bucket.key}-${provider}`}
                        className={PROVIDER_STYLES[provider] ?? "bg-slate-500/80"}
                        style={{ width }}
                        aria-label={`${provider} ${formatUsd(cost)}`}
                      />
                    );
                  })}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
