import { adminRequest, adminHttpClient } from "./httpClient";
import { getAdminAccessToken } from "@/state/auth-store";
import type {
  ActiveBudgetAlertsResponse,
  APIKeyBudgetConfigResponse,
  APIKeyListResponse,
  APIKeyUsageDetailsResponse,
  BudgetUpdatePayload,
  CostForecastResponse,
  OptimizationRecommendationListResponse,
  OptimizationSavingsReportResponse,
  RecommendationDismissResponse,
  TimeGranularity,
  TokenUsageByModelResponse,
  TokenUsageRealtimeEvent,
  TokenUsageSummaryResponse
} from "@/types/tokenMonitoring";

export interface TokenUsageFilters {
  provider?: string;
  model?: string;
  apiKeyId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export interface ByKeyFilters extends TokenUsageFilters {
  page?: number;
  pageSize?: number;
  granularity?: TimeGranularity;
}

export const TOKEN_MONITORING_ENDPOINTS = {
  summary: "/api/v1/admin/token-usage/summary",
  byModel: "/api/v1/admin/token-usage/by-model",
  byKey: (apiKeyId: string) => `/api/v1/admin/token-usage/by-key/${encodeURIComponent(apiKeyId)}`,
  costForecast: "/api/v1/admin/token-usage/cost-forecast",
  realtime: "/api/v1/admin/token-usage/realtime",
  recommendations: "/api/v1/admin/optimization/recommendations",
  dismissRecommendation: (id: string) => `/api/v1/admin/optimization/dismiss/${encodeURIComponent(id)}`,
  savingsReport: "/api/v1/admin/optimization/savings-report",
  activeAlerts: "/api/v1/admin/alerts/active",
  updateBudget: (id: string) => `/api/v1/admin/api-keys/${encodeURIComponent(id)}/budget`,
  apiKeys: "/api/v1/admin/api-keys"
} as const;

function toRealtimeEvent(payload: Record<string, unknown>): TokenUsageRealtimeEvent {
  return {
    timestamp: String(payload.timestamp ?? ""),
    provider: String(payload.provider ?? "openai") as TokenUsageRealtimeEvent["provider"],
    model_name: String(payload.model_name ?? "unknown"),
    api_key_id: payload.api_key_id ? String(payload.api_key_id) : null,
    tokens_delta: Number(payload.tokens_delta ?? 0),
    cost_delta: String(payload.cost_delta ?? "0"),
    latency_ms: Number(payload.latency_ms ?? 0),
    cache_hit: Boolean(payload.cache_hit)
  };
}

function toQuery(filters: TokenUsageFilters, granularity?: TimeGranularity) {
  return {
    provider: filters.provider,
    model: filters.model,
    api_key_id: filters.apiKeyId,
    date_from: filters.dateFrom,
    date_to: filters.dateTo,
    granularity
  };
}

export function getTokenUsageSummary(
  filters: TokenUsageFilters,
  granularity: TimeGranularity = "daily"
): Promise<TokenUsageSummaryResponse> {
  return adminRequest<TokenUsageSummaryResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.summary,
    params: toQuery(filters, granularity)
  });
}

export function getTokenUsageByModel(filters: TokenUsageFilters): Promise<TokenUsageByModelResponse> {
  return adminRequest<TokenUsageByModelResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.byModel,
    params: toQuery(filters)
  });
}

export function getTokenUsageByKey(apiKeyId: string, filters: ByKeyFilters = {}): Promise<APIKeyUsageDetailsResponse> {
  return adminRequest<APIKeyUsageDetailsResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.byKey(apiKeyId),
    params: {
      provider: filters.provider,
      model: filters.model,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
      granularity: filters.granularity ?? "daily",
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? 20
    }
  });
}

export function getCostForecast(filters: TokenUsageFilters = {}): Promise<CostForecastResponse> {
  return adminRequest<CostForecastResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.costForecast,
    params: toQuery(filters)
  });
}

export function getRecommendations(includeDismissed = false): Promise<OptimizationRecommendationListResponse> {
  return adminRequest<OptimizationRecommendationListResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.recommendations,
    params: {
      include_dismissed: includeDismissed
    }
  });
}

export function dismissRecommendation(id: string): Promise<RecommendationDismissResponse> {
  return adminRequest<RecommendationDismissResponse>({
    method: "POST",
    url: TOKEN_MONITORING_ENDPOINTS.dismissRecommendation(id)
  });
}

export function getSavingsReport(): Promise<OptimizationSavingsReportResponse> {
  return adminRequest<OptimizationSavingsReportResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.savingsReport
  });
}

export function getActiveAlerts(): Promise<ActiveBudgetAlertsResponse> {
  return adminRequest<ActiveBudgetAlertsResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.activeAlerts
  });
}

export function updateApiKeyBudget(apiKeyId: string, payload: BudgetUpdatePayload): Promise<APIKeyBudgetConfigResponse> {
  return adminRequest<APIKeyBudgetConfigResponse, BudgetUpdatePayload>({
    method: "PUT",
    url: TOKEN_MONITORING_ENDPOINTS.updateBudget(apiKeyId),
    data: payload
  });
}

export function listApiKeys(params: {
  search?: string;
  provider?: string;
  isActive?: boolean;
  limit?: number;
} = {}): Promise<APIKeyListResponse> {
  return adminRequest<APIKeyListResponse>({
    method: "GET",
    url: TOKEN_MONITORING_ENDPOINTS.apiKeys,
    params: {
      search: params.search,
      provider: params.provider,
      is_active: params.isActive,
      limit: params.limit ?? 500
    }
  });
}

export async function streamTokenUsageRealtime(params: {
  onUsage: (event: TokenUsageRealtimeEvent) => void;
  onHeartbeat?: (timestamp: string) => void;
  onError?: (error: unknown) => void;
  signal: AbortSignal;
}): Promise<void> {
  const token = getAdminAccessToken();
  if (!token) {
    throw new Error("Admin auth token is missing");
  }

  const endpointUrl = new URL(
    TOKEN_MONITORING_ENDPOINTS.realtime,
    String(adminHttpClient.defaults.baseURL ?? window.location.origin)
  ).toString();
  const response = await fetch(endpointUrl, {
    method: "GET",
    headers: {
      Accept: "text/event-stream",
      Authorization: `Bearer ${token}`
    },
    signal: params.signal
  });
  if (!response.ok) {
    throw new Error(`Realtime stream request failed (${response.status})`);
  }

  const streamValue = response.body;
  if (!streamValue || typeof streamValue.getReader !== "function") {
    throw new Error("Realtime stream is not supported in this runtime.");
  }

  const reader = streamValue.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (!params.signal.aborted) {
    const readResult = await reader.read();
    if (readResult.done) {
      break;
    }

    buffer += decoder.decode(readResult.value, { stream: true });
    const chunks = buffer.split("\n\n");
    buffer = chunks.pop() ?? "";

    for (const chunk of chunks) {
      const lines = chunk.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event:"));
      const dataLine = lines.find((line) => line.startsWith("data:"));
      if (!eventLine || !dataLine) {
        continue;
      }

      const eventName = eventLine.replace("event:", "").trim();
      const eventData = dataLine.replace("data:", "").trim();

      try {
        const parsed = JSON.parse(eventData) as Record<string, unknown>;
        if (eventName === "usage") {
          params.onUsage(toRealtimeEvent(parsed));
        } else if (eventName === "heartbeat") {
          const timestamp = String(parsed.timestamp ?? "");
          params.onHeartbeat?.(timestamp);
        }
      } catch (error) {
        params.onError?.(error);
      }
    }
  }
}
