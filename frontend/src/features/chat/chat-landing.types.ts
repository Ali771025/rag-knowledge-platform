import type { AgentMessage } from "@/types";
export type { AgentEntryContext } from "./agent-landing-entry.types";
export type { AgentLandingCardConfig, AgentLandingCardIntent, AgentLandingCardKey } from "./agent-landing-cards.types";

export interface ChatEligibilityState {
  canStartNewChat: boolean;
  reasonKey:
    | "requires_auth"
    | "requires_activation"
    | "requires_initial_interaction"
    | "requires_registration"
    | "requires_first_tasks"
    | null;
}

export interface TypedFunnelItem {
  id: string;
  label: string;
  confidence: number;
}

export type AgentLandingIconKey =
  | "audioLines"
  | "badgeCheck"
  | "bookOpen"
  | "bot"
  | "brain"
  | "cpu"
  | "history"
  | "layoutDashboard"
  | "messageCircle"
  | "mic"
  | "radio"
  | "search"
  | "shieldCheck"
  | "sparkles"
  | "stars"
  | "trophy"
  | "userPlus"
  | "userRound"
  | "wallet"
  | "waves";

export interface AgentCapabilityBadge {
  id: "rag" | "memory" | "voice" | "walletAware";
  label: string;
  icon: AgentLandingIconKey;
}

export interface AgentPromptPreset {
  id: "walletRisk" | "ecosystem" | "earning" | "continue";
  title: string;
  description: string;
  prompt: string;
  icon: AgentLandingIconKey;
}

export interface AgentNavItemConfig {
  id: "agent" | "history" | "dashboard" | "referral" | "voice" | "profile";
  to: string;
  label: string;
  ariaLabel: string;
  icon: AgentLandingIconKey;
}

export interface AgentQuickAction {
  id: "dashboard" | "history" | "referral" | "voice";
  to: string;
  label: string;
  icon: AgentLandingIconKey;
}

export interface AgentContextItem {
  id: "capabilities" | "memory" | "security";
  title: string;
  description: string;
  icon: AgentLandingIconKey;
}

export interface ChatLandingSnapshot {
  messages: AgentMessage[];
  isSubmitting: boolean;
}

export interface ChatEntryChoicePanelCopy {
  title: string;
  description: string;
  selectedTopicLabel: string;
  continueAction: string;
  startNewAction: string;
}
