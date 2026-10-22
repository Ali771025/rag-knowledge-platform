import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { HelpCircle, Sparkles, X } from "lucide-react";
import { Button } from "@/components/ui";
import { dsInteraction, dsTypography, wizardStepVariants } from "@/design-system";
import type { MessagesSchema } from "@/i18n/messages";
import type { ReferralPersonalizationProfile } from "@/services/referral";

type WizardStepKind = "single" | "multi" | "note";

type WizardStepId =
  | "inviteeRelationship"
  | "familiarityLevel"
  | "invitationReason"
  | "primaryMotivation"
  | "web3FamiliarityLevel"
  | "previousWeb3ToolExperience"
  | "readinessToTakeAction"
  | "concernsAndFrictions"
  | "previousNegativeExperience"
  | "preferredInformationStyle"
  | "suggestedEcosystemSection"
  | "conversionLikelihood"
  | "additionalNote";

interface WizardStepBase {
  id: WizardStepId;
  kind: WizardStepKind;
  required: boolean;
}

interface SingleChoiceStep extends WizardStepBase {
  kind: "single";
  options: string[];
}

interface MultiChoiceStep extends WizardStepBase {
  kind: "multi";
  options: string[];
}

interface NoteStep extends WizardStepBase {
  kind: "note";
  maxLength: number;
}

type WizardStep = SingleChoiceStep | MultiChoiceStep | NoteStep;

type SingleAnswers = Omit<ReferralPersonalizationProfile, "concernsAndFrictions" | "additionalNote">;

interface WizardAnswers extends SingleAnswers {
  concernsAndFrictions: string[];
  additionalNote: string;
}

type WizardLabels = MessagesSchema["referral"]["personalizationWizard"];

interface ReferralPersonalizationWizardProps {
  open: boolean;
  labels: WizardLabels;
  draftLabel: string;
  draftColorLabel: string;
  initialValue: ReferralPersonalizationProfile | null;
  submitting: boolean;
  onClose: () => void;
  onSubmit: (profile: ReferralPersonalizationProfile) => void;
}

const STEP_ORDER: [WizardStep, ...WizardStep[]] = [
  { id: "inviteeRelationship", kind: "single", required: true, options: ["friend", "family", "colleague", "community", "other"] },
  { id: "familiarityLevel", kind: "single", required: true, options: ["knowWell", "somewhat", "justMet", "onlineOnly", "dontKnow"] },
  { id: "invitationReason", kind: "single", required: true, options: ["learnAndEarn", "ecosystemAccess", "guidedOnboarding", "teamGrowth", "curiousExplore"] },
  { id: "primaryMotivation", kind: "single", required: true, options: ["earnRewards", "learnWeb3", "productivity", "communityStatus", "curiosity"] },
  { id: "web3FamiliarityLevel", kind: "single", required: true, options: ["newcomer", "basic", "intermediate", "advanced", "dontKnow"] },
  { id: "previousWeb3ToolExperience", kind: "single", required: true, options: ["none", "walletOnly", "defiOrNft", "daoOrGovernance", "multipleTools"] },
  { id: "readinessToTakeAction", kind: "single", required: true, options: ["readyNow", "thisWeek", "needGuidance", "researching", "unsure"] },
  { id: "concernsAndFrictions", kind: "multi", required: true, options: ["security", "fundSafety", "complexity", "timeCommitment", "fees", "privacy", "noConcerns"] },
  { id: "previousNegativeExperience", kind: "single", required: true, options: ["none", "scamAttempt", "lostFunds", "highFees", "confusingUx", "dontKnow"] },
  { id: "preferredInformationStyle", kind: "single", required: true, options: ["simpleSteps", "visualExamples", "comparisons", "dataDriven", "conversational"] },
  { id: "suggestedEcosystemSection", kind: "single", required: true, options: ["gettingStarted", "microtasks", "achievements", "walletSecurity", "community"] },
  { id: "conversionLikelihood", kind: "single", required: true, options: ["veryHigh", "high", "medium", "low", "veryLow"] },
  { id: "additionalNote", kind: "note", required: false, maxLength: 1000 },
];

