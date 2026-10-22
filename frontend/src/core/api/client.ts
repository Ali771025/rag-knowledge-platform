import axios, { type AxiosRequestConfig, type AxiosResponse } from "axios";
import { httpClient } from "./http-client";

export const apiClient = httpClient;

export interface ApiClientErrorData {
  error?: string;
  code?: string;
  detail?: string;
  message?: string;
}

export class ApiClientError extends Error {
  readonly status?: number;
  readonly code?: string;
  readonly detail?: string;
  readonly data?: unknown;

  constructor(params: { message: string; status?: number; code?: string; detail?: string; data?: unknown }) {
    super(params.message);
    this.name = "ApiClientError";
    this.status = params.status;
    this.code = params.code;
    this.detail = params.detail;
    this.data = params.data;
  }
}

export function isApiClientError(value: unknown): value is ApiClientError {
  return value instanceof ApiClientError;
}

function toApiClientError(error: unknown): ApiClientError {
  if (!axios.isAxiosError(error)) {
    return new ApiClientError({
      message: error instanceof Error ? error.message : "Unexpected API error."
    });
  }

  const responseData = error.response?.data as ApiClientErrorData | undefined;
  const isTimeout = error.code === "ECONNABORTED" || String(error.message || "").toLowerCase().includes("timeout");
  const message =
    (isTimeout
      ? "The assistant is taking longer than expected. Please retry."
      : undefined) ??
    responseData?.error ??
    responseData?.message ??
    error.message ??
    "Request failed while contacting the backend service.";

  return new ApiClientError({
    message,
    status: error.response?.status,
    code: responseData?.code ?? error.code,
    detail: responseData?.detail,
    data: error.response?.data
  });
}

export async function requestApi<TResponse, TBody = unknown>(
  config: AxiosRequestConfig<TBody>
): Promise<TResponse> {
  try {
    const response = await apiClient.request<TResponse, AxiosResponse<TResponse>, TBody>(config);
    return response.data;
  } catch (error) {
    throw toApiClientError(error);
  }
}
