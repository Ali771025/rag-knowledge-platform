import { hydrateLanguageFromServer, syncLanguagePreference } from "./language-sync";
import { isSupportedLocale, type AppLocale } from "@/i18n";
import { useLanguageStore } from "@/state/language-store";

let hasBootstrappedLanguageSync = false;

export async function bootstrapServerLanguageSync(): Promise<void> {
  if (hasBootstrappedLanguageSync) return;
  hasBootstrappedLanguageSync = true;

  const currentLocale = useLanguageStore.getState().locale;
  if (!currentLocale) {
    await hydrateLanguageFromServer();
    return;
  }

  if (!isSupportedLocale(currentLocale)) {
    return;
  }

  await syncLanguagePreference({
    desiredLocale: currentLocale as AppLocale,
    strategy: "prefer-server",
    skipLocalPersist: true
  });
}
