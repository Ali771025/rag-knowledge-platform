import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { WebSocketManager, type WebSocketConnectionStatus, type WebSocketManagerOptions } from "@/core/websocket";
import type { IncomingWebSocketEvent, OutgoingWebSocketEvent } from "@/core/websocket";
import { handleWebSocketEvent } from "@/core/websocket/websocket-handlers";
import { useConnectionStore, useMessageStreamingStore, useSessionStore, useUiStore } from "@/state";

interface UseWebSocketOptions {
  sessionId?: string | null;
  autoConnect?: boolean;
  path?: string;
  wsBaseUrl?: string;
  queryParams?: WebSocketManagerOptions["queryParams"];
  token?: string;
  reconnect?: WebSocketManagerOptions["reconnect"];
  onEvent?: (event: IncomingWebSocketEvent) => void;
  onStatusChange?: (status: WebSocketConnectionStatus) => void;
}

interface UseWebSocketResult {
  status: WebSocketConnectionStatus;
  isConnected: boolean;
  connect: () => void;
  disconnect: () => void;
  reconnect: () => void;
  sendEvent: (event: OutgoingWebSocketEvent) => boolean;
  sendMessage: (message: string, metadata?: Record<string, unknown>) => boolean;
}

function toStableKey(input: unknown): string {
  if (input === undefined) return "";
  if (input === null) return "null";

  try {
    return JSON.stringify(input, Object.keys(input as object).sort());
  } catch {
    return "unstable";
  }
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketResult {
  const {
    sessionId: providedSessionId,
    autoConnect = true,
    path,
    wsBaseUrl,
    queryParams,
    token,
    reconnect,
    onEvent,
    onStatusChange
  } = options;

  const sessionIdFromStore = useSessionStore((state) => state.sessionId);
  const effectiveSessionId = providedSessionId ?? sessionIdFromStore;

  const [status, setStatus] = useState<WebSocketConnectionStatus>("idle");
  const managerRef = useRef<WebSocketManager | null>(null);
  const onEventRef = useRef(onEvent);
  const onStatusChangeRef = useRef(onStatusChange);

  onEventRef.current = onEvent;
  onStatusChangeRef.current = onStatusChange;

  const queryParamsKey = useMemo(() => toStableKey(queryParams), [queryParams]);
  const reconnectKey = useMemo(() => toStableKey(reconnect), [reconnect]);

  useEffect(() => {
    const currentManager = managerRef.current;
    currentManager?.disconnect(1000, "session_change");
    managerRef.current = null;

    if (!effectiveSessionId) {
      setStatus("idle");
      return;
    }

    const manager = new WebSocketManager({
      sessionId: effectiveSessionId,
      path,
      wsBaseUrl,
      queryParams,
      token,
      reconnect,
      onReconnectScheduled: ({ attempt, maxAttempts, delayMs }) => {
        useConnectionStore.getState().markRetryScheduled(attempt, maxAttempts, delayMs);
      },
      onMessage: (event) => {
        handleWebSocketEvent(event);
        onEventRef.current?.(event);
      },
      onStatusChange: (nextStatus) => {
        const connectionStore = useConnectionStore.getState();
        connectionStore.setStatus(nextStatus);
        if (nextStatus === "connected") {
          if (connectionStore.statusModel.wasEverConnected) {
            connectionStore.markRecovered();
          } else {
            connectionStore.markConnected();
          }
        } else if (nextStatus === "disconnected") {
          connectionStore.markDisconnected();
        }
        setStatus(nextStatus);
        onStatusChangeRef.current?.(nextStatus);
      },
      onOpen: () => {
        useConnectionStore.getState().markConnected();
        useUiStore.getState().clearError();
      },
      onError: (error) => {
        const message = error instanceof Error ? error.message : "WebSocket connection error";
        useConnectionStore.getState().setConnectionError(message);
        useUiStore.getState().setError({
          message,
          code: "WS_CONNECTION_ERROR",
          source: "network"
        });
      },
      onClose: () => {
        const streamingState = useMessageStreamingStore.getState();
        if (streamingState.activeMessageId && streamingState.lifecycle !== "completed" && streamingState.lifecycle !== "failed") {
          streamingState.markInterrupted(streamingState.activeMessageId, "connection_closed");
        } else {
          streamingState.markIdle();
        }
        useConnectionStore.getState().markDisconnected("connection_closed");
        useUiStore.getState().setStreaming(false);
        useUiStore.getState().setTyping(false);
      }
    });

    managerRef.current = manager;
    setStatus(manager.getStatus());
    if (autoConnect) {
      manager.connect();
    }

    return () => {
      manager.disconnect(1000, "hook_cleanup");
      if (managerRef.current === manager) {
        managerRef.current = null;
      }
    };
  }, [
    autoConnect,
    effectiveSessionId,
    path,
    queryParamsKey,
    reconnectKey,
    token,
    wsBaseUrl
  ]);

  const connect = useCallback(() => {
    if (!managerRef.current) return;
    managerRef.current.connect();
  }, []);

  const disconnect = useCallback(() => {
    managerRef.current?.disconnect(1000, "hook_disconnect");
    setStatus("disconnected");
  }, []);

  const reconnectSocket = useCallback(() => {
    managerRef.current?.reconnectNow();
  }, []);

  const sendEvent = useCallback((event: OutgoingWebSocketEvent) => {
    return managerRef.current?.send(event) ?? false;
  }, []);

  const sendMessage = useCallback(
    (message: string, metadata?: Record<string, unknown>) => {
      const sessionId = effectiveSessionId ?? undefined;
      if (!message || !sessionId) return false;

      return sendEvent({
        type: "user_message",
        sessionId,
        payload: {
          message,
          sessionId,
          metadata
        }
      });
    },
    [effectiveSessionId, sendEvent]
  );

  return {
    status,
    isConnected: status === "connected",
    connect,
    disconnect,
    reconnect: reconnectSocket,
    sendEvent,
    sendMessage
  };
}
