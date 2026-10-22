import type { AgentEntryContext, AgentEntrySignals } from "./agent-landing-entry.types";

function normalizeToken(value: string | null): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function isOnboardingComplete(signals: AgentEntrySignals): boolean {
  return (
    signals.activationStatus === "active" &&
    signals.initialInteractionCompleted &&
    signals.registrationCompleted &&
    signals.firstTasksReceived
  );
}

export function resolveAgentEntryContext(signals: AgentEntrySignals): AgentEntryContext {
  const inviteToken = normalizeToken(signals.inviteToken);
  const onboardingComplete = isOnboardingComplete(signals);

  if (inviteToken && !onboardingComplete) {
    return "invite-onboarding";
  }

  if (onboardingComplete) {
    if (signals.hasConversationHistory) {
      return "returning-user";
    }
    return "post-registration";
  }

  if (!signals.isAuthenticated || signals.activationStatus !== "active") {
    return "invite-onboarding";
  }

  if (!signals.initialInteractionCompleted || !signals.registrationCompleted || !signals.firstTasksReceived) {
    return "invite-onboarding";
  }

  return signals.hasConversationHistory ? "returning-user" : "post-registration";
}
