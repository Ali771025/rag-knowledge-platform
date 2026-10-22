import { getOnboardingConversationSummaryStateLabel, type ConversationSummaryViewModel } from "@/features/onboarding";

interface ConversationSummaryCardProps {
  summary: ConversationSummaryViewModel | null;
}

export function ConversationSummaryCard({ summary }: ConversationSummaryCardProps) {
  if (!summary) {
    return <p className="text-sm text-muted-foreground">The conversation summary will appear here once enough context is available.</p>;
  }

  return (
    <div className="space-y-2 rounded-xl border border-border/70 bg-background px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-foreground">{summary.title}</p>
        <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {getOnboardingConversationSummaryStateLabel(summary.state)}
        </span>
      </div>
      {summary.summary ? <p className="text-sm text-foreground">{summary.summary}</p> : null}
      {summary.highlights.length > 0 ? (
        <ul className="list-disc space-y-1 pl-5 text-xs text-muted-foreground">
          {summary.highlights.map((highlight) => (
            <li key={highlight}>{highlight}</li>
          ))}
        </ul>
      ) : null}
      <p className="text-xs text-muted-foreground">{summary.messageCount > 0 ? `${summary.messageCount} messages captured` : "No messages captured yet"}</p>
    </div>
  );
}
