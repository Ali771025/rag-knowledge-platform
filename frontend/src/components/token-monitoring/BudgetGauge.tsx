import { formatUsd } from "@/utils/tokenFormatters";

interface BudgetGaugeProps {
  currentSpendUsd: string | number;
  monthlyBudgetUsd: string | number | null;
}

export function BudgetGauge({ currentSpendUsd, monthlyBudgetUsd }: BudgetGaugeProps) {
  const current = Number(currentSpendUsd ?? 0);
  const budget = monthlyBudgetUsd === null ? null : Number(monthlyBudgetUsd ?? 0);
  const ratio = budget && budget > 0 ? Math.min(current / budget, 1) : 0;

  return (
    <section className="rounded-2xl border border-border bg-background p-4">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Budget Utilization</p>
          <p className="mt-1 text-xl font-semibold">{formatUsd(current)}</p>
        </div>
        <p className="text-xs text-muted-foreground">{budget ? `of ${formatUsd(budget)}` : "No budget set"}</p>
      </div>
      <div className="mt-3 h-3 overflow-hidden rounded-full border border-border bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(ratio * 100, 2)}%` }} />
      </div>
      {budget ? <p className="mt-2 text-xs text-muted-foreground">{(ratio * 100).toFixed(1)}% used</p> : null}
    </section>
  );
}
