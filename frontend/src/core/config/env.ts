const APP_ENVIRONMENTS = ["development", "staging", "production", "test"] as const;

type AppEnvironment = (typeof APP_ENVIRONMENTS)[number];

export interface EnvConfig {
  appEnv: AppEnvironment;
  apiBaseUrl: string;
  apiTimeoutMs: number;
  wsBaseUrl: string;
  enableWebSocket: boolean;
}

function normalizeAppEnv(value: string | undefined): AppEnvironment {
  if (!value) return "development";

  if (APP_ENVIRONMENTS.includes(value as AppEnvironment)) {
    return value as AppEnvironment;
  }

  return "development";
}

function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function normalizeApiBaseUrl(value: string | undefined): string {
  if (!value) return "/api";

  if (value.startsWith("/")) return trimTrailingSlash(value);

  try {
    const normalized = new URL(value);
    if (!["http:", "https:"].includes(normalized.protocol)) {
      throw new Error("unsupported protocol");
    }

    return trimTrailingSlash(normalized.toString());
  } catch {
    throw new Error("VITE_API_BASE_URL must be a valid absolute URL or start with '/'.");
  }
}

function normalizeWsBaseUrl(value: string | undefined, apiBaseUrl: string): string {
  if (value) {
    if (value.startsWith("/")) return trimTrailingSlash(value);

    try {
      const normalized = new URL(value);
      if (!["ws:", "wss:"].includes(normalized.protocol)) {
        throw new Error("unsupported protocol");
      }

      return trimTrailingSlash(normalized.toString());
    } catch {
      throw new Error("VITE_WS_BASE_URL must be a valid ws(s) URL or start with '/'.");
    }
  }

  if (apiBaseUrl.startsWith("http://")) {
    return apiBaseUrl.replace("http://", "ws://");
  }

  if (apiBaseUrl.startsWith("https://")) {
    return apiBaseUrl.replace("https://", "wss://");
  }

  return "/ws";
}

function normalizeBoolean(value: string | undefined, fallback: boolean): boolean {
  if (!value) return fallback;
  const normalized = value.trim().toLowerCase();
  if (["1", "true", "yes", "on"].includes(normalized)) return true;
  if (["0", "false", "no", "off"].includes(normalized)) return false;
  return fallback;
}

function normalizeApiTimeout(value: string | undefined): number {
  const fallback = 45_000;
  if (!value) return fallback;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(180_000, Math.max(5_000, parsed));
}

const appEnv = normalizeAppEnv(import.meta.env.VITE_APP_ENV ?? import.meta.env.MODE);
const apiBaseUrl = normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL);
const apiTimeoutMs = normalizeApiTimeout(import.meta.env.VITE_API_TIMEOUT_MS);
const wsBaseUrl = normalizeWsBaseUrl(import.meta.env.VITE_WS_BASE_URL, apiBaseUrl);
const enableWebSocket = normalizeBoolean(import.meta.env.VITE_ENABLE_WEBSOCKET, false);

export const env: EnvConfig = {
  appEnv,
  apiBaseUrl,
  apiTimeoutMs,
  wsBaseUrl,
  enableWebSocket
};
