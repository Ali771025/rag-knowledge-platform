import { useMemo, useState } from "react";
import { BudgetSettingsModal } from "@/components/token-monitoring/BudgetSettingsModal";
import type { APIKeyUsageDetailsResponse } from "@/types/tokenMonitoring";
import { KeyDetailPanel } from "@/components/token-monitoring/KeyDetailPanel";
import type { APIKeyListItem, TokenProvider } from "@/types/tokenMonitoring";
import { formatDateTime, formatUsd } from "@/utils/tokenFormatters";

interface ByKeyTabProps {
  apiKeys: APIKeyListItem[];
  selectedKeyId: string | null;
  onSelectKey: (keyId: string) => void;
  keyDetails: APIKeyUsageDetailsResponse;
  isSavingBudget: boolean;
  onSaveBudget: (payload: { monthly_budget_usd: number | null; alert_thresholds: number[] }) => Promise<void>;
}

export function ByKeyTab({
  apiKeys,
  selectedKeyId,
  onSelectKey,
  keyDetails,
  isSavingBudget,
  onSaveBudget
}: ByKeyTabProps) {
  const [search, setSearch] = useState("");
  const [providerFilter, setProviderFilter] = useState<"all" | TokenProvider>("all");
  const [showBudgetModal, setShowBudgetModal] = useState(false);

  const filteredKeys = useMemo(() => {
    const term = search.trim().toLowerCase();
    return apiKeys.filter((item) => {
      if (providerFilter !== "all" && item.provider !== providerFilter) {
        return false;
      }
      if (!term) {
        return true;
      }
      const haystack = `${item.display_name} ${item.key_alias ?? ""} ${item.key_fingerprint}`.toLowerCase();
      return haystack.includes(term);
    });
  }, [apiKeys, providerFilter, search]);

  return (
    <section className="grid gap-4 lg:grid-cols-[280px,1fr]">
      <aside className="space-y-3 rounded-2xl border border-border bg-background p-4">
        <h3 className="text-sm font-semibold">API Keys</h3>
        <input
          type="search"
          value={search}
          onChange={(event) => setSearch(event.currentTarget.value)}
          placeholder="Search keys..."
          className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
        />

        <select
          value={providerFilter}
          onChange={(event) => setProviderFilter(event.currentTarget.value as "all" | TokenProvider)}
          className="w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
        >
          <option value="all">All Providers</option>
          <option value="openai">OpenAI</option>
          <option value="anthropic">Anthropic</option>
          <option value="deepseek">DeepSeek</option>
        </select>

        <div className="max-h-[620px] space-y-2 overflow-y-auto pr-1">
          {filteredKeys.length === 0 ? (
            <p className="text-sm text-muted-foreground">No API keys match these filters.</p>
          ) : (
            filteredKeys.map((key) => (
              <button
                key={key.id}
                type="button"
                onClick={() => onSelectKey(key.id)}
                className={`w-full rounded-xl border p-3 text-start ${
                  selectedKeyId === key.id ? "border-primary bg-primary/10" : "border-border bg-muted/30"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="truncate text-sm font-medium">{key.key_alias ?? key.display_name}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] uppercase ${key.is_active ? "bg-success/20 text-success" : "bg-muted text-muted-foreground"}`}>
                    {key.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{key.provider}</p>
                <p className="mt-1 text-xs text-muted-foreground">Spend: {formatUsd(key.current_month_spend_usd)}</p>
                <p className="mt-1 text-[11px] text-muted-foreground">Last used: {formatDateTime(key.last_used_at)}</p>
              </button>
            ))
          )}
        </div>
      </aside>

      <section className="space-y-4">
        <KeyDetailPanel data={keyDetails} onOpenBudgetSettings={() => setShowBudgetModal(true)} />
      </section>

      <BudgetSettingsModal
        open={showBudgetModal}
        onClose={() => setShowBudgetModal(false)}
        currentBudgetUsd={keyDetails.budget?.monthly_budget_usd ?? null}
        currentThresholds={keyDetails.budget?.alert_thresholds ?? []}
        isSaving={isSavingBudget}
        onSave={onSaveBudget}
      />
    </section>
  );
}
