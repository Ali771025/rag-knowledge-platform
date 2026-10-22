import { Plus } from "lucide-react";
import { Button, CardShell } from "@/components/ui";
import { dsTypography } from "@/design-system";

interface ReferralCreatePanelProps {
  title: string;
  subtitle: string;
  createLabel: string;
  onCreateDraft: () => void;
}

export function ReferralCreatePanel({ title, subtitle, createLabel, onCreateDraft }: ReferralCreatePanelProps) {
  return (
    <CardShell className="p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <h2 className={dsTypography.cardTitle}>{title}</h2>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">{subtitle}</p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={onCreateDraft}
          className="w-full shrink-0 border-[color:var(--color-accent-blue)] bg-[color:var(--color-accent-blue)] text-white hover:brightness-110 sm:w-auto"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {createLabel}
        </Button>
      </div>
    </CardShell>
  );
}

export const CreateReferralLinkPanel = ReferralCreatePanel;
