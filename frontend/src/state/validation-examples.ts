import type { AgentMessage, SessionStateSnapshot } from "@/types";
import { initialChatState, useChatStore } from "./chat-store";
import { initialSessionState, useSessionStore } from "./session-store";
import { initialUiState, useUiStore } from "./ui-store";

function assertState(condition: boolean, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

export function validateChatStoreUsage(): void {
  useChatStore.setState(initialChatState);

  const userMessage: AgentMessage = {
    id: "msg-user-1",
    role: "user",
    text: "Hi",
    createdAt: new Date().toISOString()
  };

  const streamingAgentMessage: AgentMessage = {
    id: "msg-agent-1",
    role: "agent",
    text: "Hello",
    createdAt: new Date().toISOString(),
    isStreaming: true
  };

  const chatStore = useChatStore.getState();
  chatStore.addMessage(userMessage);
  chatStore.addMessage(streamingAgentMessage);
  chatStore.appendToStreamingMessage("msg-agent-1", " there");

  const updatedStreamingMessage = useChatStore
    .getState()
    .messages.find((message) => message.id === "msg-agent-1");

  assertState(updatedStreamingMessage?.text === "Hello there", "Streaming message chunk append failed");

  chatStore.updateStreamingMessage("msg-agent-1", { isStreaming: false });
  assertState(useChatStore.getState().messages.length === 2, "Unexpected message count after stream update");

  chatStore.clearMessages();
  assertState(useChatStore.getState().messages.length === 0, "clearMessages did not reset the timeline");
}

export function validateSessionStoreUsage(): void {
  useSessionStore.setState(initialSessionState);

  const sessionSnapshot: SessionStateSnapshot = {
    sessionId: "session-001",
    persona: "SAVER",
    confidence: 0.82,
    trustScore: 41,
    funnelStage: "EXPLORATION",
    suggestedActions: [
      {
        id: "action-1",
        label: "Show options",
        kind: "primary"
      }
    ]
  };

  const sessionStore = useSessionStore.getState();
  sessionStore.setSession(sessionSnapshot);
  sessionStore.updatePersona("HUNTER", 0.91);
  sessionStore.updateStage("TRUST");
  sessionStore.patchSession({ trustScore: 65, funnelStage: "OPPORTUNITY" });

  const nextState = useSessionStore.getState();
  assertState(nextState.persona === "HUNTER", "Persona update failed");
  assertState(nextState.funnelStage === "OPPORTUNITY", "Funnel stage patch failed");
  assertState(nextState.trustScore === 65, "Trust score patch failed");
}

export function validateUiStoreUsage(): void {
  useUiStore.setState(initialUiState);

  const uiStore = useUiStore.getState();
  uiStore.setTyping(true);
  uiStore.setStreaming(true);
  uiStore.setError({
    message: "Temporary network issue",
    code: "NETWORK_TEMP",
    source: "network"
  });

  const erroredState = useUiStore.getState();
  assertState(erroredState.isTyping, "Typing flag was not set");
  assertState(erroredState.isStreaming, "Streaming flag was not set");
  assertState(erroredState.error?.code === "NETWORK_TEMP", "UI error was not set");

  uiStore.resetUiState();

  const resetState = useUiStore.getState();
  assertState(!resetState.isTyping, "Typing flag was not reset");
  assertState(!resetState.isStreaming, "Streaming flag was not reset");
  assertState(resetState.error === null, "UI error was not reset");
}

export function runAllStateValidationExamples(): void {
  validateChatStoreUsage();
  validateSessionStoreUsage();
  validateUiStoreUsage();
}
