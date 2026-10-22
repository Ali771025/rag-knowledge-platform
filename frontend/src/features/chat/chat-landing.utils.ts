import type { ChatEligibilityState } from "./chat-landing.types";

interface NewChatGatingInput {
  isAuthenticated: boolean;
  activationStatus: "unknown" | "active" | "inactive";
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}

export function evaluateNewChatEligibility(input: NewChatGatingInput): ChatEligibilityState {
  if (!input.isAuthenticated) {
    return { canStartNewChat: false, reasonKey: "requires_auth" };
  }

  if (input.activationStatus !== "active") {
    return { canStartNewChat: false, reasonKey: "requires_activation" };
  }

  if (!input.initialInteractionCompleted) {
    return { canStartNewChat: false, reasonKey: "requires_initial_interaction" };
  }

  if (!input.registrationCompleted) {
    return { canStartNewChat: false, reasonKey: "requires_registration" };
  }

  if (!input.firstTasksReceived) {
    return { canStartNewChat: false, reasonKey: "requires_first_tasks" };
  }

  return { canStartNewChat: true, reasonKey: null };
}
