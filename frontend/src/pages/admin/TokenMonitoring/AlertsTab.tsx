import { useMemo, useState } from "react";
import { AlertTimeline } from "@/components/token-monitoring/AlertTimeline";
import { BudgetSettingsModal } from "@/components/token-monitoring/BudgetSettingsModal";
import type { ActiveBudgetAlertsResponse, APIKeyListItem, TokenProvider } from "@/types/tokenMonitoring";
import { formatDateTime, formatUsd } from "@/utils/tokenFormatters";

interface AlertsTabProps {
  alerts: ActiveBudgetAlertsResponse;
  apiKeys: APIKeyListItem[];
  isSavingBudget: boolean;
  onSaveBudget: (
    apiKeyId: string,
    payload: { monthly_budget_usd: number | null; alert_thresholds: number[] }
  ) => Promise<void>;
}

export function AlertsTab({ alerts, apiKeys, isSavingBudget, onSaveBudget }: AlertsTabProps) {
  const [providerFilter, setProviderFilter] = useState<"all" | TokenProvider>("all");
  const [search, setSearch] = useState("");
  const [selectedKeyForBudget, setSelectedKeyForBudget] = useState<APIKeyListItem | null>(null);

  const filteredKeys = useMemo(() => {
    const term = search.trim().toLowerCase();
    return apiKeys.filter((key) => {
      if (providerFilter !== "all" && key.provider !== providerFilter) {
        return false;
      }
      if (!term) {
        return true;
      }
      const haystack = `${key.display_name} ${key.key_alias ?? ""} ${key.key_fingerprint}`.toLowerCase();
      return haystack.includes(term);
    });
  }, [apiKeys, providerFilter, search]);

  return (
    <section className="space-y-3">
      <article className="rounded-2xl border border-border bg-background p-4">
        <h3 className="text-sm font-semibold">Active Budget Alerts</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Alerts are generated when monthly spend crosses configured key thresholds.
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Acknowledgement and resolution actions are not available yet in the backend API. This tab is currently read-only.
        </p>
      </article>
      <AlertTimeline alerts={alerts.items} />

      <article className="space-y-3 rounded-2xl border border-border bg-background p-4">
        <div>
          <h3 className="text-sm font-semibold">Budget Configuration</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Update monthly budget and alert thresholds for API keys directly from the alerts view.
          </p>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Search API Keys
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.currentTarget.value)}
              placeholder="Search by alias, name, or fingerprint"
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            />
          </label>

          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Provider
            <select
              value={providerFilter}
              onChange={(event) => setProviderFilter(event.currentTarget.value as "all" | TokenProvider)}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </label>
        </div>

        {filteredKeys.length === 0 ? (
          <p className="text-sm text-muted-foreground">No API keys match this filter.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th className="px-2 py-1 text-start">API Key</th>
                  <th className="px-2 py-1 text-start">Provider</th>
                  <th className="px-2 py-1 text-end">Current Spend</th>
                  <th className="px-2 py-1 text-end">Monthly Budget</th>
                  <th className="px-2 py-1 text-start">Thresholds</th>
                  <th className="px-2 py-1 text-start">Last Used</th>
                  <th className="px-2 py-1 text-end">Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredKeys.map((key) => (
                  <tr key={key.id} className="border-t border-border/70">
                    <td className="px-2 py-1">{key.key_alias ?? key.display_name}</td>
                    <td className="px-2 py-1">{key.provider}</td>
                    <td className="px-2 py-1 text-end">{formatUsd(key.current_month_spend_usd)}</td>
                    <td className="px-2 py-1 text-end">
                      {key.monthly_budget_usd ? formatUsd(key.monthly_budget_usd) : "Not Set"}
                    </td>
                    <td className="px-2 py-1">
                      {key.alert_thresholds.length > 0 ? `${key.alert_thresholds.join("%, ")}%` : "Not Set"}
                    </td>
                    <td className="px-2 py-1">{formatDateTime(key.last_used_at)}</td>
                    <td className="px-2 py-1 text-end">
                      <button
                        type="button"
                        onClick={() => setSelectedKeyForBudget(key)}
                        className="rounded-md border border-border bg-muted px-3 py-1.5 text-xs"
                      >
                        Update Budget
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>

      <BudgetSettingsModal
        open={Boolean(selectedKeyForBudget)}
        onClose={() => setSelectedKeyForBudget(null)}
        currentBudgetUsd={selectedKeyForBudget?.monthly_budget_usd ?? null}
        currentThresholds={selectedKeyForBudget?.alert_thresholds ?? [80, 90, 100]}
        isSaving={isSavingBudget}
        onSave={async (payload) => {
          if (!selectedKeyForBudget) {
            return;
          }
          await onSaveBudget(selectedKeyForBudget.id, payload);
          setSelectedKeyForBudget(null);
        }}
      />
    </section>
  );
}
