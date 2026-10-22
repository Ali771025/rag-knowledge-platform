import type { FunnelStage, PersonaType } from "@/types";

interface OnboardingGuidanceWidgetProps {
  stage?: FunnelStage | null;
  persona?: PersonaType | null;
}

function getGuidanceCopy(stage: FunnelStage | null | undefined, persona: PersonaType | null | undefined): string {
  if (!stage || stage === "ENTRY") {
    return "Share your main goal so the assistant can tailor the next steps.";
  }

  if (stage === "EXPLORATION") {
    return "Add one concrete detail about your situation to improve recommendations.";
  }

  if (stage === "TRUST") {
    return "Ask one clarifying question to build confidence before deciding.";
  }

  if (stage === "OPPORTUNITY") {
    return "Pick one option that feels most relevant and explore it first.";
  }

  if (stage === "MICRO_COMMITMENT") {
    return "Take one small next step to keep momentum without overcommitting.";
  }

  if (stage === "ECONOMIC_ACTION") {
    if (persona === "SAVER") return "Review the value and cost details before confirming your next step.";
    return "Confirm your preferred option when you feel ready to proceed.";
  }

  return "Continue with one focused question or action.";
}

export function OnboardingGuidanceWidget({ stage, persona }: OnboardingGuidanceWidgetProps) {
  const guidance = getGuidanceCopy(stage, persona);

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Onboarding guidance">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Next helpful step</p>
      <p className="mt-1 text-xs text-muted-foreground">{guidance}</p>
    </section>
  );
}
