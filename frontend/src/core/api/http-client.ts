import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { env } from "@/core/config/env";
import { getAdminAccessToken, getAdminRefreshToken, useAdminAuthStore } from "@/state/auth-store";

interface AccessTokenRefreshResponse {
  access_token: string;
  token_type: string;
}

type RequestWithRetry = InternalAxiosRequestConfig & {
  _retry?: boolean;
  skipAuthRefresh?: boolean;
};

let refreshAccessTokenPromise: Promise<string | null> | null = null;

export const httpClient = axios.create({
  baseURL: env.apiBaseUrl,
  timeout: env.apiTimeoutMs,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json"
  }
});

async function refreshAccessToken(): Promise<string | null> {
  if (refreshAccessTokenPromise) {
    return refreshAccessTokenPromise;
  }

  refreshAccessTokenPromise = (async () => {
    const refreshToken = getAdminRefreshToken();
    if (!refreshToken) {
      useAdminAuthStore.getState().clear();
      return null;
    }

    try {
      const response = await httpClient.post<AccessTokenRefreshResponse>(
        "/v1/auth/refresh",
        { refresh_token: refreshToken },
        {
          skipAuthRefresh: true
        } as RequestWithRetry
      );
      const nextAccessToken = response.data.access_token?.trim();
      if (!nextAccessToken) {
        useAdminAuthStore.getState().clear();
        return null;
      }
      useAdminAuthStore.getState().setAccessToken(nextAccessToken);
      return nextAccessToken;
    } catch {
      useAdminAuthStore.getState().clear();
      return null;
    } finally {
      refreshAccessTokenPromise = null;
    }
  })();

  return refreshAccessTokenPromise;
}

// Extension point: attach auth/session headers once the auth phase is introduced.
httpClient.interceptors.request.use((config) => {
  const token = getAdminAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

httpClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as RequestWithRetry | undefined;
    const status = error.response?.status;

    if (!originalRequest || originalRequest.skipAuthRefresh || originalRequest._retry || status !== 401) {
      return Promise.reject(error);
    }

    const nextAccessToken = await refreshAccessToken();
    if (!nextAccessToken) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    originalRequest.headers = originalRequest.headers ?? {};
    originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
    return httpClient.request(originalRequest);
  }
);
