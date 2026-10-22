import { getConfidenceLabel, toPercent } from "@/features/conversation-intelligence";

interface ResponseConfidenceIndicatorProps {
  confidence?: number | null;
}

const CONFIDENCE_TEXT_CLASS = {
  Low: "text-warning",
  Moderate: "text-foreground",
  High: "text-success",
  Unknown: "text-muted-foreground"
} as const;

export function ResponseConfidenceIndicator({ confidence }: ResponseConfidenceIndicatorProps) {
  const label = getConfidenceLabel(confidence);
  const percent = toPercent(confidence);
  const hasConfidence = percent !== null;

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Response confidence">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Confidence</p>
        <p className={`text-xs font-semibold ${CONFIDENCE_TEXT_CLASS[label]}`}>{label}</p>
      </div>

      <div
        className="mt-2 h-1.5 w-full rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? 0}
        aria-label="Response confidence level"
      >
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent ?? 0}%` }} />
      </div>

      <p className="mt-1 text-xs text-muted-foreground">{hasConfidence ? `${percent}%` : "Awaiting confidence signal"}</p>
    </section>
  );
}
