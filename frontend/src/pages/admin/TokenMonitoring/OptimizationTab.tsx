import { RecommendationCard } from "@/components/token-monitoring/RecommendationCard";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { dsMotionVariants } from "@/design-system/motion";
import { useMemo, useState } from "react";
import type {
  OptimizationRecommendationItem,
  OptimizationRecommendationListResponse,
  OptimizationSavingsReportResponse,
  RecommendationDismissResponse,
  RecommendationCategory,
  RecommendationSeverity
} from "@/types/tokenMonitoring";
import { formatUsd } from "@/utils/tokenFormatters";

interface OptimizationTabProps {
  recommendations: OptimizationRecommendationListResponse;
  savingsReport: OptimizationSavingsReportResponse;
  dismissState: {
    isPending: boolean;
    mutateAsync: (id: string) => Promise<RecommendationDismissResponse>;
  };
}

export function OptimizationTab({ recommendations, savingsReport, dismissState }: OptimizationTabProps) {
  const shouldReduceMotion = useReducedMotion();
  const [categoryFilter, setCategoryFilter] = useState<"all" | RecommendationCategory>("all");
  const [severityFilter, setSeverityFilter] = useState<"all" | RecommendationSeverity>("all");

  const filteredRecommendations = useMemo(() => {
    return recommendations.items.filter((item) => {
      if (categoryFilter !== "all" && item.category !== categoryFilter) {
        return false;
      }
      if (severityFilter !== "all" && item.severity !== severityFilter) {
        return false;
      }
      return true;
    });
  }, [categoryFilter, recommendations.items, severityFilter]);

  const categorySummary = useMemo(() => {
    const categories = ["cost", "performance", "reliability", "caching"] as const;
    return categories.map((category) => ({
      category,
      potential_saving_usd:
        savingsReport.savings_by_category.find((entry) => entry.category === category)?.potential_saving_usd ?? "0"
    }));
  }, [savingsReport.savings_by_category]);

  const criticalCount = recommendations.items.filter((item) => item.severity === "critical").length;

  return (
    <section className="space-y-4">
      <article className="rounded-2xl border border-border bg-background p-4">
        <h3 className="text-sm font-semibold">Optimization Savings Summary</h3>
        <p className="mt-1 text-xs text-muted-foreground">
          Total potential monthly savings: {formatUsd(savingsReport.total_potential_monthly_savings_usd)} | Warning and
          critical items: {savingsReport.high_priority_recommendation_count} | Critical items: {criticalCount}
        </p>
        {categorySummary.length > 0 ? (
          <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {categorySummary.map((entry) => (
              <div key={entry.category} className="rounded-xl border border-border bg-muted/50 p-3 text-xs">
                <p className="uppercase tracking-wide text-muted-foreground">{entry.category}</p>
                <p className="mt-1 text-sm font-semibold">{formatUsd(entry.potential_saving_usd)}</p>
              </div>
            ))}
          </div>
        ) : null}
      </article>

      <article className="rounded-2xl border border-border bg-background p-4">
        <div className="grid gap-2 sm:grid-cols-2">
          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Category
            <select
              value={categoryFilter}
              onChange={(event) => setCategoryFilter(event.currentTarget.value as "all" | RecommendationCategory)}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Categories</option>
              <option value="cost">Cost</option>
              <option value="performance">Performance</option>
              <option value="reliability">Reliability</option>
              <option value="caching">Caching</option>
            </select>
          </label>

          <label className="text-xs uppercase tracking-wide text-muted-foreground">
            Severity
            <select
              value={severityFilter}
              onChange={(event) => setSeverityFilter(event.currentTarget.value as "all" | RecommendationSeverity)}
              className="mt-1 w-full rounded-md border border-border bg-muted px-3 py-2 text-sm text-foreground"
            >
              <option value="all">All Severity Levels</option>
              <option value="critical">Critical</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>
          </label>
        </div>
      </article>

      {recommendations.items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No active recommendations yet.</p>
      ) : filteredRecommendations.length === 0 ? (
        <p className="text-sm text-muted-foreground">No recommendations match the selected filters.</p>
      ) : (
        <AnimatePresence mode="popLayout">
          <div className="grid gap-3">
            {filteredRecommendations.map((recommendation: OptimizationRecommendationItem) => (
              <motion.div
                key={recommendation.id}
                layout
                variants={dsMotionVariants.subtleSlideUp}
                initial={shouldReduceMotion ? false : "hidden"}
                animate="visible"
                exit={shouldReduceMotion ? undefined : { opacity: 0, y: -8, transition: { duration: 0.15 } }}
              >
                <RecommendationCard
                  recommendation={recommendation}
                  isDismissing={dismissState.isPending}
                  onDismiss={async (id) => {
                    await dismissState.mutateAsync(id);
                  }}
                />
              </motion.div>
            ))}
          </div>
        </AnimatePresence>
      )}
    </section>
  );
}
