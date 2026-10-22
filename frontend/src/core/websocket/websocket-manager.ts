import { env } from "@/core/config/env";
import {
  normalizeIncomingWebSocketEvent,
  isIncomingWebSocketEvent,
  isOutgoingWebSocketEvent,
  type IncomingWebSocketEvent,
  type OutgoingWebSocketEvent
} from "./websocket-events";

export type WebSocketConnectionStatus =
  | "idle"
  | "connecting"
  | "connected"
  | "reconnecting"
  | "disconnected";

export interface ReconnectOptions {
  enabled?: boolean;
  maxAttempts?: number;
  baseDelayMs?: number;
  maxDelayMs?: number;
}

export interface WebSocketManagerOptions {
  sessionId?: string;
  wsBaseUrl?: string;
  path?: string;
  queryParams?: Record<string, string | number | boolean | null | undefined>;
  token?: string;
  reconnect?: ReconnectOptions;
  onReconnectScheduled?: (payload: { attempt: number; maxAttempts: number; delayMs: number }) => void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (error: Error | Event) => void;
  onMessage?: (event: IncomingWebSocketEvent) => void;
  onStatusChange?: (status: WebSocketConnectionStatus) => void;
}

type StatusListener = (status: WebSocketConnectionStatus) => void;
type MessageListener = (event: IncomingWebSocketEvent) => void;
type OpenListener = (event: Event) => void;
type CloseListener = (event: CloseEvent) => void;
type ErrorListener = (error: Error | Event) => void;

const DEFAULT_RECONNECT_OPTIONS: Required<ReconnectOptions> = {
  enabled: true,
  maxAttempts: 5,
  baseDelayMs: 1_000,
  maxDelayMs: 10_000
};

const MAX_CLOSE_REASON_LENGTH = 123;

function withWsScheme(url: URL): URL {
  const protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.protocol = protocol;
  return url;
}

function buildSocketUrl(options: WebSocketManagerOptions): string {
  const configuredBase = options.wsBaseUrl ?? env.wsBaseUrl;
  const origin = window.location.origin;

  let url: URL;

  if (configuredBase.startsWith("ws://") || configuredBase.startsWith("wss://")) {
    url = new URL(configuredBase);
  } else if (configuredBase.startsWith("http://") || configuredBase.startsWith("https://")) {
    url = withWsScheme(new URL(configuredBase));
  } else {
    url = withWsScheme(new URL(configuredBase, origin));
  }

  if (options.path) {
    const normalizedPath = options.path.startsWith("/") ? options.path : `/${options.path}`;
    url.pathname = `${url.pathname.replace(/\/$/, "")}${normalizedPath}`;
  }

  if (options.sessionId) {
    url.searchParams.set("session_id", options.sessionId);
  }

  if (options.token) {
    url.searchParams.set("token", options.token);
  }

  if (options.queryParams) {
    for (const [key, value] of Object.entries(options.queryParams)) {
      if (value === null || value === undefined) continue;
      url.searchParams.set(key, String(value));
    }
  }

  return url.toString();
}

function sanitizeCloseCode(code: number): number {
  if (code === 1000) return code;
  if (code >= 3000 && code <= 4999) return code;
  return 1000;
}

function sanitizeCloseReason(reason: string): string {
  return reason.slice(0, MAX_CLOSE_REASON_LENGTH);
}

export class WebSocketManager {
  private socket: WebSocket | null = null;
  private reconnectTimer: number | null = null;
  private reconnectAttempts = 0;
  private hasManualDisconnect = false;
  private status: WebSocketConnectionStatus = "idle";

  private readonly options: WebSocketManagerOptions;
  private readonly reconnect: Required<ReconnectOptions>;

  private readonly statusListeners = new Set<StatusListener>();
  private readonly messageListeners = new Set<MessageListener>();
  private readonly openListeners = new Set<OpenListener>();
  private readonly closeListeners = new Set<CloseListener>();
  private readonly errorListeners = new Set<ErrorListener>();

  constructor(options: WebSocketManagerOptions = {}) {
    this.options = options;
    this.reconnect = {
      ...DEFAULT_RECONNECT_OPTIONS,
      ...(options.reconnect ?? {})
    };
  }

  connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.CONNECTING || this.socket.readyState === WebSocket.OPEN)) {
      return;
    }

    this.clearReconnectTimer();
    this.hasManualDisconnect = false;

    const existingSocket = this.socket;
    if (existingSocket && existingSocket.readyState === WebSocket.CLOSING) {
      return;
    }

    const url = buildSocketUrl(this.options);
    this.setStatus(this.reconnectAttempts > 0 ? "reconnecting" : "connecting");

    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = (event) => {
      if (socket !== this.socket) {
        return;
      }

      this.reconnectAttempts = 0;
      this.setStatus("connected");
      this.options.onOpen?.(event);
      this.openListeners.forEach((listener) => listener(event));
    };

    socket.onmessage = (event) => {
      if (socket !== this.socket) {
        return;
      }

      if (typeof event.data !== "string") {
        this.emitError(new Error("WebSocket message data is not a JSON string."));
        return;
      }

      let parsed: unknown;
      try {
        parsed = JSON.parse(event.data);
      } catch {
        this.emitError(new Error("Malformed JSON received from WebSocket."));
        return;
      }

      const normalized = normalizeIncomingWebSocketEvent(parsed);
      if (!normalized || !isIncomingWebSocketEvent(normalized)) {
        this.emitError(new Error("Unsupported WebSocket event contract."));
        return;
      }

      this.options.onMessage?.(normalized);
      this.messageListeners.forEach((listener) => listener(normalized));
    };

    socket.onerror = (event) => {
      if (socket !== this.socket) {
        return;
      }

      this.options.onError?.(event);
      this.errorListeners.forEach((listener) => listener(event));
    };

    socket.onclose = (event) => {
      if (socket === this.socket) {
        this.socket = null;
      }

      this.options.onClose?.(event);
      this.closeListeners.forEach((listener) => listener(event));

      if (this.hasManualDisconnect) {
        this.setStatus("disconnected");
        return;
      }

      if (!this.reconnect.enabled || this.reconnectAttempts >= this.reconnect.maxAttempts) {
        this.setStatus("disconnected");
        return;
      }

      this.scheduleReconnect();
    };
  }

  disconnect(code = 1000, reason = "manual_disconnect"): void {
    this.hasManualDisconnect = true;
    this.clearReconnectTimer();

    const socket = this.socket;
    this.socket = null;

    if (!socket) {
      this.setStatus("disconnected");
      return;
    }

    socket.onopen = null;
    socket.onmessage = null;
    socket.onerror = null;
    socket.onclose = null;

    if (socket.readyState === WebSocket.CONNECTING || socket.readyState === WebSocket.OPEN) {
      socket.close(sanitizeCloseCode(code), sanitizeCloseReason(reason));
    }

    this.setStatus("disconnected");
  }

  reconnectNow(): void {
    this.clearReconnectTimer();
    this.reconnectAttempts = 0;
    this.disconnect(1000, "manual_reconnect");
    this.hasManualDisconnect = false;
    this.connect();
  }

  send(event: OutgoingWebSocketEvent): boolean {
    if (!isOutgoingWebSocketEvent(event)) {
      this.emitError(new Error("Outgoing event does not match the WebSocket contract."));
      return false;
    }

    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return false;
    }

    try {
      this.socket.send(JSON.stringify(event));
      return true;
    } catch (error) {
      this.emitError(error instanceof Error ? error : new Error("Failed to send WebSocket message."));
      return false;
    }
  }

  getStatus(): WebSocketConnectionStatus {
    return this.status;
  }

  getReconnectAttempts(): number {
    return this.reconnectAttempts;
  }

  onStatusChange(listener: StatusListener): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  onOpen(listener: OpenListener): () => void {
    this.openListeners.add(listener);
    return () => this.openListeners.delete(listener);
  }

  onClose(listener: CloseListener): () => void {
    this.closeListeners.add(listener);
    return () => this.closeListeners.delete(listener);
  }

  onError(listener: ErrorListener): () => void {
    this.errorListeners.add(listener);
    return () => this.errorListeners.delete(listener);
  }

  private setStatus(status: WebSocketConnectionStatus): void {
    if (this.status === status) return;

    this.status = status;
    this.options.onStatusChange?.(status);
    this.statusListeners.forEach((listener) => listener(status));
  }

  private emitError(error: Error | Event): void {
    this.options.onError?.(error);
    this.errorListeners.forEach((listener) => listener(error));
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts += 1;
    const multiplier = 2 ** (this.reconnectAttempts - 1);
    const delayMs = Math.min(this.reconnect.maxDelayMs, this.reconnect.baseDelayMs * multiplier);

    this.setStatus("reconnecting");
    this.options.onReconnectScheduled?.({
      attempt: this.reconnectAttempts,
      maxAttempts: this.reconnect.maxAttempts,
      delayMs
    });
    this.clearReconnectTimer();

    this.reconnectTimer = window.setTimeout(() => {
      if (this.hasManualDisconnect) {
        this.setStatus("disconnected");
        return;
      }
      this.connect();
    }, delayMs);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer === null) return;
    window.clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
  }
}
