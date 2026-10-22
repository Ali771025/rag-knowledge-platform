import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LoadingFallback, NetworkError } from "@/components/ui";
import { getRAGConfig, testRAG, updateRAGConfig } from "@/services/admin/ragService";
import type { RAGConfig, RAGTestResult } from "@/types/admin";
import { RagConfigEditor } from "./components/rag-config-editor";
import { RetrievalTester } from "./components/retrieval-tester";

export function RagManagementPage() {
  const queryClient = useQueryClient();
  const [testResult, setTestResult] = useState<RAGTestResult | null>(null);

  const configQuery = useQuery({
    queryKey: ["admin-rag-config"],
    queryFn: getRAGConfig
  });

  const saveConfigMutation = useMutation({
    mutationFn: (payload: RAGConfig) => updateRAGConfig(payload),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-rag-config"] });
    }
  });

  const testMutation = useMutation({
    mutationFn: testRAG,
    onSuccess: (result) => {
      setTestResult(result);
    }
  });

  return (
    <main className="mx-auto w-full max-w-[1200px] space-y-4 p-4 sm:p-6">
      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Admin RAG Management</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage retrieval defaults and run interactive retrieval tests.</p>
      </section>

      <section className="flex flex-wrap gap-2 text-sm">
        <a href="/admin/knowledge" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Sources
        </a>
        <a href="/admin/rag" className="rounded-md border border-border bg-muted px-3 py-1.5 font-medium">
          RAG Management
        </a>
        <a href="/admin/knowledge-graph" className="rounded-md border border-border px-3 py-1.5">
          Knowledge Graph
        </a>
      </section>

      {configQuery.isLoading ? <LoadingFallback title="Loading RAG configuration" /> : null}

      {configQuery.isError ? (
        <NetworkError
          title="Failed to load RAG configuration"
          message={configQuery.error instanceof Error ? configQuery.error.message : "Unknown error"}
          onRetry={() => {
            void configQuery.refetch();
          }}
        />
      ) : null}

      {!configQuery.isError ? (
        <RagConfigEditor
          config={configQuery.data ?? null}
          isLoading={configQuery.isLoading}
          isSaving={saveConfigMutation.isPending}
          onSave={async (nextConfig) => {
            await saveConfigMutation.mutateAsync(nextConfig);
          }}
        />
      ) : null}

      <RetrievalTester
        config={configQuery.data ?? null}
        result={testResult}
        isTesting={testMutation.isPending}
        onTest={async (payload) => {
          const labels = payload.labels && payload.labels.length > 0 ? payload.labels : undefined;
          await testMutation.mutateAsync({
            query: payload.query,
            labels,
            topK: payload.topK,
            includeGraphContext: payload.includeGraphContext
          });
        }}
      />

      {testResult?.diagnostics?.flags?.graph_fallback_used ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 shadow-sm">
          <p className="font-medium">Graph fallback was applied for this test run.</p>
          <p className="mt-1">
            Neo4j/graph retrieval was unavailable, so the test automatically continued with non-graph retrieval sources.
          </p>
        </section>
      ) : null}

      {testMutation.isError ? (
        <NetworkError
          title="RAG test failed"
          message={testMutation.error instanceof Error ? testMutation.error.message : "Unknown error"}
          onRetry={() => {
            testMutation.reset();
          }}
        />
      ) : null}
    </main>
  );
}
