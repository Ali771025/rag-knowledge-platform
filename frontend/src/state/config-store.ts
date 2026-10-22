import { getEffectiveLocale, useLanguageStore } from "./language-store";
import type { AppLocale } from "@/i18n";

interface ConfigStoreView {
  language: AppLocale;
  setLanguage: (locale: AppLocale) => void;
}

export function useConfigStore(): ConfigStoreView {
  const locale = useLanguageStore((state) => state.locale);
  const setLocale = useLanguageStore((state) => state.setLocale);

  return {
    language: getEffectiveLocale(locale),
    setLanguage: (nextLocale) => setLocale(nextLocale)
  };
}
