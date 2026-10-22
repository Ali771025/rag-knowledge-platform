import { useMemo } from "react";
import { Skeleton } from "@/components/ui";
import { dsFeedback, dsTypography } from "@/design-system";
import { useAnalytics, useOnboardingWorkflow } from "@/hooks";
import {
  getOnboardingWorkflowStageLabel,
  getOnboardingWorkflowStatusLabel,
  type NextBestActionKind
} from "@/features/onboarding";
import { AdaptivePromptChips } from "./adaptive-prompt-chips";
import { ConversationSummaryCard } from "./conversation-summary-card";
import { NextBestActionCard } from "./next-best-action-card";
import { OnboardingTimeline } from "./onboarding-timeline";
import { SessionResumeBanner } from "./session-resume-banner";
import { WorkflowContextCard } from "./workflow-context-card";

function WorkflowLoadingState() {
  return (
    <div className="space-y-2" aria-hidden="true">
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
      <Skeleton className="h-12 w-full" />
    </div>
  );
}

function getStatusTone(status: string) {
  if (status === "failed") return dsFeedback.variantClass.error;
  if (status === "blocked" || status === "paused") return dsFeedback.variantClass.warning;
  return dsFeedback.variantClass.info;
}

export function WorkflowPanel() {
  const workflow = useOnboardingWorkflow();
  const { trackCtaClicked } = useAnalytics();
  const showExtendedContext =
    workflow.summaryAvailable ||
    workflow.resumable ||
    workflow.visibleAdaptivePrompts.length > 0 ||
    workflow.visibleWorkflowCards.length > 0 ||
    workflow.context.messageCount > 0;

  const headerNote = useMemo(() => {
    const parts = [getOnboardingWorkflowStageLabel(workflow.stage), getOnboardingWorkflowStatusLabel(workflow.status)];
    if (workflow.context.messageCount > 0) {
      parts.push(`${workflow.context.messageCount} messages`);
    }
    return parts.join(" · ");
  }, [workflow.context.messageCount, workflow.stage, workflow.status]);

  const handleActionSelect = (action: { id: string; kind: NextBestActionKind; label: string }, position: number) => {
    trackCtaClicked(action.id, action.kind, position);
  };

  const handlePromptSelect = (promptId: string, promptKind: NextBestActionKind | string, position: number) => {
    trackCtaClicked(promptId, promptKind, position);
  };

  const handleResumeSelect = (sessionId: string, status: string) => {
    trackCtaClicked(sessionId, status, 0);
  };

  return (
    <aside className="rounded-2xl border border-border/80 bg-muted/20 p-3" aria-label="Workflow panel" role="complementary">
      <div className="mb-3">
        <p className={dsTypography.caption}>Workflow</p>
        <p className={dsTypography.secondary}>{headerNote}</p>
      </div>

      <div className="space-y-3">
        {!workflow.isReady ? (
          <div className={`rounded-2xl border px-3 py-2 text-sm ${getStatusTone(workflow.status)}`} role="status" aria-live="polite">
            {workflow.status === "failed" ? "Workflow data is temporarily unavailable." : "Workflow details are still syncing."}
          </div>
        ) : null}

        <section className="rounded-2xl border border-border bg-background p-3">
          <div className="mb-2">
            <h2 className={dsTypography.cardTitle}>Timeline</h2>
            <p className={dsTypography.secondary}>A compact view of onboarding progress.</p>
          </div>
          {workflow.isReady || workflow.timeline.length > 0 ? (
            <OnboardingTimeline
              steps={workflow.timeline}
              currentStep={workflow.currentTimelineStep}
              completionPercent={workflow.timelineCompletionPercent}
              isLoading={!workflow.isReady && workflow.timeline.length === 0}
            />
          ) : (
            <WorkflowLoadingState />
          )}
        </section>

        <section className="rounded-2xl border border-border bg-background p-3">
          <div className="mb-2">
            <h2 className={dsTypography.cardTitle}>Next best actions</h2>
            <p className={dsTypography.secondary}>Small actions that keep the conversation moving.</p>
          </div>
          {workflow.hasNextBestActions ? (
            <div className="space-y-2">
              {workflow.nextBestActions.slice(0, 3).map((action, index) => (
                <NextBestActionCard key={action.id} action={action} position={index} onSelect={handleActionSelect} />
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">No immediate actions are available yet.</p>
          )}
        </section>

        <section className="rounded-2xl border border-border bg-background p-3">
          <div className="mb-2">
            <h2 className={dsTypography.cardTitle}>Session resume</h2>
            <p className={dsTypography.secondary}>Continue where you left off if a session is available.</p>
          </div>
          <SessionResumeBanner
            sessionResume={workflow.sessionResume}
            onResume={(sessionResume) => handleResumeSelect(sessionResume.sessionId || "resume-session", sessionResume.status)}
          />
        </section>

        <section className="rounded-2xl border border-border bg-background p-3">
          <div className="mb-2">
            <h2 className={dsTypography.cardTitle}>Adaptive prompts</h2>
            <p className={dsTypography.secondary}>Light suggestions that can help you add context.</p>
          </div>
          <AdaptivePromptChips
            prompts={workflow.visibleAdaptivePrompts}
            onPromptSelect={(prompt, position) => handlePromptSelect(prompt.id, prompt.kind, position)}
          />
        </section>

        {showExtendedContext ? (
          <section className="rounded-2xl border border-border bg-background p-3">
            <div className="mb-2">
              <h2 className={dsTypography.cardTitle}>Conversation summary</h2>
              <p className={dsTypography.secondary}>A short memory of the current conversation.</p>
            </div>
            <ConversationSummaryCard summary={workflow.conversationSummary} />
          </section>
        ) : null}

        {showExtendedContext ? (
          <section className="rounded-2xl border border-border bg-background p-3">
            <div className="mb-2">
              <h2 className={dsTypography.cardTitle}>Context cards</h2>
              <p className={dsTypography.secondary}>Compact cards for supporting workflow context.</p>
            </div>
            {workflow.visibleWorkflowCards.length > 0 ? (
              <div className="space-y-2">
                {workflow.visibleWorkflowCards.map((card) => (
                  <WorkflowContextCard
                    key={card.id}
                    card={card}
                    onActionSelect={(label, _value, position) => handleActionSelect({ id: label, kind: "link", label }, position)}
                  />
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No contextual cards yet.</p>
            )}
          </section>
        ) : null}
      </div>
    </aside>
  );
}
