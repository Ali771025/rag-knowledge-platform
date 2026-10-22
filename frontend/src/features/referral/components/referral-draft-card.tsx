import { Check, Sparkles, Tag } from "lucide-react";
import { Button, CardShell, InputShell } from "@/components/ui";
import { dsTypography } from "@/design-system";
import type { ReferralTagColor } from "@/services/referral";

const REFERRAL_COLORS: ReferralTagColor[] = ["blue", "violet", "cyan", "green", "orange", "pink", "gold", "gray"];

function colorClass(color: ReferralTagColor): string {
  const colorMap: Record<ReferralTagColor, string> = {
    blue: "bg-blue-500/20 border-blue-400/50 text-blue-200",
    violet: "bg-violet-500/20 border-violet-400/50 text-violet-200",
    cyan: "bg-cyan-500/20 border-cyan-400/50 text-cyan-200",
    green: "bg-emerald-500/20 border-emerald-400/50 text-emerald-200",
    orange: "bg-orange-500/20 border-orange-400/50 text-orange-200",
    pink: "bg-pink-500/20 border-pink-400/50 text-pink-200",
    gold: "bg-amber-500/20 border-amber-400/50 text-amber-200",
    gray: "bg-slate-500/20 border-slate-400/50 text-slate-200",
  };
  return colorMap[color];
}

interface ReferralDraftCardProps {
  label: string;
  color: ReferralTagColor;
  shortUrlPreview: string;
  labels: {
    draftTitle: string;
    draftLabel: string;
    draftUrlPreview: string;
    selectColor: string;
    done: string;
    customize: string;
    tagColors: Record<ReferralTagColor, string>;
  };
  onChangeLabel: (next: string) => void;
  onSelectColor: (next: ReferralTagColor) => void;
  onDone: () => void;
  onCustomize: () => void;
}

export function ReferralDraftCard({
  label,
  color,
  shortUrlPreview,
  labels,
  onChangeLabel,
  onSelectColor,
  onDone,
  onCustomize,
}: ReferralDraftCardProps) {
  const canSubmit = label.trim().length > 0;
  return (
    <CardShell className="p-4">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <Tag className="h-4 w-4 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
          <h3 className={dsTypography.cardTitle}>{labels.draftTitle}</h3>
        </div>
        <div>
          <label className="mb-1 block text-xs text-[color:var(--color-text-muted)]">{labels.draftLabel}</label>
          <InputShell value={label} onChange={(event) => onChangeLabel(event.target.value)} />
        </div>
        <div>
          <p className="text-xs text-[color:var(--color-text-muted)]">{labels.selectColor}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {REFERRAL_COLORS.map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onSelectColor(item)}
                aria-label={`${labels.selectColor} ${labels.tagColors[item]}`}
                className={[
                  "inline-flex min-h-9 min-w-9 items-center justify-center gap-1 rounded-full border px-3 text-xs transition",
                  colorClass(item),
                  color === item ? "ring-2 ring-[color:var(--color-accent-cyan)]" : "",
                ].join(" ")}
              >
                <span className="h-2.5 w-2.5 rounded-full bg-current opacity-90" aria-hidden="true" />
              </button>
            ))}
          </div>
        </div>
        <div className="rounded-lg border border-[color:var(--color-border-glow)] bg-[color:var(--color-surface-soft)] px-3 py-2 text-sm text-[color:var(--color-text-main)]">
          <p className="text-xs text-[color:var(--color-text-muted)]">{labels.draftUrlPreview}</p>
          <p className="mt-1 truncate">{shortUrlPreview}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={onDone}
            disabled={!canSubmit}
            className="border-[color:var(--color-accent-cyan)] bg-[color:var(--color-accent-cyan)] text-slate-900 hover:brightness-110"
          >
            <Check className="h-4 w-4" aria-hidden="true" />
            {labels.done}
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={!canSubmit}
            onClick={onCustomize}
            className="border-[color:var(--color-accent-cyan)]/50 text-[color:var(--color-accent-cyan)] hover:bg-[color:var(--color-accent-cyan)]/10"
          >
            <Sparkles className="h-4 w-4" aria-hidden="true" />
            {labels.customize}
          </Button>
        </div>
      </div>
    </CardShell>
  );
}

export const ReferralDraftLinkCard = ReferralDraftCard;
