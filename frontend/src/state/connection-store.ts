import { create } from "zustand";
import type { WebSocketConnectionStatus } from "@/core/websocket";
import { buildConnectionStatusModel, type ConnectionStatusModel } from "@/core/websocket";

interface ConnectionSnapshotInput {
  status?: WebSocketConnectionStatus;
  reconnectAttempts?: number;
  maxReconnectAttempts?: number;
  nextRetryAt?: string | null;
  lastConnectedAt?: string | null;
  lastDisconnectedAt?: string | null;
  lastErrorMessage?: string | null;
  wasEverConnected?: boolean;
}

export interface ConnectionState {
  statusModel: ConnectionStatusModel;
}

export interface ConnectionActions {
  patchConnection: (partial: ConnectionSnapshotInput) => void;
  setStatus: (status: WebSocketConnectionStatus) => void;
  markConnected: () => void;
  markDisconnected: (reason?: string | null) => void;
  markRetryScheduled: (attempt: number, maxAttempts: number, delayMs: number) => void;
  markRecovered: () => void;
  acknowledgeRecovered: () => void;
  setConnectionError: (message: string | null) => void;
  resetConnection: () => void;
}

export type ConnectionStore = ConnectionState & ConnectionActions;

const initialSnapshot: Required<ConnectionSnapshotInput> = {
  status: "idle",
  reconnectAttempts: 0,
  maxReconnectAttempts: 0,
  nextRetryAt: null,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
  lastErrorMessage: null,
  wasEverConnected: false
};

function nowIso() {
  return new Date().toISOString();
}

function buildModel(input: ConnectionSnapshotInput): ConnectionStatusModel {
  const merged = {
    ...initialSnapshot,
    ...input
  };

  return buildConnectionStatusModel({
    status: merged.status,
    reconnectAttempts: merged.reconnectAttempts,
    maxReconnectAttempts: merged.maxReconnectAttempts,
    nextRetryAt: merged.nextRetryAt,
    lastConnectedAt: merged.lastConnectedAt,
    lastDisconnectedAt: merged.lastDisconnectedAt,
    lastErrorMessage: merged.lastErrorMessage,
    wasEverConnected: merged.wasEverConnected
  });
}

export const initialConnectionState: ConnectionState = {
  statusModel: buildModel(initialSnapshot)
};

export const useConnectionStore = create<ConnectionStore>((set) => ({
  ...initialConnectionState,
  patchConnection: (partial) => {
    set((state) => {
      const nextInput: ConnectionSnapshotInput = {
        status: partial.status ?? state.statusModel.status,
        reconnectAttempts: partial.reconnectAttempts ?? state.statusModel.reconnectAttempts,
        maxReconnectAttempts: partial.maxReconnectAttempts ?? state.statusModel.maxReconnectAttempts,
        nextRetryAt: partial.nextRetryAt ?? state.statusModel.nextRetryAt,
        lastConnectedAt: partial.lastConnectedAt ?? state.statusModel.lastConnectedAt,
        lastDisconnectedAt: partial.lastDisconnectedAt ?? state.statusModel.lastDisconnectedAt,
        lastErrorMessage: partial.lastErrorMessage ?? state.statusModel.lastErrorMessage,
        wasEverConnected: partial.wasEverConnected ?? Boolean(state.statusModel.lastConnectedAt)
      };

      return {
        statusModel: buildModel(nextInput)
      };
    });
  },
  setStatus: (status) => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        status
      })
    }));
  },
  markConnected: () => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        status: "connected",
        reconnectAttempts: 0,
        nextRetryAt: null,
        lastConnectedAt: nowIso(),
        lastErrorMessage: null,
        wasEverConnected: true
      })
    }));
  },
  markDisconnected: (reason) => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        status: "disconnected",
        nextRetryAt: null,
        lastDisconnectedAt: nowIso(),
        lastErrorMessage: reason ?? state.statusModel.lastErrorMessage
      })
    }));
  },
  markRetryScheduled: (attempt, maxAttempts, delayMs) => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        status: "reconnecting",
        reconnectAttempts: attempt,
        maxReconnectAttempts: maxAttempts,
        nextRetryAt: new Date(Date.now() + Math.max(0, delayMs)).toISOString()
      })
    }));
  },
  markRecovered: () => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        status: "connected",
        nextRetryAt: null,
        wasEverConnected: true,
        lastConnectedAt: nowIso()
      })
    }));
  },
  acknowledgeRecovered: () => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        reconnectAttempts: 0
      })
    }));
  },
  setConnectionError: (message) => {
    set((state) => ({
      statusModel: buildModel({
        ...state.statusModel,
        lastErrorMessage: message
      })
    }));
  },
  resetConnection: () => {
    set(initialConnectionState);
  }
}));
