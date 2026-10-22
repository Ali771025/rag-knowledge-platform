import { create } from "zustand";

export const ADMIN_ACCESS_TOKEN_STORAGE_KEY = "adminAccessToken";
export const ADMIN_REFRESH_TOKEN_STORAGE_KEY = "adminRefreshToken";
const LEGACY_ACCESS_TOKEN_STORAGE_KEY = "authToken";

interface AdminAuthState {
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
}

interface AdminAuthActions {
  setTokens: (accessToken: string, refreshToken: string) => void;
  setAccessToken: (accessToken: string) => void;
  clear: () => void;
  hydrate: () => void;
}

type AdminAuthStore = AdminAuthState & AdminAuthActions;

function canUseStorage(): boolean {
  return typeof window !== "undefined" && typeof window.localStorage !== "undefined";
}

function readStoredToken(key: string): string | null {
  if (!canUseStorage()) return null;
  const value = window.localStorage.getItem(key);
  const normalized = value?.trim();
  return normalized ? normalized : null;
}

function persistTokens(accessToken: string | null, refreshToken: string | null): void {
  if (!canUseStorage()) return;

  if (accessToken) {
    window.localStorage.setItem(ADMIN_ACCESS_TOKEN_STORAGE_KEY, accessToken);
    window.localStorage.setItem(LEGACY_ACCESS_TOKEN_STORAGE_KEY, accessToken);
  } else {
    window.localStorage.removeItem(ADMIN_ACCESS_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(LEGACY_ACCESS_TOKEN_STORAGE_KEY);
  }

  if (refreshToken) {
    window.localStorage.setItem(ADMIN_REFRESH_TOKEN_STORAGE_KEY, refreshToken);
  } else {
    window.localStorage.removeItem(ADMIN_REFRESH_TOKEN_STORAGE_KEY);
  }
}

function getInitialState(): AdminAuthState {
  const accessToken = readStoredToken(ADMIN_ACCESS_TOKEN_STORAGE_KEY) ?? readStoredToken(LEGACY_ACCESS_TOKEN_STORAGE_KEY);
  const refreshToken = readStoredToken(ADMIN_REFRESH_TOKEN_STORAGE_KEY);

  return {
    accessToken,
    refreshToken,
    isAuthenticated: Boolean(accessToken)
  };
}

export const useAdminAuthStore = create<AdminAuthStore>((set) => ({
  ...getInitialState(),
  setTokens: (accessToken, refreshToken) => {
    const nextAccessToken = accessToken.trim();
    const nextRefreshToken = refreshToken.trim();
    persistTokens(nextAccessToken, nextRefreshToken);
    set({
      accessToken: nextAccessToken,
      refreshToken: nextRefreshToken,
      isAuthenticated: true
    });
  },
  setAccessToken: (accessToken) => {
    const nextAccessToken = accessToken.trim();
    const currentRefreshToken = readStoredToken(ADMIN_REFRESH_TOKEN_STORAGE_KEY);
    persistTokens(nextAccessToken, currentRefreshToken);
    set((state) => ({
      accessToken: nextAccessToken,
      refreshToken: state.refreshToken ?? currentRefreshToken,
      isAuthenticated: true
    }));
  },
  clear: () => {
    persistTokens(null, null);
    set({
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false
    });
  },
  hydrate: () => {
    const accessToken = readStoredToken(ADMIN_ACCESS_TOKEN_STORAGE_KEY) ?? readStoredToken(LEGACY_ACCESS_TOKEN_STORAGE_KEY);
    const refreshToken = readStoredToken(ADMIN_REFRESH_TOKEN_STORAGE_KEY);
    set({
      accessToken,
      refreshToken,
      isAuthenticated: Boolean(accessToken)
    });
  }
}));

export function getAdminAccessToken(): string | null {
  const state = useAdminAuthStore.getState();
  if (state.accessToken) {
    return state.accessToken;
  }
  return readStoredToken(ADMIN_ACCESS_TOKEN_STORAGE_KEY) ?? readStoredToken(LEGACY_ACCESS_TOKEN_STORAGE_KEY);
}

export function getAdminRefreshToken(): string | null {
  const state = useAdminAuthStore.getState();
  if (state.refreshToken) {
    return state.refreshToken;
  }
  return readStoredToken(ADMIN_REFRESH_TOKEN_STORAGE_KEY);
}
