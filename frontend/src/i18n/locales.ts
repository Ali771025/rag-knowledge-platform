export const supportedLocales = ["en", "fa", "ar"] as const;

export type AppLocale = (typeof supportedLocales)[number];

export type Direction = "ltr" | "rtl";

export const defaultLocale: AppLocale = "en";

const localeDirectionMap: Record<AppLocale, Direction> = {
  en: "ltr",
  fa: "rtl",
  ar: "rtl"
};

export function isSupportedLocale(value: unknown): value is AppLocale {
  return typeof value === "string" && supportedLocales.includes(value as AppLocale);
}

export function getLocaleDirection(locale: AppLocale): Direction {
  return localeDirectionMap[locale];
}
