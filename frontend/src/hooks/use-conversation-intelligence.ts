import { useMemo } from "react";
import type { SessionInsightDisplayItem } from "@/features/conversation-intelligence";
import { useChatStore, useSessionStore, useUiStore } from "@/state";
import {
  getDefaultIntelligenceWidgetVisibility,
  getFunnelProgressVisualState,
  getTrustDisplayLevel,
  type ConversationIntelligenceDisplayState
} from "@/features/conversation-intelligence";

function buildSessionInsights(params: {
  persona: ReturnType<typeof useSessionStore.getState>["persona"];
  confidence: number | null;
  trustScore: number | null;
  funnelStage: ReturnType<typeof useSessionStore.getState>["funnelStage"];
  messageCount: number;
  hasError: boolean;
}): SessionInsightDisplayItem[] {
  const insights: SessionInsightDisplayItem[] = [];

  if (params.messageCount > 0) {
    insights.push({
      id: "insight-conversation-active",
      title: "Conversation active",
      description: `You have ${params.messageCount} message${params.messageCount > 1 ? "s" : ""} so far.`,
      severity: "info"
    });
  }

  if (params.persona !== "UNKNOWN") {
    insights.push({
      id: "insight-persona-available",
      title: "Persona detected",
      description: "Guidance can adapt to your communication style.",
      severity: "info"
    });
  }

  if (params.confidence !== null && params.confidence < 0.4) {
    insights.push({
      id: "insight-confidence-low",
      title: "Clarity opportunity",
      description: "A bit more detail can improve response confidence.",
      severity: "warning"
    });
  }

  if (params.trustScore !== null && params.trustScore < 30) {
    insights.push({
      id: "insight-trust-low",
      title: "Trust still early",
      description: "Short clarifying exchanges can build confidence steadily.",
      severity: "warning"
    });
  }

  if (params.hasError) {
    insights.push({
      id: "insight-temporary-error",
      title: "Temporary issue",
      description: "You can continue once the connection stabilizes.",
      severity: "critical"
    });
  }

  return insights;
}

function buildContextualHints(params: {
  isStreaming: boolean;
  trustScore: number | null;
  funnelStage: ReturnType<typeof useSessionStore.getState>["funnelStage"];
  hasError: boolean;
}): string[] {
  if (params.hasError) {
    return ["Connection is temporarily unstable. You can retry in a moment."];
  }

  const hints: string[] = [];

  if (params.isStreaming) {
    hints.push("The assistant is currently responding.");
  }

  const trustLevel = getTrustDisplayLevel(params.trustScore);
  if (trustLevel === "caution" || trustLevel === "low") {
    hints.push("A single focused follow-up can improve guidance quality.");
  }

  const funnelVisualState = getFunnelProgressVisualState(params.funnelStage);
  if (funnelVisualState === "not_started") {
    hints.push("Share your main goal to kick off personalized onboarding.");
  }

  if (funnelVisualState === "advanced") {
    hints.push("You are near action stage. Confirm details before proceeding.");
  }

  return hints;
}

export function useConversationIntelligence(): ConversationIntelligenceDisplayState {
  const persona = useSessionStore((state) => state.persona);
  const confidence = useSessionStore((state) => state.confidence);
  const trustScore = useSessionStore((state) => state.trustScore);
  const funnelStage = useSessionStore((state) => state.funnelStage);

  const isStreaming = useUiStore((state) => state.isStreaming);
  const hasError = useUiStore((state) => state.error !== null);

  const messageCount = useChatStore((state) => state.messages.length);

  return useMemo(() => {
    const visibility = getDefaultIntelligenceWidgetVisibility();
    const hasPersona = persona !== "UNKNOWN";
    const hasConfidence = confidence !== null;
    const hasTrustScore = trustScore !== null;
    const hasAdvancedStage = funnelStage !== "ENTRY";

    const sessionInsights = buildSessionInsights({
      persona,
      confidence,
      trustScore,
      funnelStage,
      messageCount,
      hasError
    });

    const contextualHints = buildContextualHints({
      isStreaming,
      trustScore,
      funnelStage,
      hasError
    });

    visibility.personaBadge = hasPersona;
    visibility.responseConfidenceIndicator = hasConfidence;
    visibility.trustScoreIndicator = hasTrustScore;
    visibility.funnelStageProgress = hasAdvancedStage;
    visibility.sessionInsightsList = sessionInsights.length > 0;
    visibility.contextualAssistantPanel = contextualHints.length > 0;

    return {
      persona,
      confidence,
      trustScore,
      funnelStage,
      sessionInsights,
      contextualHints,
      visibility
    };
  }, [confidence, funnelStage, hasError, isStreaming, messageCount, persona, trustScore]);
}
