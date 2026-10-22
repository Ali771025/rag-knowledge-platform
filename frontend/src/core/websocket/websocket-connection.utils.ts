import type {
  ConnectionBannerState,
  ConnectionHealthState,
  ConnectionRecoveryState,
  ConnectionStatusModel
} from "./websocket-connection.types";
import type { WebSocketConnectionStatus } from "./websocket-manager";

interface BuildConnectionStatusModelInput {
  status: WebSocketConnectionStatus;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  nextRetryAt: string | null;
  lastConnectedAt: string | null;
  lastDisconnectedAt: string | null;
  lastErrorMessage: string | null;
  wasEverConnected: boolean;
}

function deriveRecoveryState(params: {
  status: WebSocketConnectionStatus;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  wasEverConnected: boolean;
}): ConnectionRecoveryState {
  if (params.status === "reconnecting") {
    if (params.reconnectAttempts >= params.maxReconnectAttempts) {
      return "exhausted";
    }
    return "attempting";
  }

  if (params.status === "connected" && params.wasEverConnected) {
    return params.reconnectAttempts > 0 ? "recovered" : "idle";
  }

  if (params.status === "disconnected" && params.reconnectAttempts >= params.maxReconnectAttempts) {
    return "exhausted";
  }

  return "idle";
}

function deriveHealthState(params: {
  status: WebSocketConnectionStatus;
  recovery: ConnectionRecoveryState;
  wasEverConnected: boolean;
  hasError: boolean;
}): ConnectionHealthState {
  if (params.status === "connected") {
    return params.recovery === "recovered" ? "recovered" : "healthy";
  }

  if (params.status === "reconnecting" || params.status === "connecting") {
    return "degraded";
  }

  if (params.recovery === "exhausted" || (params.hasError && !params.wasEverConnected)) {
    return "unavailable";
  }

  if (params.status === "disconnected") {
    return "offline";
  }

  return "degraded";
}

function deriveBannerState(params: {
  health: ConnectionHealthState;
  recovery: ConnectionRecoveryState;
  status: WebSocketConnectionStatus;
}): ConnectionBannerState {
  if (params.health === "recovered") {
    return "recovered";
  }

  if (params.status === "reconnecting" || params.recovery === "attempting") {
    return "reconnecting";
  }

  if (params.health === "unavailable" || params.recovery === "exhausted") {
    return "temporarily_unavailable";
  }

  if (params.health === "offline") {
    return "offline";
  }

  return "none";
}

export function buildConnectionStatusModel(input: BuildConnectionStatusModelInput): ConnectionStatusModel {
  const recovery = deriveRecoveryState({
    status: input.status,
    reconnectAttempts: input.reconnectAttempts,
    maxReconnectAttempts: input.maxReconnectAttempts,
    wasEverConnected: input.wasEverConnected
  });
  const health = deriveHealthState({
    status: input.status,
    recovery,
    wasEverConnected: input.wasEverConnected,
    hasError: Boolean(input.lastErrorMessage)
  });
  const banner = deriveBannerState({
    health,
    recovery,
    status: input.status
  });
  const isConnected = input.status === "connected";
  const isRecovering = input.status === "reconnecting" || recovery === "attempting";
  const isDegraded = health === "degraded";
  const isOffline = health === "offline";
  const isUnavailable = health === "unavailable";
  const hasRecovered = health === "recovered";

  return {
    status: input.status,
    health,
    recovery,
    banner,
    isConnected,
    isDegraded,
    isRecovering,
    isOffline,
    isUnavailable,
    hasRecovered,
    reconnectAttempts: input.reconnectAttempts,
    maxReconnectAttempts: input.maxReconnectAttempts,
    wasEverConnected: input.wasEverConnected,
    nextRetryAt: input.nextRetryAt,
    lastConnectedAt: input.lastConnectedAt,
    lastDisconnectedAt: input.lastDisconnectedAt,
    lastErrorMessage: input.lastErrorMessage
  };
}
