export const MESSAGE_STREAM_LIFECYCLE_STATES = [
  "idle",
  "starting",
  "streaming",
  "paused",
  "completed",
  "interrupted",
  "failed"
] as const;

export type MessageStreamLifecycleState = (typeof MESSAGE_STREAM_LIFECYCLE_STATES)[number];

export const MESSAGE_STREAM_ACTIVE_STATES = ["starting", "streaming", "paused"] as const;
export type MessageStreamActiveState = (typeof MESSAGE_STREAM_ACTIVE_STATES)[number];

export const MESSAGE_STREAM_TERMINAL_STATES = ["completed", "interrupted", "failed"] as const;
export type MessageStreamTerminalState = (typeof MESSAGE_STREAM_TERMINAL_STATES)[number];

export function isMessageStreamLifecycleState(value: unknown): value is MessageStreamLifecycleState {
  return typeof value === "string" && MESSAGE_STREAM_LIFECYCLE_STATES.includes(value as MessageStreamLifecycleState);
}

export function isMessageStreamActiveState(value: MessageStreamLifecycleState): value is MessageStreamActiveState {
  return MESSAGE_STREAM_ACTIVE_STATES.includes(value as MessageStreamActiveState);
}

export function isMessageStreamTerminalState(value: MessageStreamLifecycleState): value is MessageStreamTerminalState {
  return MESSAGE_STREAM_TERMINAL_STATES.includes(value as MessageStreamTerminalState);
}
