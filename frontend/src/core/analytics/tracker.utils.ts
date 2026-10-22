import type { AnalyticsContext, AnalyticsEvent, AnalyticsEventName, AnalyticsEventPayloadMap } from "./analytics.types";

export function createAnalyticsEvent<TEventName extends AnalyticsEventName>(
  name: TEventName,
  payload: AnalyticsEventPayloadMap[TEventName],
  context?: AnalyticsContext
): AnalyticsEvent<TEventName> {
  return {
    id: createEventId(),
    name,
    payload,
    ts: context?.ts ?? new Date().toISOString(),
    sessionId: context?.sessionId,
    source: context?.source
  };
}

export function chunkEvents<T>(items: T[], size: number): T[][] {
  if (size <= 0) return [items];

  const chunks: T[][] = [];
  for (let index = 0; index < items.length; index += size) {
    chunks.push(items.slice(index, index + size));
  }
  return chunks;
}

export function createEventId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `evt-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}
