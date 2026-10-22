import { motion, useReducedMotion } from "framer-motion";
import { Check } from "lucide-react";
import { dsMotionVariants, dsTypography } from "@/design-system";
import { useI18n } from "@/i18n";
import { languageOptions } from "@/features/language/language.constants";
import type { AppLocale } from "@/i18n";

interface LanguageSwitcherProps {
  value: AppLocale;
  compact?: boolean;
  onChange: (locale: AppLocale) => void;
}

export function LanguageSwitcher({ value, compact = false, onChange }: LanguageSwitcherProps) {
  const { messages } = useI18n();
  const shouldReduceMotion = useReducedMotion();

  if (compact) {
    return (
      <label className="inline-flex items-center gap-2 text-xs text-muted-foreground">
        <span>{messages.language.switcherLabel}</span>
        <select
          value={value}
          onChange={(event) => onChange(event.target.value as AppLocale)}
          className="h-9 rounded-lg border border-border bg-background px-2 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {languageOptions.map((option) => (
            <option key={option.locale} value={option.locale}>
              {messages.locales[option.locale].nativeName}
            </option>
          ))}
        </select>
      </label>
    );
  }

  return (
    <div role="radiogroup" aria-label={messages.language.radioGroupLabel} className="grid w-full gap-3 sm:grid-cols-2">
      {languageOptions.map((option) => {
        const isSelected = option.locale === value;
        const localeCopy = messages.locales[option.locale];

        return (
          <motion.button
            key={option.locale}
            type="button"
            role="radio"
            aria-checked={isSelected}
            aria-label={`${localeCopy.nativeName} (${localeCopy.englishName})`}
            whileTap={shouldReduceMotion ? undefined : { scale: 0.98 }}
            initial={shouldReduceMotion ? false : "hidden"}
            animate="visible"
            variants={shouldReduceMotion ? undefined : dsMotionVariants.subtleSlideUp}
            onClick={() => onChange(option.locale)}
            className={`relative min-h-16 rounded-xl border px-4 py-3 text-start transition ${
              isSelected
                ? "border-primary bg-primary/10 shadow-sm"
                : "border-border bg-surface-1 hover:border-primary/35 hover:bg-muted/35"
            } focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background`}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl" aria-hidden="true">
                {option.flag}
              </span>
              <div className="min-w-0">
                <p className={dsTypography.bodyLg}>{localeCopy.nativeName}</p>
                <p className={dsTypography.secondary}>{localeCopy.englishName}</p>
              </div>
            </div>
            {isSelected ? (
              <span className="absolute end-3 top-3 inline-flex h-5 w-5 items-center justify-center rounded-full bg-primary text-white">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
              </span>
            ) : null}
          </motion.button>
        );
      })}
    </div>
  );
}
