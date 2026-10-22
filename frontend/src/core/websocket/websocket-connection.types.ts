export const CONNECTION_HEALTH_STATES = ["healthy", "degraded", "offline", "unavailable", "recovered"] as const;
export type ConnectionHealthState = (typeof CONNECTION_HEALTH_STATES)[number];

export const CONNECTION_RECOVERY_STATES = ["idle", "attempting", "backoff_wait", "exhausted", "recovered"] as const;
export type ConnectionRecoveryState = (typeof CONNECTION_RECOVERY_STATES)[number];

export const CONNECTION_BANNER_STATES = ["none", "reconnecting", "offline", "temporarily_unavailable", "recovered"] as const;
export type ConnectionBannerState = (typeof CONNECTION_BANNER_STATES)[number];

export interface ConnectionStatusModel {
  status: import("./websocket-manager").WebSocketConnectionStatus;
  health: ConnectionHealthState;
  recovery: ConnectionRecoveryState;
  banner: ConnectionBannerState;
  isConnected: boolean;
  isDegraded: boolean;
  isRecovering: boolean;
  isOffline: boolean;
  isUnavailable: boolean;
  hasRecovered: boolean;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  wasEverConnected: boolean;
  nextRetryAt: string | null;
  lastConnectedAt: string | null;
  lastDisconnectedAt: string | null;
  lastErrorMessage: string | null;
}

export function isConnectionHealthState(value: unknown): value is ConnectionHealthState {
  return typeof value === "string" && CONNECTION_HEALTH_STATES.includes(value as ConnectionHealthState);
}

export function isConnectionRecoveryState(value: unknown): value is ConnectionRecoveryState {
  return typeof value === "string" && CONNECTION_RECOVERY_STATES.includes(value as ConnectionRecoveryState);
}

export function isConnectionBannerState(value: unknown): value is ConnectionBannerState {
  return typeof value === "string" && CONNECTION_BANNER_STATES.includes(value as ConnectionBannerState);
}
