import type { ModelUsageMetrics } from "@/types/tokenMonitoring";
import { formatInteger, formatPercentFromRatio, formatUsd } from "@/utils/tokenFormatters";

interface ModelComparisonTableProps {
  rows: ModelUsageMetrics[];
}

export function ModelComparisonTable({ rows }: ModelComparisonTableProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-muted-foreground">No model usage data found.</p>;
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-border">
      <table className="min-w-full text-sm">
        <thead className="bg-muted/60 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-start">Model</th>
            <th className="px-3 py-2 text-start">Provider</th>
            <th className="px-3 py-2 text-end">Input</th>
            <th className="px-3 py-2 text-end">Output</th>
            <th className="px-3 py-2 text-end">Total Cost</th>
            <th className="px-3 py-2 text-end">Requests</th>
            <th className="px-3 py-2 text-end">Avg Latency</th>
            <th className="px-3 py-2 text-end">Cache Hit</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.provider}-${row.model_name}`} className="border-t border-border/70">
              <td className="px-3 py-2">{row.model_name}</td>
              <td className="px-3 py-2">{row.provider}</td>
              <td className="px-3 py-2 text-end">{formatInteger(row.input_tokens)}</td>
              <td className="px-3 py-2 text-end">{formatInteger(row.output_tokens)}</td>
              <td className="px-3 py-2 text-end font-medium">{formatUsd(row.total_cost_usd)}</td>
              <td className="px-3 py-2 text-end">{formatInteger(row.request_count)}</td>
              <td className="px-3 py-2 text-end">{Math.round(row.avg_latency_ms)} ms</td>
              <td className="px-3 py-2 text-end">{formatPercentFromRatio(row.cache_hit_rate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
