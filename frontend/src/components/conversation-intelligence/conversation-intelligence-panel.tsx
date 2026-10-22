import type { FunnelStage, PersonaType } from "@/types";
import { getDefaultIntelligenceWidgetVisibility } from "@/features/conversation-intelligence";
import type { SessionInsightDisplayItem } from "@/features/conversation-intelligence";
import { dsTypography } from "@/design-system";
import { useAnalytics } from "@/hooks/use-analytics";
import { ContextualAssistantPanel } from "./contextual-assistant-panel";
import { FunnelStageProgress } from "./funnel-stage-progress";
import { OnboardingGuidanceWidget } from "./onboarding-guidance-widget";
import { PersonaBadge } from "./persona-badge";
import { ResponseConfidenceIndicator } from "./response-confidence-indicator";
import { SessionInsightsList } from "./session-insights-list";
import { TrustScoreIndicator } from "./trust-score-indicator";

interface ConversationIntelligencePanelProps {
  persona?: PersonaType | null;
  confidence?: number | null;
  trustScore?: number | null;
  funnelStage?: FunnelStage | null;
  sessionInsights?: SessionInsightDisplayItem[];
  contextualHints?: string[];
  visibility?: Partial<ReturnType<typeof getDefaultIntelligenceWidgetVisibility>>;
}

export function ConversationIntelligencePanel({
  persona = null,
  confidence = null,
  trustScore = null,
  funnelStage = null,
  sessionInsights = [],
  contextualHints = [],
  visibility: visibilityOverrides
}: ConversationIntelligencePanelProps) {
  const { trackInfoExpanded } = useAnalytics();

  const visibility = {
    ...getDefaultIntelligenceWidgetVisibility(),
    ...visibilityOverrides
  };

  return (
    <aside className="rounded-2xl border border-border/80 bg-muted/25 p-2.5 sm:p-3" aria-label="Conversation intelligence panel">
      <div className="mb-2">
        <p className={dsTypography.caption}>Conversation intelligence</p>
        <p className={dsTypography.secondary}>Light context to support the ongoing conversation.</p>
      </div>

      <div className="grid gap-2">
        {visibility.personaBadge ? <PersonaBadge persona={persona} /> : null}
        {visibility.responseConfidenceIndicator ? <ResponseConfidenceIndicator confidence={confidence} /> : null}

        {visibility.trustScoreIndicator ? <TrustScoreIndicator trustScore={trustScore} /> : null}

        {visibility.funnelStageProgress ? <FunnelStageProgress stage={funnelStage} /> : null}

        {visibility.onboardingGuidanceWidget ? <OnboardingGuidanceWidget stage={funnelStage} persona={persona} /> : null}

        {visibility.sessionInsightsList ? <SessionInsightsList insights={sessionInsights} /> : null}

        {visibility.contextualAssistantPanel ? (
          <ContextualAssistantPanel
            hints={contextualHints}
            onHintExpanded={(hintId, expanded) => trackInfoExpanded(hintId, expanded, "intelligence")}
          />
        ) : null}
      </div>
    </aside>
  );
}
