export type AgentEntryContext = "invite-onboarding" | "post-registration" | "returning-user";

export interface AgentEntrySignals {
  inviteToken: string | null;
  isAuthenticated: boolean;
  activationStatus: "unknown" | "active" | "inactive";
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
  hasConversationHistory: boolean;
}
