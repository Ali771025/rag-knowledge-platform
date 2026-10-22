import { getTrustDisplayLevel, getTrustLabel, toPercent } from "@/features/conversation-intelligence";

interface TrustScoreIndicatorProps {
  trustScore?: number | null;
}

const TRUST_TONE_CLASS = {
  strong: "text-success",
  caution: "text-foreground",
  low: "text-warning",
  unknown: "text-muted-foreground"
} as const;

export function TrustScoreIndicator({ trustScore }: TrustScoreIndicatorProps) {
  const percent = toPercent(trustScore);
  const trustLevel = getTrustDisplayLevel(trustScore);
  const trustLabel = getTrustLabel(trustScore);

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Trust score">
      <div className="flex items-center justify-between gap-2">
        <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Trust</p>
        <p className={`text-xs font-semibold ${TRUST_TONE_CLASS[trustLevel]}`}>{trustLabel}</p>
      </div>

      <div
        className="mt-2 h-1.5 w-full rounded-full bg-muted"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? 0}
        aria-label="Trust progress"
      >
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent ?? 0}%` }} />
      </div>

      <p className="mt-1 text-xs text-muted-foreground">{percent === null ? "Not enough data yet" : `${percent}%`}</p>
    </section>
  );
}
