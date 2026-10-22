import type { SessionInsightDisplayItem } from "@/features/conversation-intelligence";
import { clampInsightCount } from "@/features/conversation-intelligence";
import { SessionInsightCard } from "./session-insight-card";

interface SessionInsightsListProps {
  insights?: SessionInsightDisplayItem[];
}

export function SessionInsightsList({ insights = [] }: SessionInsightsListProps) {
  const visibleInsights = clampInsightCount(insights);

  if (visibleInsights.length === 0) {
    return null;
  }

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Session insights">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Session insights</p>
      <div className="mt-2 space-y-2" role="list">
        {visibleInsights.map((insight) => (
          <SessionInsightCard key={insight.id} insight={insight} />
        ))}
      </div>
    </section>
  );
}
