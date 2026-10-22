import { useMemo, useState } from "react";
import type { RAGConfig } from "@/types/admin";

interface RagConfigEditorProps {
  config: RAGConfig | null;
  isLoading?: boolean;
  isSaving?: boolean;
  onSave: (nextConfig: RAGConfig) => Promise<void>;
}

function normalizeLabels(input: string): string[] {
  return input
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function RagConfigEditor({ config, isLoading = false, isSaving = false, onSave }: RagConfigEditorProps) {
  const [draft, setDraft] = useState<RAGConfig | null>(null);

  const active = useMemo(() => draft ?? config, [config, draft]);

  if (isLoading) {
    return (
      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <p className="text-sm text-muted-foreground">Loading RAG configuration...</p>
      </section>
    );
  }

  if (!active) {
    return (
      <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
        <p className="text-sm text-muted-foreground">RAG configuration is unavailable.</p>
      </section>
    );
  }

  const labelsText = active.defaultLabels.join(", ");

  const setField = <K extends keyof RAGConfig>(key: K, value: RAGConfig[K]) => {
    setDraft({
      ...(active as RAGConfig),
      [key]: value
    });
  };

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-foreground">RAG Configuration</h2>
          <p className="text-sm text-muted-foreground">Persisted admin defaults for retrieval and ranking.</p>
        </div>
        <button
          type="button"
          disabled={isSaving}
          onClick={() => {
            void onSave(active);
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSaving ? "Saving..." : "Save Config"}
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium">chunkSize</span>
          <input
            type="number"
            value={active.chunkSize}
            min={128}
            max={8192}
            onChange={(event) => setField("chunkSize", Number(event.target.value))}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium">chunkOverlap</span>
          <input
            type="number"
            value={active.chunkOverlap}
            min={0}
            max={2048}
            onChange={(event) => setField("chunkOverlap", Number(event.target.value))}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium">topK</span>
          <input
            type="number"
            value={active.topK}
            min={1}
            max={100}
            onChange={(event) => setField("topK", Number(event.target.value))}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium">similarityThreshold</span>
          <input
            type="number"
            step="0.01"
            value={active.similarityThreshold}
            min={0}
            max={1}
            onChange={(event) => setField("similarityThreshold", Number(event.target.value))}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium">embeddingModel</span>
          <select
            value={active.embeddingModel}
            onChange={(event) => setField("embeddingModel", event.target.value as RAGConfig["embeddingModel"])}
            className="w-full rounded-md border border-border px-3 py-2"
          >
            <option value="text-embedding-3-large">text-embedding-3-large</option>
            <option value="bge-m3">bge-m3</option>
          </select>
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium">rerankerModel</span>
          <input
            type="text"
            value={active.rerankerModel}
            onChange={(event) => setField("rerankerModel", event.target.value)}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className="font-medium">vectorCollectionName</span>
          <input
            type="text"
            value={active.vectorCollectionName}
            onChange={(event) => setField("vectorCollectionName", event.target.value)}
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="space-y-1 text-sm md:col-span-2">
          <span className="font-medium">defaultLabels</span>
          <input
            type="text"
            value={labelsText}
            onChange={(event) => setField("defaultLabels", normalizeLabels(event.target.value))}
            placeholder="support,faq,billing"
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={active.rerankerEnabled}
            onChange={(event) => setField("rerankerEnabled", event.target.checked)}
          />
          rerankerEnabled
        </label>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={active.hybridSearchEnabled}
            onChange={(event) => setField("hybridSearchEnabled", event.target.checked)}
          />
          hybridSearchEnabled
        </label>

        <label className="flex items-center gap-2 text-sm md:col-span-2">
          <input
            type="checkbox"
            checked={active.graphEnhancedRetrievalEnabled}
            onChange={(event) => setField("graphEnhancedRetrievalEnabled", event.target.checked)}
          />
          graphEnhancedRetrievalEnabled
        </label>
      </div>
    </section>
  );
}
