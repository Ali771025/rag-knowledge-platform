import { CheckCircle2, Circle, Clock3 } from "lucide-react";
import type { ReferralLifecycleStatus, ReferralProgressEvent } from "@/services/referral";

type MilestoneState = "completed" | "current" | "upcoming";

interface StatusTimelineLabels {
  panelTitle: string;
  invited: string;
  connectedWallet: string;
  activatedQora: string;
  firstMicrotask: string;
  firstAchievement: string;
  completed: string;
  current: string;
  upcoming: string;
  noActivity: string;
}

interface TimelineItem {
  id: ReferralLifecycleStatus;
  label: string;
}

interface TimelineRow {
  id: ReferralLifecycleStatus;
  label: string;
  state: MilestoneState;
  occurredAt?: string;
  description?: string;
}

const TIMELINE_ITEMS: ReadonlyArray<ReferralLifecycleStatus> = [
  "invite_opened",
  "wallet_connected",
  "qora_activated",
  "first_microtask_completed",
  "first_achievement_unlocked",
];

const STATUS_INDEX: Record<ReferralLifecycleStatus, number> = {
  created: 0,
  invite_opened: 1,
  wallet_connected: 2,
  qora_activated: 3,
  first_microtask_completed: 4,
  first_achievement_unlocked: 5,
};

function resolveTimelineItems(labels: StatusTimelineLabels): TimelineItem[] {
  return [
    { id: "invite_opened", label: labels.invited },
    { id: "wallet_connected", label: labels.connectedWallet },
    { id: "qora_activated", label: labels.activatedQora },
    { id: "first_microtask_completed", label: labels.firstMicrotask },
    { id: "first_achievement_unlocked", label: labels.firstAchievement },
  ];
}

function toTimelineRows(
  items: TimelineItem[],
  latestStatus: ReferralLifecycleStatus,
  events: ReferralProgressEvent[]
): TimelineRow[] {
  const byStatus = new Map<ReferralLifecycleStatus, ReferralProgressEvent>();
  for (const event of events) {
    if (!TIMELINE_ITEMS.includes(event.status)) continue;
    if (!byStatus.has(event.status)) {
      byStatus.set(event.status, event);
    }
  }

  const currentIndex = STATUS_INDEX[latestStatus];
  return items.map((item, index) => {
    const event = byStatus.get(item.id);
    let state: MilestoneState = "upcoming";
    if (index + 1 < currentIndex) {
      state = "completed";
    } else if (index + 1 === currentIndex) {
      state = "current";
    }
    return {
      id: item.id,
      label: item.label,
      state,
      occurredAt: event?.occurredAt,
      description: event?.description,
    };
  });
}

function stateLabel(labels: StatusTimelineLabels, state: MilestoneState): string {
  if (state === "completed") return labels.completed;
  if (state === "current") return labels.current;
  return labels.upcoming;
}

function indicatorClass(state: MilestoneState): string {
  if (state === "completed") return "text-emerald-300";
  if (state === "current") return "text-[color:var(--color-accent-cyan)]";
  return "text-[color:var(--color-text-muted)]";
}

function connectorClass(state: MilestoneState): string {
  if (state === "completed") return "bg-emerald-400/70";
  return "bg-white/10";
}

interface ReferralLinkStatusPanelProps {
  locale: string;
  labels: StatusTimelineLabels;
  latestStatus: ReferralLifecycleStatus;
  events: ReferralProgressEvent[];
}

export function ReferralLinkStatusPanel({ locale, labels, latestStatus, events }: ReferralLinkStatusPanelProps) {
  const timelineRows = toTimelineRows(resolveTimelineItems(labels), latestStatus, events);
  const hasOccurredEvent = timelineRows.some((row) => row.occurredAt);
  return (
    <div
      className="rounded-xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)] p-3 transition-all"
      aria-label={labels.panelTitle}
    >
      <div className="mb-3 flex items-center justify-between">
        <p className="text-xs font-semibold text-[color:var(--color-text-main)]">{labels.panelTitle}</p>
        {!hasOccurredEvent ? <span className="text-xs text-[color:var(--color-text-muted)]">{labels.noActivity}</span> : null}
      </div>
      <ol className="space-y-2">
        {timelineRows.map((row, index) => {
          const isLast = index === timelineRows.length - 1;
          const dateLabel =
            row.occurredAt && Number.isFinite(new Date(row.occurredAt).valueOf())
              ? new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(row.occurredAt))
              : undefined;
          return (
            <li key={row.id} className="flex gap-3" aria-current={row.state === "current" ? "step" : undefined}>
              <div className="flex w-5 flex-col items-center">
                <span className={indicatorClass(row.state)}>
                  {row.state === "completed" ? (
                    <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                  ) : row.state === "current" ? (
                    <Clock3 className="h-4 w-4" aria-hidden="true" />
                  ) : (
                    <Circle className="h-4 w-4" aria-hidden="true" />
                  )}
                </span>
                {!isLast ? <span className={`mt-1 flex-1 w-px ${connectorClass(row.state)}`} aria-hidden="true" /> : null}
              </div>
              <div className="min-w-0 flex-1 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-[color:var(--color-text-main)]">{row.label}</p>
                  <span className="text-[11px] text-[color:var(--color-text-muted)]">{stateLabel(labels, row.state)}</span>
                </div>
                {dateLabel ? <p className="text-xs text-[color:var(--color-text-muted)]">{dateLabel}</p> : null}
                {row.description ? <p className="text-xs text-[color:var(--color-text-muted)]">{row.description}</p> : null}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export const ReferralLinkExpandableShell = ReferralLinkStatusPanel;
