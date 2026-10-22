import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  dismissRecommendation,
  getActiveAlerts,
  getCostForecast,
  getRecommendations,
  getSavingsReport,
  getTokenUsageByKey,
  getTokenUsageByModel,
  getTokenUsageSummary,
  listApiKeys,
  streamTokenUsageRealtime,
  updateApiKeyBudget,
  type TokenUsageFilters
} from "@/services/admin/tokenMonitoringService";
import type { BudgetUpdatePayload, TimeGranularity, TokenUsageRealtimeEvent } from "@/types/tokenMonitoring";

export function useTokenUsageSummary(filters: TokenUsageFilters, granularity: TimeGranularity) {
  return useQuery({
    queryKey: ["token-usage", "summary", filters, granularity],
    queryFn: () => getTokenUsageSummary(filters, granularity)
  });
}

export function useTokenUsageByModel(filters: TokenUsageFilters) {
  return useQuery({
    queryKey: ["token-usage", "by-model", filters],
    queryFn: () => getTokenUsageByModel(filters)
  });
}

export function useTokenUsageByKey(apiKeyId: string | null, filters: TokenUsageFilters) {
  return useQuery({
    queryKey: ["token-usage", "by-key", apiKeyId, filters],
    queryFn: () => {
      if (!apiKeyId) {
        throw new Error("API key ID is required for by-key usage query.");
      }
      return getTokenUsageByKey(apiKeyId, { ...filters });
    },
    enabled: Boolean(apiKeyId)
  });
}

export function useTokenUsageForecast(filters: TokenUsageFilters) {
  return useQuery({
    queryKey: ["token-usage", "forecast", filters],
    queryFn: () => getCostForecast(filters)
  });
}

export function useOptimizationRecommendations() {
  return useQuery({
    queryKey: ["token-usage", "optimization", "recommendations"],
    queryFn: () => getRecommendations(false)
  });
}

export function useOptimizationSavingsReport() {
  return useQuery({
    queryKey: ["token-usage", "optimization", "savings"],
    queryFn: getSavingsReport
  });
}

export function useActiveBudgetAlerts() {
  return useQuery({
    queryKey: ["token-usage", "alerts", "active"],
    queryFn: getActiveAlerts
  });
}

export function useApiKeys(params: { search?: string; provider?: string; isActive?: boolean } = {}) {
  return useQuery({
    queryKey: ["token-usage", "api-keys", params],
    queryFn: () => listApiKeys(params)
  });
}

export function useDismissRecommendation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => dismissRecommendation(id),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["token-usage", "optimization", "recommendations"] }),
        queryClient.invalidateQueries({ queryKey: ["token-usage", "optimization", "savings"] })
      ]);
    }
  });
}

export function useUpdateApiKeyBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ apiKeyId, payload }: { apiKeyId: string; payload: BudgetUpdatePayload }) =>
      updateApiKeyBudget(apiKeyId, payload),
    onSuccess: async (_result, variables) => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["token-usage", "alerts", "active"] }),
        queryClient.invalidateQueries({ queryKey: ["token-usage", "by-key", variables.apiKeyId] })
      ]);
    }
  });
}

export function useRealtimeCounter(enabled: boolean) {
  const [latestEvent, setLatestEvent] = useState<TokenUsageRealtimeEvent | null>(null);
  const [heartbeatAt, setHeartbeatAt] = useState<string | null>(null);
  const [errors, setErrors] = useState(0);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const controller = new AbortController();
    void streamTokenUsageRealtime({
      signal: controller.signal,
      onUsage: (event) => {
        setLatestEvent(event);
      },
      onHeartbeat: (timestamp) => {
        setHeartbeatAt(timestamp);
      },
      onError: () => {
        setErrors((current) => current + 1);
      }
    }).catch(() => {
      if (!controller.signal.aborted) {
        setErrors((current) => current + 1);
      }
    });

    return () => {
      controller.abort();
    };
  }, [enabled]);

  return useMemo(
    () => ({
      latestEvent,
      heartbeatAt,
      errors
    }),
    [errors, heartbeatAt, latestEvent]
  );
}
