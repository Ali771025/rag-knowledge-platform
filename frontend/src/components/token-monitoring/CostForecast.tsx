import type { CostForecastResponse } from "@/types/tokenMonitoring";
import { formatUsd } from "@/utils/tokenFormatters";

interface CostForecastProps {
  forecast: CostForecastResponse;
}

export function CostForecast({ forecast }: CostForecastProps) {
  return (
    <section className="rounded-2xl border border-border bg-background p-4">
      <p className="text-xs uppercase tracking-wide text-muted-foreground">Billing Forecast</p>
      <div className="mt-2 grid gap-2 sm:grid-cols-2">
        <div>
          <p className="text-xs text-muted-foreground">Current Spend</p>
          <p className="text-lg font-semibold">{formatUsd(forecast.current_spend_usd)}</p>
        </div>
        <div>
          <p className="text-xs text-muted-foreground">Projected Spend</p>
          <p className="text-lg font-semibold">{formatUsd(forecast.projected_spend_usd)}</p>
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Confidence: {forecast.confidence.toUpperCase()} - {forecast.confidence_note}
      </p>
    </section>
  );
}