const DEFAULT_WIZARD_ANSWERS: WizardAnswers = {
  inviteeRelationship: "",
  familiarityLevel: "",
  invitationReason: "",
  primaryMotivation: "",
  web3FamiliarityLevel: "",
  previousWeb3ToolExperience: "",
  readinessToTakeAction: "",
  concernsAndFrictions: [],
  previousNegativeExperience: "",
  preferredInformationStyle: "",
  suggestedEcosystemSection: "",
  conversionLikelihood: "",
  additionalNote: "",
};

function toWizardAnswers(profile: ReferralPersonalizationProfile | null): WizardAnswers {
  if (!profile) return { ...DEFAULT_WIZARD_ANSWERS };
  return {
    inviteeRelationship: profile.inviteeRelationship,
    familiarityLevel: profile.familiarityLevel,
    invitationReason: profile.invitationReason,
    primaryMotivation: profile.primaryMotivation,
    web3FamiliarityLevel: profile.web3FamiliarityLevel,
    previousWeb3ToolExperience: profile.previousWeb3ToolExperience,
    readinessToTakeAction: profile.readinessToTakeAction,
    concernsAndFrictions: [...profile.concernsAndFrictions],
    previousNegativeExperience: profile.previousNegativeExperience,
    preferredInformationStyle: profile.preferredInformationStyle,
    suggestedEcosystemSection: profile.suggestedEcosystemSection,
    conversionLikelihood: profile.conversionLikelihood,
    additionalNote: profile.additionalNote ?? "",
  };
}

function toProfile(answers: WizardAnswers): ReferralPersonalizationProfile {
  return {
    inviteeRelationship: answers.inviteeRelationship,
    familiarityLevel: answers.familiarityLevel,
    invitationReason: answers.invitationReason,
    primaryMotivation: answers.primaryMotivation,
    web3FamiliarityLevel: answers.web3FamiliarityLevel,
    previousWeb3ToolExperience: answers.previousWeb3ToolExperience,
    readinessToTakeAction: answers.readinessToTakeAction,
    concernsAndFrictions: answers.concernsAndFrictions,
    previousNegativeExperience: answers.previousNegativeExperience,
    preferredInformationStyle: answers.preferredInformationStyle,
    suggestedEcosystemSection: answers.suggestedEcosystemSection,
    conversionLikelihood: answers.conversionLikelihood,
    additionalNote: answers.additionalNote.trim() ? answers.additionalNote.trim() : null,
  };
}

function isDirty(answers: WizardAnswers): boolean {
  return Object.entries(answers).some(([key, value]) => {
    if (key === "concernsAndFrictions") return Array.isArray(value) && value.length > 0;
    if (typeof value === "string") return value.trim().length > 0;
    return false;
  });
}

