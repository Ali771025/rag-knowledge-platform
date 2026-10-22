import type { SessionInsightDisplayItem } from "@/features/conversation-intelligence";

interface SessionInsightCardProps {
  insight: SessionInsightDisplayItem;
}

const INSIGHT_SEVERITY_CLASS = {
  info: "text-muted-foreground",
  warning: "text-warning",
  critical: "text-error"
} as const;

export function SessionInsightCard({ insight }: SessionInsightCardProps) {
  return (
    <article className="rounded-lg border border-border/70 bg-background/80 px-2.5 py-2" role="listitem">
      <p className="text-xs font-semibold text-foreground">{insight.title}</p>
      <p className={`mt-1 text-xs ${INSIGHT_SEVERITY_CLASS[insight.severity]}`}>{insight.description}</p>
    </article>
  );
}
