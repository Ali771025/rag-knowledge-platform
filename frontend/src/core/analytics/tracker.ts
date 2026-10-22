import {
  ANALYTICS_ENDPOINT_DEFAULT,
  ANALYTICS_FLUSH_INTERVAL_MS,
  ANALYTICS_MAX_BATCH_SIZE,
  ANALYTICS_RETRY_LIMIT
} from "./analytics.constants";
import type {
  AnalyticsContext,
  AnalyticsEvent,
  AnalyticsEventName,
  AnalyticsEventPayloadMap
} from "./analytics.types";
import { chunkEvents, createAnalyticsEvent } from "./tracker.utils";

interface AnalyticsTrackerOptions {
  endpoint?: string;
  maxBatchSize?: number;
  flushIntervalMs?: number;
  retryLimit?: number;
}

interface FlushOptions {
  keepalive?: boolean;
  preferBeacon?: boolean;
}

export class AnalyticsTracker {
  private queue: AnalyticsEvent[] = [];
  private flushTimer: number | null = null;
  private isFlushing = false;
  private lifecycleBound = false;
  private hasShutdown = false;
  private readonly endpoint: string;
  private readonly maxBatchSize: number;
  private readonly flushIntervalMs: number;
  private readonly retryLimit: number;
  private readonly handlePageHide = () => {
    void this.flush({ keepalive: true, preferBeacon: true });
  };
  private readonly handleVisibilityChange = () => {
    if (document.visibilityState === "hidden") {
      void this.flush({ keepalive: true, preferBeacon: true });
    }
  };

  constructor(options: AnalyticsTrackerOptions = {}) {
    this.endpoint = options.endpoint ?? import.meta.env.VITE_ANALYTICS_ENDPOINT ?? ANALYTICS_ENDPOINT_DEFAULT;
    this.maxBatchSize = options.maxBatchSize ?? ANALYTICS_MAX_BATCH_SIZE;
    this.flushIntervalMs = options.flushIntervalMs ?? ANALYTICS_FLUSH_INTERVAL_MS;
    this.retryLimit = options.retryLimit ?? ANALYTICS_RETRY_LIMIT;

    this.setupLifecycleHandlers();
    this.startFlushTimer();
  }

  track<TEventName extends AnalyticsEventName>(
    name: TEventName,
    payload: AnalyticsEventPayloadMap[TEventName],
    context?: AnalyticsContext
  ): void {
    if (this.hasShutdown) {
      return;
    }

    try {
      const event = createAnalyticsEvent(name, payload, context);
      this.queue.push(event);

      if (this.queue.length >= this.maxBatchSize) {
        void this.flush();
      }
    } catch {
      // Intentionally swallow analytics failures to avoid impacting UX flow.
    }
  }

  async flush(options: FlushOptions = {}): Promise<void> {
    if (this.isFlushing || this.queue.length === 0) {
      return;
    }

    this.isFlushing = true;
    const drainingQueue = [...this.queue];
    this.queue = [];

    try {
      const batches = chunkEvents(drainingQueue, this.maxBatchSize);

      for (const batch of batches) {
        const sent = await this.sendBatchWithRetry(batch, options);
        if (!sent) {
          this.queue.unshift(...batch);
        }
      }
    } finally {
      this.isFlushing = false;
    }
  }

  shutdown(reason: AnalyticsEventPayloadMap["session_end"]["reason"] = "manual", messageCount = 0): void {
    if (this.hasShutdown) {
      return;
    }

    this.track("session_end", { reason, messageCount });
    this.hasShutdown = true;
    void this.flush({ keepalive: true, preferBeacon: true });
    this.dispose();
  }

  dispose(): void {
    this.stopFlushTimer();
    this.removeLifecycleHandlers();
  }

  private startFlushTimer(): void {
    if (typeof window === "undefined" || this.flushTimer !== null) {
      return;
    }

    this.flushTimer = window.setInterval(() => {
      void this.flush();
    }, this.flushIntervalMs);
  }

  private stopFlushTimer(): void {
    if (this.flushTimer !== null) {
      window.clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  private setupLifecycleHandlers(): void {
    if (typeof window === "undefined" || this.lifecycleBound) {
      return;
    }

    this.lifecycleBound = true;
    window.addEventListener("pagehide", this.handlePageHide);
    document.addEventListener("visibilitychange", this.handleVisibilityChange);
  }

  private removeLifecycleHandlers(): void {
    if (typeof window === "undefined" || !this.lifecycleBound) {
      return;
    }

    window.removeEventListener("pagehide", this.handlePageHide);
    document.removeEventListener("visibilitychange", this.handleVisibilityChange);
    this.lifecycleBound = false;
  }

  private async sendBatchWithRetry(batch: AnalyticsEvent[], options: FlushOptions): Promise<boolean> {
    for (let attempt = 0; attempt <= this.retryLimit; attempt += 1) {
      const sent = await this.sendBatch(batch, options);
      if (sent) {
        return true;
      }
    }

    return false;
  }

  private async sendBatch(batch: AnalyticsEvent[], options: FlushOptions): Promise<boolean> {
    try {
      const body = JSON.stringify({ events: batch });

      if (options.preferBeacon && typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
        const blob = new Blob([body], { type: "application/json" });
        const queued = navigator.sendBeacon(this.endpoint, blob);
        if (queued) {
          return true;
        }
      }

      const response = await fetch(this.endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body,
        keepalive: options.keepalive ?? false
      });

      return response.ok;
    } catch {
      return false;
    }
  }
}

export const analyticsTracker = new AnalyticsTracker();

if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    analyticsTracker.dispose();
  });
}
