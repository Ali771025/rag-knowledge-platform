export { WebSocketManager } from "./websocket-manager";
export { handleWebSocketEvent } from "./websocket-handlers";
export { runWebSocketValidationExamples } from "./validation-examples";
export { buildConnectionStatusModel } from "./websocket-connection.utils";

export {
  INCOMING_WS_EVENT_TYPES,
  OUTGOING_WS_EVENT_TYPES,
  isIncomingWebSocketEvent,
  isIncomingWebSocketEventType,
  isOutgoingWebSocketEvent,
  isOutgoingWebSocketEventType
} from "./websocket-events";

export type {
  ConnectionBannerState,
  ConnectionHealthState,
  ConnectionRecoveryState,
  ConnectionStatusModel
} from "./websocket-connection.types";

export type {
  ConnectionAckEvent,
  ConnectionAckPayload,
  ErrorEvent,
  ErrorEventPayload,
  IncomingWebSocketEvent,
  IncomingWebSocketEventType,
  MessageCompleteEvent,
  MessageCompletePayload,
  MessageStreamEvent,
  MessageStreamPayload,
  OutgoingWebSocketEvent,
  OutgoingWebSocketEventType,
  PersonaUpdateEvent,
  PersonaUpdatePayload,
  PingEvent,
  PingPayload,
  SessionUpdateEvent,
  SessionUpdatePayload,
  StageUpdateEvent,
  StageUpdatePayload,
  SubscribeSessionEvent,
  SubscribeSessionPayload,
  SuggestedActionsEvent,
  SuggestedActionsPayload,
  UserMessageEvent,
  UserMessagePayload
} from "./websocket-events";

export type { ReconnectOptions, WebSocketConnectionStatus, WebSocketManagerOptions } from "./websocket-manager";
