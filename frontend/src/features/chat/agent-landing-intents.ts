import type { AgentLandingCardIntent } from "./agent-landing-cards.types";

export function intentToPrompt(intent: AgentLandingCardIntent): string {
  switch (intent) {
    case "status_next_action":
      return "status_next_action";
    case "microtasks":
      return "microtasks";
    case "security_risk":
      return "security_risk";
    case "investing_strategy":
      return "investing_strategy";
    case "referral_growth":
      return "referral_growth";
    case "ecosystem_guide":
      return "ecosystem_guide";
    case "help_troubleshooting":
      return "help_troubleshooting";
    default: {
      const fallback: never = intent;
      return fallback;
    }
  }
}
