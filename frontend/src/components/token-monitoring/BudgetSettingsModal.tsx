import { useEffect, useState } from "react";
import { ConversationDialogShell } from "@/components/workspace/sidebar/conversation-dialog-shell";

interface BudgetSettingsModalProps {
  open: boolean;
  onClose: () => void;
  currentBudgetUsd: string | null;
  currentThresholds: number[];
  isSaving: boolean;
  onSave: (payload: { monthly_budget_usd: number | null; alert_thresholds: number[] }) => Promise<void>;
}

function normalizeThresholds(raw: string): number[] {
  return raw
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value >= 1 && value <= 100)
    .sort((a, b) => a - b)
    .filter((value, index, arr) => index === 0 || arr[index - 1] !== value);
}

export function BudgetSettingsModal({
  open,
  onClose,
  currentBudgetUsd,
  currentThresholds,
  isSaving,
  onSave
}: BudgetSettingsModalProps) {
  const [budgetInput, setBudgetInput] = useState<string>(currentBudgetUsd ?? "");
  const [thresholdInput, setThresholdInput] = useState<string>((currentThresholds.length > 0 ? currentThresholds : [80, 90, 100]).join(", "));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setBudgetInput(currentBudgetUsd ?? "");
    setThresholdInput((currentThresholds.length > 0 ? currentThresholds : [80, 90, 100]).join(", "));
    setError(null);
  }, [currentBudgetUsd, currentThresholds]);

  if (!open) {
    return null;
  }

  return (
    <ConversationDialogShell
      title="Update Budget Settings"
      description="Configure monthly budget and alert thresholds for this API key."
      onClose={onClose}
    >
      <form
        className="space-y-3"
        onSubmit={async (event) => {
          event.preventDefault();
          const monthlyBudget = budgetInput.trim() ? Number(budgetInput) : null;
          const thresholds = normalizeThresholds(thresholdInput);

          if (monthlyBudget !== null && (!Number.isFinite(monthlyBudget) || monthlyBudget <= 0)) {
            setError("Monthly budget must be a positive number.");
            return;
          }
          if (thresholds.length === 0) {
            setError("At least one valid threshold (1-100) is required.");
            return;
          }

          setError(null);
          await onSave({ monthly_budget_usd: monthlyBudget, alert_thresholds: thresholds });
          onClose();
        }}
      >
        <label className="block text-sm text-slate-300">
          Monthly Budget (USD)
          <input
            type="number"
            min={0}
            step="0.01"
            value={budgetInput}
            onChange={(event) => setBudgetInput(event.currentTarget.value)}
            className="mt-1 w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100"
            placeholder="e.g. 250"
          />
        </label>

        <label className="block text-sm text-slate-300">
          Alert Thresholds (%)
          <input
            type="text"
            value={thresholdInput}
            onChange={(event) => setThresholdInput(event.currentTarget.value)}
            className="mt-1 w-full rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100"
            placeholder="80, 90, 100"
          />
        </label>

        {error ? <p className="text-xs text-rose-400">{error}</p> : null}

        <div className="flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-slate-600 px-3 py-1.5 text-sm text-slate-200"
            disabled={isSaving}
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="rounded-md border border-primary bg-primary/85 px-3 py-1.5 text-sm font-medium text-slate-950 disabled:opacity-60"
          >
            {isSaving ? "Saving..." : "Save"}
          </button>
        </div>
      </form>
    </ConversationDialogShell>
  );
}
