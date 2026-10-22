import { Navigate, Outlet, createBrowserRouter, useLocation, useRouteError } from "react-router-dom";
import { AppShell } from "../layouts/app-shell";
import { ErrorBoundary } from "@/components/ui";
import { KnowledgeManagementPage } from "@/features/admin-knowledge";
import { KnowledgeGraphPage } from "@/features/admin-knowledge-graph";
import { RagManagementPage } from "@/features/admin-rag";
import { AdminLoginPage } from "@/features/auth";
import { TokenMonitoringPage } from "@/pages/admin/TokenMonitoring";
import { useAdminAuthStore } from "@/state/auth-store";
import { appRoutes, toTokenMonitoringRoute } from "./contracts";
import { LanguagePage } from "@/features/language";
import { routeForPostLanguageEntry, useLanguageStore } from "@/state/language-store";
import { VoiceConversationPage } from "@/features/voice";
import { ChatLandingPage } from "@/features/chat";
import { ConversationHistoryPage } from "@/features/history";
import { ReferralPage } from "@/features/referral";
import { ProfilePage } from "@/features/profile";
import { DashboardPage } from "@/features/dashboard";

function AgentHomePlaceholder() {
  return (
    <div className="h-full w-full">
      <ErrorBoundary
        fallback={
          <section className="rounded-2xl border border-border bg-muted p-6 text-sm text-muted-foreground">
            Chat temporarily unavailable. Reload to retry.
          </section>
        }
      >
        <ChatLandingPage />
      </ErrorBoundary>
    </div>
  );
}

function NotFoundPage() {
  return (
    <main className="flex min-h-full items-center justify-center">
      <section className="w-full rounded-2xl border border-border bg-muted p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Page not found</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This route does not exist yet. Please use the app entry points configured in this phase.
        </p>
      </section>
    </main>
  );
}

function RequireLanguageSelection() {
  const location = useLocation();
  const locale = useLanguageStore((state) => state.locale);

  if (!locale) {
    return <Navigate to={appRoutes.language} replace state={{ from: location }} />;
  }

  return <Outlet />;
}

function RootEntryRedirect() {
  const locale = useLanguageStore((state) => state.locale);
  if (!locale) {
    return <Navigate to={appRoutes.language} replace />;
  }

  return <Navigate to={routeForPostLanguageEntry(locale)} replace />;
}

function SkipLanguageWhenSelected() {
  const location = useLocation();
  const locale = useLanguageStore((state) => state.locale);
  const fromPath = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? null;

  if (locale) {
    const safeDestination =
      fromPath && fromPath !== appRoutes.language ? fromPath : routeForPostLanguageEntry(locale);
    return <Navigate to={safeDestination} replace />;
  }

  return <LanguagePage />;
}

function RouteErrorPage() {
  const error = useRouteError();
  const message = error instanceof Error ? error.message : "Unexpected route error.";
  return (
    <main className="flex min-h-full items-center justify-center p-4">
      <section className="w-full max-w-xl rounded-2xl border border-border bg-muted p-6 shadow-sm">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          The current page hit a runtime error. Reload the page or navigate to a different section.
        </p>
        <pre className="mt-4 overflow-auto rounded-md border border-border bg-background p-3 text-xs text-muted-foreground">{message}</pre>
        <div className="mt-4 flex gap-2">
          <a href="/" className="rounded-md border border-border px-3 py-1.5 text-sm">
            Go to Home
          </a>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="rounded-md border border-border px-3 py-1.5 text-sm"
          >
            Reload
          </button>
        </div>
      </section>
    </main>
  );
}

function RequireAdminAuth() {
  const location = useLocation();
  const isAuthenticated = useAdminAuthStore((state) => state.isAuthenticated);

  if (!isAuthenticated) {
    return <Navigate to={appRoutes.admin.login} replace state={{ from: location }} />;
  }

  return <Outlet />;
}

export const appRouter = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        path: appRoutes.language.slice(1),
        element: <SkipLanguageWhenSelected />
      },
      {
        element: <RequireLanguageSelection />,
        children: [
          {
            index: true,
            element: <RootEntryRedirect />
          },
          {
            path: appRoutes.agent.slice(1),
            element: <AgentHomePlaceholder />
          },
          {
            path: appRoutes.history.slice(1),
            element: <ConversationHistoryPage />
          },
          {
            path: appRoutes.referral.slice(1),
            element: <ReferralPage />
          },
          {
            path: appRoutes.profile.slice(1),
            element: <ProfilePage />
          },
          {
            path: appRoutes.dashboard.slice(1),
            element: <DashboardPage />
          },
          {
            path: appRoutes.voice.slice(1),
            element: <VoiceConversationPage />
          },
          {
            path: appRoutes.admin.login.slice(1),
            element: <AdminLoginPage />
          },
          {
            element: <RequireAdminAuth />,
            children: [
              {
                path: appRoutes.admin.knowledge.slice(1),
                element: <KnowledgeManagementPage />
              },
              {
                path: appRoutes.admin.rag.slice(1),
                element: <RagManagementPage />
              },
              {
                path: appRoutes.admin.knowledgeGraph.slice(1),
                element: <KnowledgeGraphPage />
              },
              {
                path: appRoutes.admin.tokenMonitoring.slice(1),
                element: <TokenMonitoringPage />
              },
              {
                path: appRoutes.admin.tokenUsageSummary.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("overview")} replace />
              },
              {
                path: appRoutes.admin.tokenUsageByModel.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("by-model")} replace />
              },
              {
                path: appRoutes.admin.tokenUsageByKey.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("by-key")} replace />
              },
              {
                path: appRoutes.admin.tokenUsageCostForecast.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("overview")} replace />
              },
              {
                path: appRoutes.admin.tokenUsageRealtime.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("overview")} replace />
              },
              {
                path: appRoutes.admin.apiKeys.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("by-key")} replace />
              },
              {
                path: appRoutes.admin.apiKeyBudget.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("by-key")} replace />
              },
              {
                path: appRoutes.admin.alertsActive.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("alerts")} replace />
              },
              {
                path: appRoutes.admin.optimizationRecommendations.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("optimization")} replace />
              },
              {
                path: appRoutes.admin.optimizationDismiss.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("optimization")} replace />
              },
              {
                path: appRoutes.admin.optimizationSavingsReport.slice(1),
                element: <Navigate to={toTokenMonitoringRoute("optimization")} replace />
              }
            ]
          },
          {
            path: "*",
            element: <NotFoundPage />
          }
        ]
      }
    ]
  }
]);
