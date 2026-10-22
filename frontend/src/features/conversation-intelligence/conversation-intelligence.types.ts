export type ConfidenceLevelLabel = "Low" | "Moderate" | "High" | "Unknown";

export type TrustDisplayLevel = "strong" | "caution" | "low" | "unknown";

export type FunnelProgressVisualState = "not_started" | "in_progress" | "advanced";

export type InsightSeverity = "info" | "warning" | "critical";

export interface SessionInsightDisplayItem {
  id: string;
  title: string;
  description: string;
  severity: InsightSeverity;
}

export interface IntelligenceWidgetVisibility {
  personaBadge: boolean;
  trustScoreIndicator: boolean;
  funnelStageProgress: boolean;
  responseConfidenceIndicator: boolean;
  onboardingGuidanceWidget: boolean;
  sessionInsightsList: boolean;
  contextualAssistantPanel: boolean;
}

export interface ConversationIntelligenceDisplayState {
  persona: import("@/types").PersonaType | null;
  confidence: number | null;
  trustScore: number | null;
  funnelStage: import("@/types").FunnelStage | null;
  sessionInsights: SessionInsightDisplayItem[];
  contextualHints: string[];
  visibility: IntelligenceWidgetVisibility;
}
