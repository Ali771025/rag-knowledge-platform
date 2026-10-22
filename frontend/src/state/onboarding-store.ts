import { create } from "zustand";
import type { OnboardingWorkflowSnapshotInput } from "@/features/onboarding";
import { normalizeOnboardingWorkflowSnapshot, type OnboardingWorkflowViewModel } from "@/features/onboarding";

export interface OnboardingState {
  workflow: OnboardingWorkflowViewModel;
}

export interface OnboardingActions {
  setWorkflow: (input: OnboardingWorkflowSnapshotInput) => void;
  patchWorkflow: (partial: Partial<OnboardingWorkflowSnapshotInput>) => void;
  resetWorkflow: () => void;
}

export type OnboardingStore = OnboardingState & OnboardingActions;

const emptyWorkflowSnapshot: OnboardingWorkflowSnapshotInput = {};

export const initialOnboardingState: OnboardingState = {
  workflow: normalizeOnboardingWorkflowSnapshot(emptyWorkflowSnapshot)
};

export const useOnboardingStore = create<OnboardingStore>((set) => ({
  ...initialOnboardingState,
  setWorkflow: (input) => {
    set({
      workflow: normalizeOnboardingWorkflowSnapshot(input)
    });
  },
  patchWorkflow: (partial) => {
    set((state) => {
      const mergedInput: OnboardingWorkflowSnapshotInput = {
        stage: partial.stage ?? state.workflow.stage,
        status: partial.status ?? state.workflow.status,
        timeline: partial.timeline ?? state.workflow.timeline,
        nextBestActions: partial.nextBestActions ?? state.workflow.nextBestActions,
        sessionResume: partial.sessionResume ?? state.workflow.sessionResume,
        adaptivePrompts: partial.adaptivePrompts ?? state.workflow.adaptivePrompts,
        conversationSummary: partial.conversationSummary ?? state.workflow.conversationSummary,
        workflowCards: partial.workflowCards ?? state.workflow.workflowCards,
        metadata: partial.metadata ?? state.workflow.metadata
      };

      return {
        workflow: normalizeOnboardingWorkflowSnapshot(mergedInput)
      };
    });
  },
  resetWorkflow: () => {
    set(initialOnboardingState);
  }
}));
