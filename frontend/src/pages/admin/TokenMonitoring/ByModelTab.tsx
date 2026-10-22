import { useMemo, useState } from "react";
import { ModelCostBarChart } from "@/components/token-monitoring/ModelCostBarChart";
import { ModelCostLatencyScatter } from "@/components/token-monitoring/ModelCostLatencyScatter";
import { ModelComparisonTable } from "@/components/token-monitoring/ModelComparisonTable";
import type { TokenUsageByModelResponse } from "@/types/tokenMonitoring";
import { downloadCsv } from "@/utils/csv";

interface ByModelTabProps {
  data: TokenUsageByModelResponse;
  selectedProvider: "all" | "openai" | "anthropic" | "deepseek";
  onProviderChange: (provider: "all" | "openai" | "anthropic" | "deepseek") => void;
  datePresetLabel: string;
  granularityLabel: string;
}

type SortKey = "cost" | "latency" | "requests" | "model";

export function ByModelTab({ data, selectedProvider, onProviderChange, datePresetLabel, granularityLabel }: ByModelTabProps) {
  const [sortKey, setSortKey] = useState<SortKey>("cost");
  const [descending, setDescending] = useState(true);

  const filteredRows = useMemo(() => {
    const rows = selectedProvider === "all" ? data.items : data.items.filter((item) => item.provider === selectedProvider);
    const next = [...rows];
    next.sort((left, right) => {
      if (sortKey === "model") {
        return left.model_name.localeCompare(right.model_name);
      }
      if (sortKey === "latency") {
        return left.avg_latency_ms - right.avg_latency_ms;
      }
      if (sortKey === "requests") {
        return left.request_count - right.request_count;
      }
      return Number(left.total_cost_usd) - Number(right.total_cost_usd);
    });
    return descending ? next.reverse() : next;
  }, [data.items, descending, selectedProvider, sortKey]);

  return (
    <section className="space-y-3">
      <article className="rounded-2xl border border-border bg-background p-4">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold">Model Comparison</h3>
            <p className="mt-1 text-xs text-muted-foreground">
              Compare model-level cost and performance for {datePresetLabel.toLowerCase()} ({granularityLabel} buckets).
            </p>
          </div>
          <button
            type="button"
            className="rounded-md border border-border px-3 py-2 text-sm"
            onClick={() => {
              downloadCsv({
                filename: "token-model-comparison.csv",
                headers: [
                  "Provider",
                  "Model",
                  "Input Tokens",
                  "Output Tokens",
                  "Total Tokens",
                  "Total Cost USD",
                  "Request Count",
                  "Avg Latency (ms)",
                  "Cache Hit Rate"
                ],
                rows: filteredRows.map((row) => [
                  row.provider,
                  row.model_name,
                  row.input_tokens,
                  row.output_tokens,
                  row.total_tokens,
                  row.total_cost_usd,
                  row.request_count,
                  Math.round(row.avg_latency_ms),
                  row.cache_hit_rate
                ])
              });
            }}
          >
            Export CSV
          </button>
        </div>

        <div className="mt-3 grid gap-2 sm:grid-cols-3">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Provider
            <select
              value={selectedProvider}
              onChange={(event) => onProviderChange(event.currentTarget.value as "all" | "openai" | "anthropic" | "deepseek")}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </label>

          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Sort By
            <select
              value={sortKey}
              onChange={(event) => setSortKey(event.currentTarget.value as SortKey)}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="cost">Total Cost</option>
              <option value="latency">Latency</option>
              <option value="requests">Request Count</option>
              <option value="model">Model Name</option>
            </select>
          </label>

          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Order
            <select
              value={descending ? "desc" : "asc"}
              onChange={(event) => setDescending(event.currentTarget.value === "desc")}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="desc">Descending</option>
              <option value="asc">Ascending</option>
            </select>
          </label>
        </div>
      </article>

      {filteredRows.length === 0 ? (
        <article className="rounded-2xl border border-border bg-background p-6 text-sm text-muted-foreground">
          No model data found for this provider/date combination.
        </article>
      ) : (
        <>
          <ModelComparisonTable rows={filteredRows} />

          <div className="grid gap-4 lg:grid-cols-2">
            <article className="rounded-2xl border border-border bg-background p-4">
              <h4 className="text-sm font-semibold">Cost Per Model</h4>
              <p className="mt-1 text-xs text-muted-foreground">Comparative cost by model for current filters.</p>
              <div className="mt-3">
                <ModelCostBarChart rows={filteredRows.slice(0, 12)} />
              </div>
            </article>

            <article className="rounded-2xl border border-border bg-background p-4">
              <h4 className="text-sm font-semibold">Cost vs Latency</h4>
              <p className="mt-1 text-xs text-muted-foreground">Bubble size maps request count.</p>
              <div className="mt-3">
                <ModelCostLatencyScatter rows={filteredRows.slice(0, 20)} />
              </div>
            </article>
          </div>
        </>
      )}
    </section>
  );
}
