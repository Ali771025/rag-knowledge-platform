import { useEffect, useMemo, useState, type ReactNode } from "react";
import { ArrowDownRight, ArrowRight, ArrowUpRight } from "lucide-react";

interface KPICardProps {
  title: string;
  value: number;
  valueFormatter: (value: number) => string;
  previousValue?: number | null;
  hint?: string;
  icon?: ReactNode;
}

function trendFromDelta(delta: number): "up" | "down" | "flat" {
  if (delta > 0) return "up";
  if (delta < 0) return "down";
  return "flat";
}

function TrendIcon({ direction }: { direction: "up" | "down" | "flat" }) {
  if (direction === "up") return <ArrowUpRight className="size-3" />;
  if (direction === "down") return <ArrowDownRight className="size-3" />;
  return <ArrowRight className="size-3" />;
}

export function KPICard({ title, value, valueFormatter, previousValue = null, hint, icon }: KPICardProps) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    const start = displayValue;
    const end = value;
    const delta = end - start;
    if (Math.abs(delta) < 0.0001) {
      setDisplayValue(end);
      return;
    }

    const durationMs = 380;
    const startAt = performance.now();
    let frame = 0;

    const tick = (timestamp: number) => {
      const elapsed = timestamp - startAt;
      const progress = Math.min(elapsed / durationMs, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(start + delta * eased);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [value]);

  const trend = useMemo(() => {
    if (previousValue === null || previousValue === undefined) {
      return null;
    }
    const diff = value - previousValue;
    const base = Math.abs(previousValue) > 0.000001 ? Math.abs(previousValue) : 1;
    const deltaPercent = (diff / base) * 100;
    return {
      direction: trendFromDelta(diff),
      diff,
      deltaPercent
    };
  }, [previousValue, value]);

  const trendClass =
    trend?.direction === "up"
      ? "text-warning"
      : trend?.direction === "down"
        ? "text-success"
        : "text-muted-foreground";

  return (
    <article className="rounded-2xl border border-border bg-muted/60 p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{title}</p>
          <p className="mt-2 text-2xl font-semibold text-foreground">{valueFormatter(displayValue)}</p>
          {trend ? (
            <p className={`mt-1 inline-flex items-center gap-1 text-xs ${trendClass}`}>
              <TrendIcon direction={trend.direction} />
              {Math.abs(trend.deltaPercent).toFixed(1)}% vs previous period
            </p>
          ) : hint ? (
            <p className="mt-1 text-xs text-muted-foreground">{hint}</p>
          ) : null}
        </div>
        {icon ? <div className="rounded-xl border border-border bg-background p-2 text-muted-foreground">{icon}</div> : null}
      </div>
    </article>
  );
}
