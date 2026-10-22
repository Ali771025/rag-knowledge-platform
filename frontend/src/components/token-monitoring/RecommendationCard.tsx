import type { OptimizationRecommendationItem } from "@/types/tokenMonitoring";
import { formatDateTime, formatUsd } from "@/utils/tokenFormatters";
import { AlertTriangle, CircleAlert, Gauge, Sparkles, TrendingDown, Zap } from "lucide-react";

interface RecommendationCardProps {
  recommendation: OptimizationRecommendationItem;
  onDismiss: (id: string) => Promise<void>;
  isDismissing: boolean;
}

const severityClass: Record<string, string> = {
  info: "border-cyan-500/40",
  warning: "border-amber-500/50",
  critical: "border-rose-500/60"
};

const severityBadgeClass: Record<string, string> = {
  info: "bg-cyan-500/15 text-cyan-300 border-cyan-500/30",
  warning: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  critical: "bg-rose-500/15 text-rose-300 border-rose-500/30"
};

const categoryIcon: Record<string, typeof TrendingDown> = {
  cost: TrendingDown,
  performance: Gauge,
  reliability: AlertTriangle,
  caching: Zap
};

export function RecommendationCard({ recommendation, onDismiss, isDismissing }: RecommendationCardProps) {
  const CategoryIcon = categoryIcon[recommendation.category] ?? Sparkles;

  return (
    <article className={`rounded-2xl border bg-background p-4 ${severityClass[recommendation.severity] ?? "border-border"}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${severityBadgeClass[recommendation.severity] ?? "border-border text-muted-foreground"}`}>
              <CircleAlert className="h-3.5 w-3.5" />
              {recommendation.severity}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[11px] text-muted-foreground">
              <CategoryIcon className="h-3.5 w-3.5" />
              {recommendation.category}
            </span>
          </div>
          <h4 className="mt-1 text-sm font-semibold">{recommendation.title}</h4>
        </div>
        <div className="text-end">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Potential Monthly Saving</p>
          <p className="text-sm font-semibold text-foreground">{formatUsd(recommendation.potential_saving_usd)}</p>
        </div>
      </div>
      <p className="mt-2 text-sm text-muted-foreground">{recommendation.description}</p>
      {recommendation.action_items.length > 0 ? (
        <ul className="mt-3 space-y-1 text-xs text-muted-foreground">
          {recommendation.action_items.map((item) => (
            <li key={item}>- {item}</li>
          ))}
        </ul>
      ) : null}
      <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
        <span>Generated {formatDateTime(recommendation.generated_at)}</span>
        <button
          type="button"
          disabled={isDismissing || recommendation.is_dismissed}
          className="rounded-md border border-border px-2 py-1 disabled:opacity-60"
          onClick={async () => {
            await onDismiss(recommendation.id);
          }}
        >
          {recommendation.is_dismissed ? "Dismissed" : isDismissing ? "Dismissing..." : "Dismiss"}
        </button>
      </div>
    </article>
  );
}
