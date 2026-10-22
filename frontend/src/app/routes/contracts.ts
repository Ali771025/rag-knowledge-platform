export const tokenMonitoringTabs = ["overview", "by-model", "by-key", "alerts", "optimization"] as const;

export type TokenMonitoringTab = (typeof tokenMonitoringTabs)[number];

export const appRoutes = {
  root: "/",
  language: "/language",
  agent: "/agent",
  history: "/history",
  wallet: "/wallet",
  voice: "/voice",
  referral: "/referral",
  profile: "/profile",
  dashboard: "/dashboard",
  funnel: "/funnel",
  admin: {
    login: "/admin/login",
    knowledge: "/admin/knowledge",
    rag: "/admin/rag",
    knowledgeGraph: "/admin/knowledge-graph",
    tokenMonitoring: "/admin/token-monitoring",
    tokenUsageSummary: "/admin/token-usage/summary",
    tokenUsageByModel: "/admin/token-usage/by-model",
    tokenUsageByKey: "/admin/token-usage/by-key/:apiKeyId",
    tokenUsageCostForecast: "/admin/token-usage/cost-forecast",
    tokenUsageRealtime: "/admin/token-usage/realtime",
    apiKeys: "/admin/api-keys",
    apiKeyBudget: "/admin/api-keys/:id/budget",
    alertsActive: "/admin/alerts/active",
    optimizationRecommendations: "/admin/optimization/recommendations",
    optimizationDismiss: "/admin/optimization/dismiss/:id",
    optimizationSavingsReport: "/admin/optimization/savings-report"
  }
} as const;

export function toTokenMonitoringRoute(tab: TokenMonitoringTab): string {
  return `${appRoutes.admin.tokenMonitoring}?tab=${tab}`;
}

