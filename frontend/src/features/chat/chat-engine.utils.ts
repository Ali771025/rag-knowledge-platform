import type { AgentMessage, MessageRole, SuggestedAction } from "@/types";
import type { MessageAlignment, MessageVisualVariant } from "./chat-engine.types";
import { MAX_SUGGESTED_ACTIONS } from "./chat-engine.constants";

export function getMessageAlignment(role: MessageRole): MessageAlignment {
  return role === "user" ? "end" : "start";
}

export function getMessageVisualVariant(role: MessageRole): MessageVisualVariant {
  if (role === "user") return "user";
  if (role === "system") return "system";
  return "agent";
}

export function getSuggestedActionsPreview(
  actions: SuggestedAction[],
  maxActions: number = MAX_SUGGESTED_ACTIONS
): SuggestedAction[] {
  return actions.slice(0, Math.max(0, maxActions));
}

export function isAgentMessage(message: AgentMessage): boolean {
  return message.role === "agent";
}
