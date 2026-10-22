import { createContext, useContext, useEffect, useMemo, type PropsWithChildren } from "react";
import { getMessages, type MessagesSchema } from "./messages";
import { getLocaleDirection, type AppLocale, type Direction } from "./locales";
import { getEffectiveLocale, useLanguageStore } from "@/state/language-store";

interface I18nContextValue {
  locale: AppLocale;
  direction: Direction;
  messages: MessagesSchema;
  selectedLocale: AppLocale | null;
  setLocale: (locale: AppLocale) => void;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: PropsWithChildren) {
  const selectedLocale = useLanguageStore((state) => state.locale);
  const setLocale = useLanguageStore((state) => state.setLocale);

  const locale = getEffectiveLocale(selectedLocale);
  const direction = getLocaleDirection(locale);
  const messages = useMemo(() => getMessages(locale), [locale]);

  useEffect(() => {
    const root = document.documentElement;
    root.lang = locale;
    root.dir = direction;
  }, [direction, locale]);

  const contextValue = useMemo<I18nContextValue>(
    () => ({
      locale,
      direction,
      messages,
      selectedLocale,
      setLocale
    }),
    [direction, locale, messages, selectedLocale, setLocale]
  );

  return <I18nContext.Provider value={contextValue}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used within I18nProvider.");
  }

  return context;
}