function isStepAnswered(step: WizardStep, answers: WizardAnswers): boolean {
  if (step.kind === "note") return true;
  if (step.kind === "multi") return answers.concernsAndFrictions.length > 0;
  const value = answers[step.id as keyof SingleAnswers];
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeMultiSelection(next: string, current: string[]): string[] {
  if (next === "noConcerns") return ["noConcerns"];
  const withoutNoConcerns = current.filter((value) => value !== "noConcerns");
  if (withoutNoConcerns.includes(next)) {
    return withoutNoConcerns.filter((value) => value !== next);
  }
  return [...withoutNoConcerns, next];
}

function stepContent(labels: WizardLabels, step: WizardStep) {
  const item = labels.steps[step.id];
  const optionLabels =
    "options" in item
      ? Object.fromEntries(Object.entries(item.options).map(([key, value]) => [key, value]))
      : {};
  return {
    title: item.title,
    tooltip: item.tooltip,
    question: item.question,
    optionLabels,
    placeholder: "placeholder" in item ? item.placeholder : undefined,
  };
}

function stateForStep(step: WizardStep, answers: WizardAnswers): string | string[] {
  if (step.kind === "multi") return answers.concernsAndFrictions;
  if (step.kind === "note") return answers.additionalNote;
  return answers[step.id as keyof SingleAnswers];
}

export function ReferralPersonalizationWizard({
  open,
  labels,
  draftLabel,
  draftColorLabel,
  initialValue,
  submitting,
  onClose,
  onSubmit,
}: ReferralPersonalizationWizardProps) {
  const shouldReduceMotion = useReducedMotion();
  const firstInteractiveRef = useRef<HTMLButtonElement>(null);
  const [stepIndex, setStepIndex] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [answers, setAnswers] = useState<WizardAnswers>(DEFAULT_WIZARD_ANSWERS);
  const [showUnsavedConfirm, setShowUnsavedConfirm] = useState(false);
  const [validationError, setValidationError] = useState(false);

  const currentStep: WizardStep = STEP_ORDER[Math.min(stepIndex, STEP_ORDER.length - 1)] ?? STEP_ORDER[0];
  const progressLabel = `${stepIndex + 1}/${STEP_ORDER.length}`;
  const dialogTitleId = "referral-personalization-title";
  const dialogDescriptionId = "referral-personalization-description";

  useEffect(() => {
    if (!open) return;
    setStepIndex(0);
    setAnswers(toWizardAnswers(initialValue));
    setDirection(1);
    setShowUnsavedConfirm(false);
    setValidationError(false);
  }, [open, initialValue]);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const timer = window.setTimeout(() => {
      firstInteractiveRef.current?.focus();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [open, stepIndex, showUnsavedConfirm]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Tab") {
        const focusable = Array.from(
          document.querySelectorAll<HTMLElement>(
            "[data-referral-wizard] button:not([disabled]), [data-referral-wizard] textarea:not([disabled]), [data-referral-wizard] [href], [data-referral-wizard] input:not([disabled]), [data-referral-wizard] select:not([disabled])"
          )
        ).filter((item) => !item.hasAttribute("aria-hidden"));
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (!first || !last) return;
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
          return;
        }
        if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
      if (event.key === "Escape") {
        event.preventDefault();
        if (showUnsavedConfirm) {
          setShowUnsavedConfirm(false);
          return;
        }
        if (isDirty(answers)) {
          setShowUnsavedConfirm(true);
          return;
        }
        onClose();
      }
      if (event.key === "ArrowRight" && stepIndex < STEP_ORDER.length - 1 && !showUnsavedConfirm) {
        event.preventDefault();
        if (currentStep.required && !isStepAnswered(currentStep, answers)) {
          setValidationError(true);
          return;
        }
        setValidationError(false);
        setDirection(1);
        setStepIndex((prev) => prev + 1);
      }
      if (event.key === "ArrowLeft" && stepIndex > 0 && !showUnsavedConfirm) {
        event.preventDefault();
        setDirection(-1);
        setStepIndex((prev) => prev - 1);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [answers, currentStep, onClose, open, showUnsavedConfirm, stepIndex]);

  const canGoBack = stepIndex > 0;
  const isFinalStep = stepIndex === STEP_ORDER.length - 1;
  const validCurrentStep = !currentStep.required || isStepAnswered(currentStep, answers);

  const content = useMemo(() => stepContent(labels, currentStep), [currentStep, labels]);
  const currentState = stateForStep(currentStep, answers);
  const singleStep = currentStep.kind === "single" ? currentStep : null;
  const multiStep = currentStep.kind === "multi" ? currentStep : null;
  const noteStep = currentStep.kind === "note" ? currentStep : null;

  const handleRequestClose = () => {
    if (isDirty(answers)) {
      setShowUnsavedConfirm(true);
      return;
    }
    onClose();
  };

  const handleOptionSelect = (option: string) => {
    setValidationError(false);
    if (currentStep.kind === "multi") {
      setAnswers((prev) => ({
        ...prev,
        concernsAndFrictions: normalizeMultiSelection(option, prev.concernsAndFrictions),
      }));
      return;
    }
    if (currentStep.kind === "single") {
      setAnswers((prev) => ({ ...prev, [currentStep.id]: option }));
    }
  };

  const handleNext = () => {
    if (!validCurrentStep) {
      setValidationError(true);
      return;
    }
    setValidationError(false);
    if (isFinalStep) {
      onSubmit(toProfile(answers));
      return;
    }
    setDirection(1);
    setStepIndex((prev) => prev + 1);
  };

  const handleBack = () => {
    if (!canGoBack) return;
    setValidationError(false);
    setDirection(-1);
    setStepIndex((prev) => prev - 1);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-3 py-4 sm:px-6">
      <button type="button" className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={handleRequestClose} aria-hidden="true" />
      <section
        data-referral-wizard
        role="dialog"
        aria-modal="true"
        aria-labelledby={dialogTitleId}
        aria-describedby={dialogDescriptionId}
        className="relative z-10 flex max-h-[92vh] w-full max-w-3xl flex-col overflow-hidden rounded-2xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-card)] shadow-[0_20px_90px_rgba(0,180,255,0.15)] sm:rounded-3xl"
      >
        <header className="border-b border-white/10 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="inline-flex items-center gap-2 rounded-full border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)] px-3 py-1 text-xs text-[color:var(--color-accent-cyan)]">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                <span id={dialogTitleId}>{labels.title}</span>
              </div>
              <p id={dialogDescriptionId} className="mt-2 text-sm text-[color:var(--color-text-muted)]">{labels.subtitle}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[color:var(--color-text-muted)]">
                <span className="rounded-full border border-white/10 px-2 py-0.5">{draftLabel}</span>
                <span className="rounded-full border border-white/10 px-2 py-0.5">{draftColorLabel}</span>
              </div>
            </div>
            <button
              ref={firstInteractiveRef}
              type="button"
              onClick={handleRequestClose}
              aria-label={labels.closeAriaLabel}
              className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 text-[color:var(--color-text-muted)] transition hover:text-[color:var(--color-text-main)] ${dsInteraction.focusRingClass}`}
            >
              <X className="h-5 w-5" aria-hidden="true" />
            </button>
          </div>
          <div className="mt-4 flex items-center justify-between gap-3">
            <div className="h-2 w-full overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-gradient-to-r from-cyan-400 via-blue-500 to-violet-500 transition-all"
                style={{ width: `${((stepIndex + 1) / STEP_ORDER.length) * 100}%` }}
                role="progressbar"
                aria-label={labels.progressA11yLabel}
                aria-valuemin={1}
                aria-valuemax={STEP_ORDER.length}
                aria-valuenow={stepIndex + 1}
              />
            </div>
            <span className="rounded-full border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)] px-2 py-1 text-xs text-[color:var(--color-accent-cyan)]">
              {progressLabel}
            </span>
          </div>
        </header>

        <div className="min-h-[340px] overflow-y-auto p-4 sm:min-h-[380px] sm:p-6">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={currentStep.id}
              custom={direction}
              variants={shouldReduceMotion ? undefined : wizardStepVariants}
              initial={shouldReduceMotion ? false : "enter"}
              animate={shouldReduceMotion ? undefined : "center"}
              exit={shouldReduceMotion ? undefined : "exit"}
              className="space-y-4"
            >
              <div className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-[color:var(--color-surface-soft)] px-3 py-2 text-xs text-[color:var(--color-text-muted)]">
                <HelpCircle className="h-4 w-4 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
                {content.tooltip}
                {!currentStep.required ? (
                  <span className="rounded-full border border-white/10 px-2 py-0.5 text-[11px]">{labels.optionalBadge}</span>
                ) : null}
              </div>

              <p className="text-center text-xs uppercase tracking-wide text-[color:var(--color-text-muted)]">{content.title}</p>
              <h3 className={`text-center ${dsTypography.pageTitle}`}>{content.question}</h3>

              {singleStep ? (
                <div className="grid gap-2 sm:grid-cols-2">
                  {singleStep.options.map((option: string) => {
                    const selected = currentState === option;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => handleOptionSelect(option)}
                        aria-pressed={selected}
                        className={[
                          "min-h-12 rounded-xl border px-3 py-2 text-start text-sm transition",
                          selected
                            ? "border-[color:var(--color-accent-cyan)] bg-[color:var(--color-accent-cyan)]/15 text-[color:var(--color-text-main)]"
                            : "border-white/10 bg-[color:var(--color-surface-soft)] text-[color:var(--color-text-muted)] hover:border-[color:var(--color-border-glow)]",
                          dsInteraction.focusRingClass,
                        ].join(" ")}
                      >
                        {content.optionLabels[option]}
                      </button>
                    );
                  })}
                </div>
              ) : null}

              {multiStep ? (
                <div className="space-y-2">
                  <p className="text-center text-xs text-[color:var(--color-text-muted)]">{labels.multiSelectHint}</p>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {multiStep.options.map((option: string) => {
                      const selected = Array.isArray(currentState) && currentState.includes(option);
                      return (
                        <button
                          key={option}
                          type="button"
                          onClick={() => handleOptionSelect(option)}
                          aria-pressed={selected}
                          className={[
                            "min-h-12 rounded-xl border px-3 py-2 text-start text-sm transition",
                            selected
                              ? "border-[color:var(--color-accent-cyan)] bg-[color:var(--color-accent-cyan)]/15 text-[color:var(--color-text-main)]"
                              : "border-white/10 bg-[color:var(--color-surface-soft)] text-[color:var(--color-text-muted)] hover:border-[color:var(--color-border-glow)]",
                            dsInteraction.focusRingClass,
                          ].join(" ")}
                        >
                          {content.optionLabels[option]}
                        </button>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {noteStep ? (
                <textarea
                  value={typeof currentState === "string" ? currentState : ""}
                  onChange={(event) => {
                    setValidationError(false);
                    const nextValue = event.target.value.slice(0, noteStep.maxLength);
                    setAnswers((prev) => ({ ...prev, additionalNote: nextValue }));
                  }}
                  placeholder={content.placeholder}
                  aria-label={content.question}
                  className={`w-full rounded-xl border border-white/10 bg-[color:var(--color-surface-soft)] p-3 text-sm text-[color:var(--color-text-main)] placeholder:text-[color:var(--color-text-muted)] ${dsInteraction.focusRingClass}`}
                  rows={5}
                />
              ) : null}

              {validationError ? <p className="text-center text-xs text-rose-300">{labels.requiredAnswerError}</p> : null}
            </motion.div>
          </AnimatePresence>
        </div>

        <footer className="border-t border-white/10 p-4 sm:p-5">
          <div className="flex items-center justify-between gap-2">
            <Button variant="secondary" size="sm" onClick={handleBack} disabled={!canGoBack || submitting}>
              {labels.backButton}
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleNext}
              disabled={submitting}
              className="border-[color:var(--color-accent-cyan)] bg-[color:var(--color-accent-cyan)] text-slate-900 hover:brightness-110"
            >
              {isFinalStep ? labels.doneButton : labels.nextButton}
            </Button>
          </div>
        </footer>

        {showUnsavedConfirm ? (
          <div className="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/85 p-4">
            <div className="w-full max-w-sm rounded-2xl border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-card)] p-4 shadow-xl">
              <h4 className={dsTypography.cardTitle}>{labels.unsavedTitle}</h4>
              <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">{labels.unsavedDescription}</p>
              <div className="mt-4 flex items-center justify-end gap-2">
                <Button variant="secondary" size="sm" onClick={() => setShowUnsavedConfirm(false)}>
                  {labels.unsavedStayButton}
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setShowUnsavedConfirm(false);
                    onClose();
                  }}
                  className="border-rose-400/60 bg-rose-400/90 text-slate-900 hover:brightness-110"
                >
                  {labels.unsavedDiscardButton}
                </Button>
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}
