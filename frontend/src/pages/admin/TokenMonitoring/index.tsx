import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { LoadingFallback, NetworkError } from "@/components/ui";
import {
  useActiveBudgetAlerts,
  useApiKeys,
  useDismissRecommendation,
  useOptimizationRecommendations,
  useOptimizationSavingsReport,
  useRealtimeCounter,
  useTokenUsageByKey,
  useTokenUsageByModel,
  useTokenUsageForecast,
  useTokenUsageSummary,
  useUpdateApiKeyBudget
} from "@/hooks/useTokenUsage";
import { BudgetGauge } from "@/components/token-monitoring/BudgetGauge";
import { downloadCsv } from "@/utils/csv";
import { ByKeyTab } from "./ByKeyTab";
import { ByModelTab } from "./ByModelTab";
import { OptimizationTab } from "./OptimizationTab";
import { AlertsTab } from "./AlertsTab";
import { OverviewTab } from "./OverviewTab";
import type { TimeGranularity } from "@/types/tokenMonitoring";

const tabs = [
  { id: "overview", label: "Overview" },
  { id: "by-model", label: "By Model" },
  { id: "by-key", label: "By API Key" },
  { id: "optimization", label: "Optimization" },
  { id: "alerts", label: "Alerts" }
] as const;

type TabId = (typeof tabs)[number]["id"];
type DatePreset = "today" | "last_7_days" | "last_30_days" | "current_month";

function startOfDay(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate(), 0, 0, 0, 0);
}

function getPresetRange(preset: DatePreset): { dateFrom: string; dateTo: string; label: string } {
  const now = new Date();
  const todayStart = startOfDay(now);
  const end = now.toISOString();

  if (preset === "today") {
    return { dateFrom: todayStart.toISOString(), dateTo: end, label: "Today" };
  }
  if (preset === "last_7_days") {
    const from = new Date(todayStart);
    from.setDate(from.getDate() - 6);
    return { dateFrom: from.toISOString(), dateTo: end, label: "Last 7 Days" };
  }
  if (preset === "last_30_days") {
    const from = new Date(todayStart);
    from.setDate(from.getDate() - 29);
    return { dateFrom: from.toISOString(), dateTo: end, label: "Last 30 Days" };
  }

  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0);
  return { dateFrom: monthStart.toISOString(), dateTo: end, label: "Current Month" };
}

