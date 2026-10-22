import {
  Activity,
  BadgeDollarSign,
  BookOpen,
  CircleHelp,
  ShieldCheck,
  TrendingUp,
  UsersRound
} from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import type { AgentLandingCardConfig } from "./agent-landing-cards.types";

export const AGENT_LANDING_CARD_CONFIGS: AgentLandingCardConfig[] = [
  {
    key: "myStatusNextBestAction",
    titleI18nKey: "myStatusNextBestAction",
    descriptionI18nKey: "myStatusNextBestAction",
    icon: Activity,
    actionIntent: "status_next_action",
    requiresAuth: true,
    route: appRoutes.dashboard
  },
  {
    key: "earnViaMicrotasks",
    titleI18nKey: "earnViaMicrotasks",
    descriptionI18nKey: "earnViaMicrotasks",
    icon: BadgeDollarSign,
    actionIntent: "microtasks",
    requiresAuth: true
  },
  {
    key: "securityRiskCheck",
    titleI18nKey: "securityRiskCheck",
    descriptionI18nKey: "securityRiskCheck",
    icon: ShieldCheck,
    actionIntent: "security_risk",
    requiresAuth: true,
    requiresWallet: true
  },
  {
    key: "investingStrategy",
    titleI18nKey: "investingStrategy",
    descriptionI18nKey: "investingStrategy",
    icon: TrendingUp,
    actionIntent: "investing_strategy",
    requiresAuth: true
  },
  {
    key: "referralTeamGrowth",
    titleI18nKey: "referralTeamGrowth",
    descriptionI18nKey: "referralTeamGrowth",
    icon: UsersRound,
    actionIntent: "referral_growth",
    requiresAuth: true,
    route: appRoutes.referral
  },
  {
    key: "qora101EcosystemGuide",
    titleI18nKey: "qora101EcosystemGuide",
    descriptionI18nKey: "qora101EcosystemGuide",
    icon: BookOpen,
    actionIntent: "ecosystem_guide",
    requiresAuth: false
  },
  {
    key: "helpTroubleshooting",
    titleI18nKey: "helpTroubleshooting",
    descriptionI18nKey: "helpTroubleshooting",
    icon: CircleHelp,
    actionIntent: "help_troubleshooting",
    requiresAuth: false
  }
];
