import { httpClient } from "@/core/api/http-client";
import { useAdminAuthStore } from "@/state/auth-store";

export interface AdminLoginPayload {
  email: string;
  password: string;
}

export interface TelegramLoginPayload {
  telegramUserId: number;
  authSecret: string;
  username?: string;
  firstName?: string;
  lastName?: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

function normalizeError(error: unknown, fallback: string): Error {
  const detail =
    typeof error === "object" && error !== null && "response" in error
      ? (error as { response?: { data?: { detail?: string } } }).response?.data?.detail
      : undefined;

  if (detail && detail.trim()) {
    return new Error(detail.trim());
  }

  if (error instanceof Error && error.message.trim()) {
    return new Error(error.message);
  }

  return new Error(fallback);
}

export async function loginAdmin(payload: AdminLoginPayload): Promise<void> {
  try {
    const response = await httpClient.post<TokenResponse>("/v1/auth/admin/login", payload);
    const tokens = response.data;
    useAdminAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
  } catch (error) {
    throw normalizeError(error, "Admin login failed.");
  }
}

export async function loginTelegramUser(payload: TelegramLoginPayload): Promise<void> {
  try {
    const response = await httpClient.post<TokenResponse>("/v1/auth/telegram/login", {
      telegram_user_id: payload.telegramUserId,
      auth_secret: payload.authSecret,
      username: payload.username,
      first_name: payload.firstName,
      last_name: payload.lastName
    });
    const tokens = response.data;
    useAdminAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
  } catch (error) {
    throw normalizeError(error, "Telegram login failed.");
  }
}

export function logoutAdmin(): void {
  useAdminAuthStore.getState().clear();
}
