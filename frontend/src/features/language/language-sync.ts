import { getUserProfile, updateUserProfile, type UserProfileResponse } from "@/core/api";
import { getAdminAccessToken } from "@/state/auth-store";
import { isSupportedLocale, type AppLocale } from "@/i18n";
import { useLanguageStore } from "@/state/language-store";
import { useProfileStore } from "@/state/profile-store";
import { createLocalStorageAdapter } from "@/state/workspace-storage";

type LanguageConflictResolution = "prefer-local" | "prefer-server";

interface SyncInput {
  desiredLocale: AppLocale;
  strategy?: LanguageConflictResolution;
  skipLocalPersist?: boolean;
}

interface SyncResult {
  locale: AppLocale;
  source: "local" | "server";
  conflictResolved: boolean;
}

interface SyncMetadata {
  lastSyncedLocale: AppLocale;
  syncedAt: string;
}

const metadataStorage = createLocalStorageAdapter<SyncMetadata>("ragai.language.sync.v1");

function canSyncWithServer(): boolean {
  return Boolean(getAdminAccessToken());
}

export function normalizeServerLocale(value: string | null | undefined): AppLocale | null {
  if (!value) return null;
  const normalized = value.trim().toLowerCase();
  const base = normalized.split("-")[0] ?? normalized;
  if (isSupportedLocale(base)) {
    return base;
  }
  return null;
}

function updateProfileLanguageSummary(profile: UserProfileResponse): void {
  const current = useProfileStore.getState().summary;
  if (!current) return;

  useProfileStore.getState().setSummary({
    ...current,
    language: profile.language
  });
}

function recordSyncedLocale(locale: AppLocale): void {
  metadataStorage.save({
    lastSyncedLocale: locale,
    syncedAt: new Date().toISOString()
  });
}

async function readServerLocale(): Promise<AppLocale | null> {
  const serverProfile = await getUserProfile();
  updateProfileLanguageSummary(serverProfile);
  return normalizeServerLocale(serverProfile.language);
}

export async function hydrateLanguageFromServer(): Promise<AppLocale | null> {
  if (!canSyncWithServer()) {
    return null;
  }

  try {
    const serverLocale = await readServerLocale();
    if (!serverLocale) {
      return null;
    }

    useLanguageStore.getState().setLocale(serverLocale, { persist: true });
    recordSyncedLocale(serverLocale);
    return serverLocale;
  } catch {
    return null;
  }
}

export async function syncLanguagePreference(input: SyncInput): Promise<SyncResult> {
  const desiredLocale = input.desiredLocale;
  const strategy = input.strategy ?? "prefer-local";
  const skipLocalPersist = input.skipLocalPersist ?? false;

  if (!canSyncWithServer()) {
    useLanguageStore.getState().setLocale(desiredLocale, { persist: !skipLocalPersist });
    recordSyncedLocale(desiredLocale);
    return { locale: desiredLocale, source: "local", conflictResolved: false };
  }

  let serverLocale: AppLocale | null = null;

  try {
    serverLocale = await readServerLocale();
  } catch {
    useLanguageStore.getState().setLocale(desiredLocale, { persist: !skipLocalPersist });
    recordSyncedLocale(desiredLocale);
    return { locale: desiredLocale, source: "local", conflictResolved: false };
  }

  const hasConflict = Boolean(serverLocale && serverLocale !== desiredLocale);

  if (hasConflict && strategy === "prefer-server") {
    useLanguageStore.getState().setLocale(serverLocale as AppLocale, { persist: !skipLocalPersist });
    recordSyncedLocale(serverLocale as AppLocale);
    return {
      locale: serverLocale as AppLocale,
      source: "server",
      conflictResolved: true
    };
  }

  if (!hasConflict && serverLocale === desiredLocale) {
    useLanguageStore.getState().setLocale(desiredLocale, { persist: !skipLocalPersist });
    recordSyncedLocale(desiredLocale);
    return {
      locale: desiredLocale,
      source: "server",
      conflictResolved: false
    };
  }

  try {
    const updated = await updateUserProfile({ language: desiredLocale });
    useLanguageStore.getState().setLocale(desiredLocale, { persist: !skipLocalPersist });
    updateProfileLanguageSummary(updated);
    recordSyncedLocale(desiredLocale);
    return {
      locale: desiredLocale,
      source: "local",
      conflictResolved: hasConflict
    };
  } catch {
    if (serverLocale) {
      useLanguageStore.getState().setLocale(serverLocale, { persist: !skipLocalPersist });
      recordSyncedLocale(serverLocale);
      return {
        locale: serverLocale,
        source: "server",
        conflictResolved: hasConflict
      };
    }

    useLanguageStore.getState().setLocale(desiredLocale, { persist: !skipLocalPersist });
    recordSyncedLocale(desiredLocale);
    return { locale: desiredLocale, source: "local", conflictResolved: hasConflict };
  }
}
