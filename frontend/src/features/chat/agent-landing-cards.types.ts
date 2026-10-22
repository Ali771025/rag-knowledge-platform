import type { LucideIcon } from "lucide-react";

export type AgentLandingCardKey =
  | "myStatusNextBestAction"
  | "earnViaMicrotasks"
  | "securityRiskCheck"
  | "investingStrategy"
  | "referralTeamGrowth"
  | "qora101EcosystemGuide"
  | "helpTroubleshooting";

export type AgentLandingCardIntent =
  | "status_next_action"
  | "microtasks"
  | "security_risk"
  | "investing_strategy"
  | "referral_growth"
  | "ecosystem_guide"
  | "help_troubleshooting";

export interface AgentLandingCardConfig {
  key: AgentLandingCardKey;
  titleI18nKey: AgentLandingCardKey;
  descriptionI18nKey: AgentLandingCardKey;
  icon: LucideIcon;
  actionIntent: AgentLandingCardIntent;
  requiresAuth?: boolean;
  requiresWallet?: boolean;
  route?: string;
}
