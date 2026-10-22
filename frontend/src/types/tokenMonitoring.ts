export type TokenProvider = "openai" | "anthropic" | "deepseek";

export type TimeGranularity = "hourly" | "daily" | "weekly" | "monthly";

export interface TokenUsageSummaryPoint {
  bucket_start: string;
  provider: TokenProvider;
  model_name: string;
  api_key_id: string | null;
  total_cost_usd: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  request_count: number;
  avg_latency_ms: number;
  cache_hit_rate: number;
}

export interface ProviderCostBreakdown {
  provider: TokenProvider;
  total_cost_usd: string;
}

export interface TokenUsageSummaryResponse {
  granularity: TimeGranularity;
  points: TokenUsageSummaryPoint[];
  provider_cost_breakdown: ProviderCostBreakdown[];
}

export interface ModelUsageMetrics {
  provider: TokenProvider;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  total_cost_usd: string;
  request_count: number;
  avg_latency_ms: number;
  cache_hit_rate: number;
}

export interface TokenUsageByModelResponse {
  items: ModelUsageMetrics[];
}

export interface RecentRequestUsageItem {
  id: string;
  request_id: string | null;
  provider: TokenProvider;
  model_name: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_usd: string;
  latency_ms: number;
  cache_hit: boolean;
  endpoint: string | null;
  session_id: string | null;
  created_at: string;
}

export interface PaginatedRecentRequests {
  page: number;
  page_size: number;
  total: number;
  items: RecentRequestUsageItem[];
}

export interface APIKeyBudgetInfo {
  current_spend_usd: string;
  period: string;
  monthly_budget_usd: string | null;
  alert_thresholds: number[];
}

export interface APIKeyUsageDetailsResponse {
  api_key: {
    id: string;
    provider: TokenProvider;
    display_name: string;
    key_alias: string | null;
    key_fingerprint: string;
    is_active: boolean;
  };
  time_series: TokenUsageSummaryPoint[];
  recent_requests: PaginatedRecentRequests;
  budget: APIKeyBudgetInfo | null;
}

export interface CostForecastResponse {
  current_spend_usd: string;
  projected_spend_usd: string;
  confidence: "low" | "medium" | "high";
  confidence_note: string;
  period_start: string;
  period_end: string;
}

export interface TokenUsageRealtimeEvent {
  timestamp: string;
  provider: TokenProvider;
  model_name: string;
  api_key_id: string | null;
  tokens_delta: number;
  cost_delta: string;
  latency_ms: number;
  cache_hit: boolean;
}

export interface APIKeyBudgetConfigResponse {
  api_key_id: string;
  monthly_budget_usd: string | null;
  alert_thresholds: number[];
  updated_at: string;
}

export interface APIKeyListItem {
  id: string;
  display_name: string;
  key_alias: string | null;
  provider: TokenProvider;
  is_active: boolean;
  key_fingerprint: string;
  monthly_budget_usd: string | null;
  alert_thresholds: number[];
  current_month_spend_usd: string;
  last_used_at: string | null;
}

export interface APIKeyListResponse {
  items: APIKeyListItem[];
}

export interface BudgetUpdatePayload {
  monthly_budget_usd: number | null;
  alert_thresholds: number[];
}

export interface ActiveBudgetAlertItem {
  id: string;
  api_key_id: string;
  key_alias: string | null;
  provider: TokenProvider;
  threshold_percent: number;
  threshold_usd: string;
  current_spend_usd: string;
  budget_usd: string | null;
  triggered_at: string;
  status: string;
  cycle_start: string | null;
  cycle_end: string | null;
  metadata: Record<string, unknown>;
}

export interface ActiveBudgetAlertsResponse {
  items: ActiveBudgetAlertItem[];
}

export type RecommendationCategory = "cost" | "performance" | "reliability" | "caching";
export type RecommendationSeverity = "info" | "warning" | "critical";

export interface OptimizationRecommendationItem {
  id: string;
  api_key_id: string | null;
  category: RecommendationCategory;
  severity: RecommendationSeverity;
  title: string;
  description: string;
  potential_saving_usd: string;
  action_items: string[];
  generated_at: string;
  is_dismissed: boolean;
  dismissed_at: string | null;
  metadata: Record<string, unknown>;
}

export interface OptimizationRecommendationListResponse {
  items: OptimizationRecommendationItem[];
}

export interface RecommendationDismissResponse {
  id: string;
  is_dismissed: boolean;
  dismissed_at: string | null;
}

export interface SavingsByCategory {
  category: RecommendationCategory;
  potential_saving_usd: string;
}

export interface OptimizationSavingsReportResponse {
  total_potential_monthly_savings_usd: string;
  savings_by_category: SavingsByCategory[];
  high_priority_recommendation_count: number;
}
