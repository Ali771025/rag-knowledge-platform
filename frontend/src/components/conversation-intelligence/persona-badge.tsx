import type { PersonaType } from "@/types";
import { dsTypography } from "@/design-system";
import { getPersonaLabel } from "@/features/conversation-intelligence";

interface PersonaBadgeProps {
  persona?: PersonaType | null;
}

export function PersonaBadge({ persona }: PersonaBadgeProps) {
  const label = getPersonaLabel(persona);

  return (
    <section className="rounded-xl border border-border bg-background px-3 py-2" aria-label="Current persona">
      <p className={dsTypography.caption}>Persona</p>
      <p className={`mt-1 ${dsTypography.cardTitle}`}>{label}</p>
    </section>
  );
}
