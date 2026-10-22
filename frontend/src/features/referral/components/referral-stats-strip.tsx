import { CardShell } from "@/components/ui";

interface ReferralStatsStripProps {
  locale: string;
  stats: {
    totalInvites: number;
    activatedQora: number;
    firstMicroTask: number;
    firstAchievement: number;
  };
  labels: {
    totalInvites: string;
    activatedQora: string;
    firstMicroTask: string;
    firstAchievement: string;
  };
}

function formatNumber(locale: string, value: number): string {
  return new Intl.NumberFormat(locale).format(value);
}

export function ReferralStatsStrip({ locale, stats, labels }: ReferralStatsStripProps) {
  const items = [
    { label: labels.totalInvites, value: stats.totalInvites },
    { label: labels.activatedQora, value: stats.activatedQora },
    { label: labels.firstMicroTask, value: stats.firstMicroTask },
    { label: labels.firstAchievement, value: stats.firstAchievement },
  ];

  return (
    <section className="grid grid-cols-2 gap-3 md:grid-cols-4" aria-label={labels.totalInvites}>
      {items.map((item) => (
        <CardShell key={item.label} className="min-h-24 p-4">
          <p className="text-xs leading-5 text-[color:var(--color-text-muted)]">{item.label}</p>
          <p className="mt-2 text-2xl font-semibold tabular-nums text-[color:var(--color-text-main)]">
            {formatNumber(locale, item.value)}
          </p>
        </CardShell>
      ))}
    </section>
  );
}
