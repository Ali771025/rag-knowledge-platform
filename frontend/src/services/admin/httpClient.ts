import axios, { type AxiosResponse, type AxiosRequestConfig } from "axios";
import { env } from "@/core/config/env";
import { getAdminAccessToken, useAdminAuthStore } from "@/state/auth-store";

export interface AdminApiErrorData {
  error?: string;
  code?: string;
  detail?: string;
  message?: string;
}

export class AdminApiError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly detail?: string;
  readonly data?: unknown;

  constructor(params: { message: string; status?: number; code?: string; detail?: string; data?: unknown }) {
    super(params.message);
    this.name = "AdminApiError";
    this.status = params.status;
    this.code = params.code;
    this.detail = params.detail;
    this.data = params.data;
  }
}

function normalizeAdminBaseUrl(apiBaseUrl: string): string {
  if (apiBaseUrl.endsWith("/api")) {
    return apiBaseUrl.slice(0, -4);
  }

  return apiBaseUrl;
}

function normalizeApiError(error: unknown): AdminApiError {
  if (!axios.isAxiosError(error)) {
    return new AdminApiError({
      message: error instanceof Error ? error.message : "Unexpected admin API error."
    });
  }

  const responseData = error.response?.data as AdminApiErrorData | undefined;
  const message =
    responseData?.error ??
    responseData?.message ??
    error.message ??
    "Request failed while contacting admin APIs.";

  return new AdminApiError({
    message,
    status: error.response?.status,
    code: responseData?.code ?? error.code,
    detail: responseData?.detail,
    data: error.response?.data
  });
}

export const adminHttpClient = axios.create({
  baseURL: normalizeAdminBaseUrl(env.apiBaseUrl),
  timeout: 120_000,
  headers: {
    Accept: "application/json"
  }
});

adminHttpClient.interceptors.request.use((config) => {
  const token = getAdminAccessToken();

  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

adminHttpClient.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    if (axios.isAxiosError(error) && error.response?.status === 401) {
      useAdminAuthStore.getState().clear();
    }
    return Promise.reject(normalizeApiError(error));
  }
);

export async function adminRequest<TResponse, TBody = unknown>(
  config: AxiosRequestConfig<TBody>
): Promise<TResponse> {
  try {
    const response = await adminHttpClient.request<TResponse, AxiosResponse<TResponse>, TBody>(config);
    return response.data;
  } catch (error) {
    throw normalizeApiError(error);
  }
}
