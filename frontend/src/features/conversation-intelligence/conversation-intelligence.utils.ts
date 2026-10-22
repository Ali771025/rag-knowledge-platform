import type { FunnelStage, PersonaType } from "@/types";
import { FUNNEL_STAGES } from "@/types";
import {
  CONFIDENCE_HIGH_THRESHOLD,
  CONFIDENCE_LOW_THRESHOLD,
  MAX_VISIBLE_SESSION_INSIGHTS,
  TRUST_SCORE_WARNING_THRESHOLD
} from "./conversation-intelligence.constants";
import type {
  ConfidenceLevelLabel,
  FunnelProgressVisualState,
  IntelligenceWidgetVisibility,
  TrustDisplayLevel
} from "./conversation-intelligence.types";

export function getConfidenceLabel(value: number | null | undefined): ConfidenceLevelLabel {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "Unknown";
  }

  if (value < CONFIDENCE_LOW_THRESHOLD) return "Low";
  if (value >= CONFIDENCE_HIGH_THRESHOLD) return "High";
  return "Moderate";
}

export function getTrustDisplayLevel(value: number | null | undefined): TrustDisplayLevel {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "unknown";
  }

  if (value < TRUST_SCORE_WARNING_THRESHOLD * 0.6) return "low";
  if (value < TRUST_SCORE_WARNING_THRESHOLD) return "caution";
  return "strong";
}

export function getTrustLabel(value: number | null | undefined): string {
  const level = getTrustDisplayLevel(value);

  if (level === "strong") return "Solid connection";
  if (level === "caution") return "Building trust";
  if (level === "low") return "Early connection";
  return "Not enough context yet";
}

export function getFunnelStageLabel(stage: FunnelStage | null | undefined): string {
  if (!stage) return "Not started";

  const labels: Record<FunnelStage, string> = {
    ENTRY: "Entry",
    EXPLORATION: "Exploration",
    TRUST: "Trust",
    OPPORTUNITY: "Opportunity",
    MICRO_COMMITMENT: "Micro-commitment",
    ECONOMIC_ACTION: "Economic action"
  };

  return labels[stage];
}

export function getFunnelProgressVisualState(stage: FunnelStage | null | undefined): FunnelProgressVisualState {
  if (!stage || stage === "ENTRY") return "not_started";
  if (stage === "ECONOMIC_ACTION") return "advanced";
  return "in_progress";
}

export function getFunnelStageStep(stage: FunnelStage | null | undefined): number {
  if (!stage) return 0;
  return Math.max(0, FUNNEL_STAGES.indexOf(stage) + 1);
}

export function getFunnelProgressPercent(stage: FunnelStage | null | undefined): number {
  const step = getFunnelStageStep(stage);
  if (step === 0) return 0;
  return Math.round((step / FUNNEL_STAGES.length) * 100);
}

export function clampInsightCount<T>(items: T[], maxVisible: number = MAX_VISIBLE_SESSION_INSIGHTS): T[] {
  return items.slice(0, Math.max(0, maxVisible));
}

export function getPersonaLabel(persona: PersonaType | null | undefined): string {
  if (!persona || persona === "UNKNOWN") return "Profiling in progress";

  const labels: Record<Exclude<PersonaType, "UNKNOWN">, string> = {
    SAVER: "Saver",
    HUNTER: "Hunter",
    PLAYER: "Player",
    ARCHITECT: "Architect"
  };

  return labels[persona];
}

export function toPercent(value: number | null | undefined): number | null {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return null;
  }

  if (value <= 1) {
    return Math.max(0, Math.min(100, Math.round(value * 100)));
  }

  return Math.max(0, Math.min(100, Math.round(value)));
}

export function getDefaultIntelligenceWidgetVisibility(): IntelligenceWidgetVisibility {
  return {
    personaBadge: true,
    trustScoreIndicator: true,
    funnelStageProgress: true,
    responseConfidenceIndicator: true,
    onboardingGuidanceWidget: true,
    sessionInsightsList: true,
    contextualAssistantPanel: true
  };
}
