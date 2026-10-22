import { WebSocketManager } from "./websocket-manager";
import { isIncomingWebSocketEvent } from "./websocket-events";

function assertCondition(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

export function validateWebSocketEventGuardExamples(): void {
  const validEvent = {
    type: "message_stream",
    payload: {
      messageId: "stream-1",
      chunk: "hello"
    }
  };

  const invalidEvent = {
    type: "message_stream"
  };

  assertCondition(isIncomingWebSocketEvent(validEvent), "Expected valid event to pass type guard");
  assertCondition(!isIncomingWebSocketEvent(invalidEvent), "Expected invalid event to fail type guard");
}

export function validateReconnectDefaultsExample(): void {
  const manager = new WebSocketManager({
    sessionId: "session-validation",
    reconnect: {
      maxAttempts: 3,
      baseDelayMs: 500,
      maxDelayMs: 2_000
    }
  });

  assertCondition(manager.getStatus() === "idle", "Manager should initialize in idle status");
  assertCondition(manager.getReconnectAttempts() === 0, "Reconnect attempts should start at zero");
}

export function runWebSocketValidationExamples(): void {
  validateWebSocketEventGuardExamples();
  validateReconnectDefaultsExample();
}