export function TokenMonitoringPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialTab = (searchParams.get("tab") as TabId | null) ?? "overview";
  const [activeTab, setActiveTab] = useState<TabId>(tabs.some((tab) => tab.id === initialTab) ? initialTab : "overview");
  const [selectedApiKeyId, setSelectedApiKeyId] = useState<string | null>(null);
  const [datePreset, setDatePreset] = useState<DatePreset>("last_30_days");
  const [granularity, setGranularity] = useState<TimeGranularity>("daily");
  const [providerFilter, setProviderFilter] = useState<"all" | "openai" | "anthropic" | "deepseek">("all");

  useEffect(() => {
    const tabParam = searchParams.get("tab") as TabId | null;
    if (!tabParam || !tabs.some((tab) => tab.id === tabParam) || tabParam === activeTab) {
      return;
    }
    setActiveTab(tabParam);
  }, [activeTab, searchParams]);

  const range = useMemo(() => getPresetRange(datePreset), [datePreset]);
  const previousRange = useMemo(() => {
    const start = new Date(range.dateFrom);
    const end = new Date(range.dateTo);
    const durationMs = Math.max(end.getTime() - start.getTime(), 1);
    const prevEnd = new Date(start.getTime() - 1);
    const prevStart = new Date(prevEnd.getTime() - durationMs);
    return {
      dateFrom: prevStart.toISOString(),
      dateTo: prevEnd.toISOString()
    };
  }, [range.dateFrom, range.dateTo]);

  const filters = useMemo(
    () => ({
      provider: providerFilter === "all" ? undefined : providerFilter,
      dateFrom: range.dateFrom,
      dateTo: range.dateTo
    }),
    [providerFilter, range.dateFrom, range.dateTo]
  );

  const previousFilters = useMemo(
    () => ({
      provider: providerFilter === "all" ? undefined : providerFilter,
      dateFrom: previousRange.dateFrom,
      dateTo: previousRange.dateTo
    }),
    [previousRange.dateFrom, previousRange.dateTo, providerFilter]
  );

  const summaryQuery = useTokenUsageSummary(filters, granularity);
  const previousSummaryQuery = useTokenUsageSummary(previousFilters, granularity);
  const byModelQuery = useTokenUsageByModel(filters);
  const forecastQuery = useTokenUsageForecast(filters);
  const recommendationsQuery = useOptimizationRecommendations();
  const savingsQuery = useOptimizationSavingsReport();
  const alertsQuery = useActiveBudgetAlerts();
  const apiKeysQuery = useApiKeys({});

  const realtime = useRealtimeCounter(activeTab === "overview");
  const budgetMutation = useUpdateApiKeyBudget();
  const dismissMutation = useDismissRecommendation();

  const [liveDeltas, setLiveDeltas] = useState({ costUsd: 0, totalTokens: 0, requestCount: 0 });

  useEffect(() => {
    setLiveDeltas({ costUsd: 0, totalTokens: 0, requestCount: 0 });
  }, [range.dateFrom, range.dateTo, providerFilter, granularity]);

  useEffect(() => {
    if (!realtime.latestEvent) {
      return;
    }
    const latestEvent = realtime.latestEvent;

    if (providerFilter !== "all" && latestEvent.provider !== providerFilter) {
      return;
    }

    const eventTime = new Date(latestEvent.timestamp);
    const from = new Date(range.dateFrom);
    const to = new Date(range.dateTo);
    if (eventTime < from || eventTime > to) {
      return;
    }

    setLiveDeltas((current) => ({
      costUsd: current.costUsd + Number(latestEvent.cost_delta ?? 0),
      totalTokens: current.totalTokens + Number(latestEvent.tokens_delta ?? 0),
      requestCount: current.requestCount + 1
    }));
  }, [providerFilter, range.dateFrom, range.dateTo, realtime.latestEvent]);

  const apiKeys = useMemo(() => apiKeysQuery.data?.items ?? [], [apiKeysQuery.data?.items]);

  useEffect(() => {
    if (!selectedApiKeyId && apiKeys.length > 0) {
      setSelectedApiKeyId(apiKeys[0]!.id);
      return;
    }
    if (selectedApiKeyId && apiKeys.length > 0 && !apiKeys.some((item) => item.id === selectedApiKeyId)) {
      setSelectedApiKeyId(apiKeys[0]!.id);
    }
  }, [apiKeys, selectedApiKeyId]);

  const byKeyFilters = useMemo(
    () => ({
      provider: providerFilter === "all" ? undefined : providerFilter,
      dateFrom: range.dateFrom,
      dateTo: range.dateTo
    }),
    [providerFilter, range.dateFrom, range.dateTo]
  );

  const byKeyQuery = useTokenUsageByKey(selectedApiKeyId, byKeyFilters);

  const isLoadingCore = summaryQuery.isLoading || byModelQuery.isLoading || forecastQuery.isLoading;
  const isErrorCore = summaryQuery.isError || byModelQuery.isError || forecastQuery.isError;

  const selectedApiKey = useMemo(
    () => (selectedApiKeyId ? apiKeys.find((item) => item.id === selectedApiKeyId) ?? null : null),
    [apiKeys, selectedApiKeyId]
  );

  return (
    <main className="mx-auto w-full max-w-[1280px] space-y-4 p-4 sm:p-6" dir="auto">
      <section className="rounded-2xl border border-border bg-background/95 p-5 shadow-sm">
        <h1 className="text-2xl font-semibold">Token Monitoring Dashboard</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Monitor LLM token usage, costs, forecast trends, optimization suggestions, and budget alerts in one place.
        </p>
      </section>

      <section className="flex flex-wrap gap-2 text-sm">
        <a href="/admin/knowledge" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Sources
        </a>
        <a href="/admin/rag" className="rounded-md border border-border px-3 py-1.5">
          RAG Management
        </a>
        <a href="/admin/knowledge-graph" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Graph
        </a>
        <a href="/admin/token-monitoring" className="rounded-md border border-border bg-muted px-3 py-1.5 font-medium">
          Token Monitoring
        </a>
      </section>

      <section className="rounded-2xl border border-border bg-background p-3">
        <nav className="grid grid-cols-2 gap-2 sm:grid-cols-5" aria-label="Token monitoring tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setActiveTab(tab.id);
                setSearchParams((current) => {
                  const next = new URLSearchParams(current);
                  next.set("tab", tab.id);
                  return next;
                });
              }}
              className={`rounded-md border px-3 py-2 text-sm ${
                activeTab === tab.id ? "border-primary bg-primary/15 text-foreground" : "border-border text-muted-foreground"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </section>

      <section className="rounded-2xl border border-border bg-background p-3">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Date Range
            <select
              value={datePreset}
              onChange={(event) => setDatePreset(event.currentTarget.value as DatePreset)}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="today">Today</option>
              <option value="last_7_days">Last 7 Days</option>
              <option value="last_30_days">Last 30 Days</option>
              <option value="current_month">Current Month</option>
            </select>
          </label>

          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Provider Filter
            <select
              value={providerFilter}
              onChange={(event) => setProviderFilter(event.currentTarget.value as "all" | "openai" | "anthropic" | "deepseek")}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </label>

          {activeTab === "overview" || activeTab === "by-model" ? (
            <button
              type="button"
              className="rounded-md border border-border px-3 py-2 text-sm"
              onClick={() => {
                if (!summaryQuery.data) {
                  return;
                }
                downloadCsv({
                  filename: `token-overview-${datePreset}.csv`,
                  headers: [
                    "Bucket",
                    "Provider",
                    "Model",
                    "API Key ID",
                    "Prompt Tokens",
                    "Completion Tokens",
                    "Total Tokens",
                    "Request Count",
                    "Average Latency",
                    "Cache Hit Rate",
                    "Total Cost USD"
                  ],
                  rows: summaryQuery.data.points.map((point) => [
                    point.bucket_start,
                    point.provider,
                    point.model_name,
                    point.api_key_id,
                    point.prompt_tokens,
                    point.completion_tokens,
                    point.total_tokens,
                    point.request_count,
                    point.avg_latency_ms,
                    point.cache_hit_rate,
                    point.total_cost_usd
                  ])
                });
              }}
            >
              Export Overview CSV
            </button>
          ) : null}

          <button
            type="button"
            className="rounded-md border border-border px-3 py-2 text-sm"
            onClick={() => {
              const refetchTasks: Array<Promise<unknown>> = [
                summaryQuery.refetch(),
                previousSummaryQuery.refetch(),
                byModelQuery.refetch(),
                forecastQuery.refetch(),
                apiKeysQuery.refetch(),
                alertsQuery.refetch(),
                recommendationsQuery.refetch(),
                savingsQuery.refetch()
              ];
              if (selectedApiKeyId) {
                refetchTasks.push(byKeyQuery.refetch());
              }
              void Promise.all([
                ...refetchTasks
              ]);
            }}
          >
            Refresh Data
          </button>
        </div>
      </section>

      {isLoadingCore ? <LoadingFallback title="Loading token monitoring data" /> : null}

      {isErrorCore ? (
        <NetworkError
          title="Failed to load token monitoring"
          message={
            summaryQuery.error instanceof Error
              ? summaryQuery.error.message
              : byModelQuery.error instanceof Error
                ? byModelQuery.error.message
                : forecastQuery.error instanceof Error
                  ? forecastQuery.error.message
                  : "Unknown error"
          }
          onRetry={() => {
            void Promise.all([summaryQuery.refetch(), byModelQuery.refetch(), forecastQuery.refetch()]);
          }}
        />
      ) : null}

      {!isLoadingCore && !isErrorCore && summaryQuery.data && byModelQuery.data && forecastQuery.data ? (
        <>
          {activeTab === "overview" ? (
            <section className="space-y-4">
              <OverviewTab
                summary={summaryQuery.data}
                previousSummary={previousSummaryQuery.data ?? null}
                byModelItems={byModelQuery.data.items}
                forecast={forecastQuery.data}
                selectedGranularity={granularity}
                onGranularityChange={setGranularity}
                datePresetLabel={range.label}
                latestRealtimeEvent={realtime.latestEvent}
                heartbeatAt={realtime.heartbeatAt}
                realtimeErrors={realtime.errors}
                budgetMonthlyUsd={selectedApiKey?.monthly_budget_usd ?? byKeyQuery.data?.budget?.monthly_budget_usd ?? null}
                liveDeltas={liveDeltas}
              />
              <BudgetGauge
                currentSpendUsd={forecastQuery.data.current_spend_usd}
                monthlyBudgetUsd={selectedApiKey?.monthly_budget_usd ?? byKeyQuery.data?.budget?.monthly_budget_usd ?? null}
              />
            </section>
          ) : null}

          {activeTab === "by-model" ? (
            <ByModelTab
              data={byModelQuery.data}
              selectedProvider={providerFilter}
              onProviderChange={setProviderFilter}
              datePresetLabel={range.label}
              granularityLabel={granularity}
            />
          ) : null}

          {activeTab === "by-key" ? (
            apiKeysQuery.isLoading ? (
              <LoadingFallback title="Loading API keys" />
            ) : apiKeysQuery.isError ? (
              <NetworkError
                title="Failed to load API keys"
                message={apiKeysQuery.error instanceof Error ? apiKeysQuery.error.message : "Unknown error"}
                onRetry={() => {
                  void apiKeysQuery.refetch();
                }}
              />
            ) : apiKeys.length === 0 ? (
              <p className="text-sm text-muted-foreground">No API keys are configured yet.</p>
            ) : byKeyQuery.isLoading ? (
              <LoadingFallback title="Loading key details" />
            ) : byKeyQuery.isError ? (
              <NetworkError
                title="Failed to load API key details"
                message={byKeyQuery.error instanceof Error ? byKeyQuery.error.message : "Unknown error"}
                onRetry={() => {
                  void byKeyQuery.refetch();
                }}
              />
            ) : byKeyQuery.data ? (
              <ByKeyTab
                apiKeys={apiKeys}
                selectedKeyId={selectedApiKeyId}
                onSelectKey={setSelectedApiKeyId}
                keyDetails={byKeyQuery.data}
                isSavingBudget={budgetMutation.isPending}
                onSaveBudget={async (payload) => {
                  if (!selectedApiKeyId) {
                    return;
                  }
                  await budgetMutation.mutateAsync({ apiKeyId: selectedApiKeyId, payload });
                  await Promise.all([byKeyQuery.refetch(), apiKeysQuery.refetch(), alertsQuery.refetch()]);
                }}
              />
            ) : null
          ) : null}

          {activeTab === "optimization" ? (
            recommendationsQuery.isLoading || savingsQuery.isLoading ? (
              <LoadingFallback title="Loading optimization insights" />
            ) : recommendationsQuery.isError || savingsQuery.isError ? (
              <NetworkError
                title="Failed to load optimization insights"
                message={
                  recommendationsQuery.error instanceof Error
                    ? recommendationsQuery.error.message
                    : savingsQuery.error instanceof Error
                      ? savingsQuery.error.message
                      : "Unknown error"
                }
                onRetry={() => {
                  void Promise.all([recommendationsQuery.refetch(), savingsQuery.refetch()]);
                }}
              />
            ) : recommendationsQuery.data && savingsQuery.data ? (
              <OptimizationTab
                recommendations={recommendationsQuery.data}
                savingsReport={savingsQuery.data}
                dismissState={dismissMutation}
              />
            ) : null
          ) : null}

          {activeTab === "alerts" ? (
            alertsQuery.isLoading ? (
              <LoadingFallback title="Loading active alerts" />
            ) : alertsQuery.isError ? (
              <NetworkError
                title="Failed to load active alerts"
                message={alertsQuery.error instanceof Error ? alertsQuery.error.message : "Unknown error"}
                onRetry={() => {
                  void alertsQuery.refetch();
                }}
              />
            ) : alertsQuery.data ? (
              <AlertsTab
                alerts={alertsQuery.data}
                apiKeys={apiKeys}
                isSavingBudget={budgetMutation.isPending}
                onSaveBudget={async (apiKeyId, payload) => {
                  await budgetMutation.mutateAsync({ apiKeyId, payload });
                  await Promise.all([alertsQuery.refetch(), apiKeysQuery.refetch()]);
                  if (selectedApiKeyId === apiKeyId) {
                    await byKeyQuery.refetch();
                  }
                }}
              />
            ) : null
          ) : null}
        </>
      ) : null}
    </main>
  );
}
