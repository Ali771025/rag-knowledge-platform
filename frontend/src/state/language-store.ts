import { create } from "zustand";
import { appRoutes } from "@/app/routes/contracts";
import { createLocalStorageAdapter } from "./workspace-storage";
import { defaultLocale, isSupportedLocale, type AppLocale } from "@/i18n/locales";

interface LanguagePersistedState {
  locale: AppLocale;
}

export interface LanguageState {
  locale: AppLocale | null;
}

export interface LanguageActions {
  setLocale: (locale: AppLocale, options?: { persist?: boolean }) => void;
  clearLocale: () => void;
}

export type LanguageStore = LanguageState & LanguageActions;

const STORAGE_KEY = "ragai.language.v1";

const languageStorage = createLocalStorageAdapter<LanguagePersistedState>(STORAGE_KEY);

function loadInitialLocale(): AppLocale | null {
  const persisted = languageStorage.load();
  if (persisted && isSupportedLocale(persisted.locale)) {
    return persisted.locale;
  }

  return null;
}

function persistLocale(locale: AppLocale | null): void {
  if (locale === null) {
    languageStorage.clear();
    return;
  }

  languageStorage.save({ locale });
}

export const useLanguageStore = create<LanguageStore>((set) => ({
  locale: loadInitialLocale(),
  setLocale: (locale, options) => {
    if (options?.persist !== false) {
      persistLocale(locale);
    }
    set({ locale });
  },
  clearLocale: () => {
    persistLocale(null);
    set({ locale: null });
  }
}));

export function getEffectiveLocale(locale: AppLocale | null): AppLocale {
  return locale ?? defaultLocale;
}

export function routeForPostLanguageEntry(_locale: AppLocale): string {
  return appRoutes.agent;
}
