import { useState } from "react";
import type { RAGConfig, RAGTestResult } from "@/types/admin";

interface RetrievalTesterPayload {
  query: string;
  labels?: string[];
  topK?: number;
  includeGraphContext: boolean;
}

interface RetrievalTesterProps {
  config: RAGConfig | null;
  result: RAGTestResult | null;
  isTesting?: boolean;
  onTest: (payload: RetrievalTesterPayload) => Promise<void>;
}

function parseLabels(text: string): string[] {
  return text
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function RetrievalTester({ config, result, isTesting = false, onTest }: RetrievalTesterProps) {
  const [query, setQuery] = useState("");
  const [labelsText, setLabelsText] = useState("");
  const [topKOverride, setTopKOverride] = useState<number | "">("");
  const [includeGraphContext, setIncludeGraphContext] = useState(false);

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Retrieval Tester</h2>
      <p className="mt-1 text-sm text-muted-foreground">Run test retrieval with label filters and overrides.</p>

      <div className="mt-3 space-y-3">
        <label className="space-y-1 text-sm">
          <span className="font-medium">Query</span>
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            rows={4}
            placeholder="Ask a question to test retrieval"
            className="w-full rounded-md border border-border px-3 py-2"
          />
        </label>

        <div className="grid gap-3 md:grid-cols-2">
          <label className="space-y-1 text-sm">
            <span className="font-medium">Label filters</span>
            <span className="block text-xs text-muted-foreground">Labels constrain retrieval scope to matching knowledge sources/chunks.</span>
            <input
              type="text"
              value={labelsText}
              onChange={(event) => setLabelsText(event.target.value)}
              placeholder={(config?.defaultLabels ?? []).join(", ") || "support,faq"}
              className="w-full rounded-md border border-border px-3 py-2"
            />
          </label>

          <label className="space-y-1 text-sm">
            <span className="font-medium">topK override</span>
            <input
              type="number"
              min={1}
              max={100}
              value={topKOverride}
              onChange={(event) => {
                const raw = event.target.value;
                setTopKOverride(raw === "" ? "" : Number(raw));
              }}
              placeholder={String(config?.topK ?? 12)}
              className="w-full rounded-md border border-border px-3 py-2"
            />
          </label>
        </div>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={includeGraphContext}
            onChange={(event) => setIncludeGraphContext(event.target.checked)}
          />
          include graph context
        </label>

        <button
          type="button"
          disabled={isTesting || !query.trim()}
          onClick={() => {
            void onTest({
              query: query.trim(),
              labels: parseLabels(labelsText),
              topK: topKOverride === "" ? undefined : topKOverride,
              includeGraphContext
            });
          }}
          className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isTesting ? "Running..." : "Run Retrieval Test"}
        </button>
      </div>

      {result ? (
        <div className="mt-5 space-y-4">
          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-sm font-medium">Generated Answer</p>
            <p className="mt-2 whitespace-pre-wrap text-sm text-foreground">{result.finalAnswer}</p>
          </div>

          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-sm font-medium">Diagnostics</p>
            <pre className="mt-2 overflow-auto text-xs text-foreground">{JSON.stringify(result.diagnostics, null, 2)}</pre>
          </div>

          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-sm font-medium">Retrieved Chunks</p>
            {result.retrievedChunks.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No retrieved chunks.</p>
            ) : (
              <div className="mt-2 space-y-2">
                {result.retrievedChunks.map((chunk) => (
                  <article key={chunk.id} className="rounded-md border border-border bg-background p-3 text-sm">
                    <p className="font-medium">{chunk.sourceTitle ?? chunk.sourceId}</p>
                    <p className="text-xs text-muted-foreground">
                      label: {chunk.label || "-"} | score: {chunk.score.toFixed(4)}
                      {typeof chunk.rerankedScore === "number" ? ` | rerank: ${chunk.rerankedScore.toFixed(4)}` : ""}
                    </p>
                    <p className="mt-2 whitespace-pre-wrap text-foreground">{chunk.content}</p>
                  </article>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-lg border border-border bg-muted/50 p-3">
            <p className="text-sm font-medium">Citations</p>
            {result.citations.length === 0 ? (
              <p className="mt-2 text-sm text-muted-foreground">No citations available.</p>
            ) : (
              <ul className="mt-2 space-y-2 text-sm">
                {result.citations.map((citation, index) => (
                  <li key={`${citation.sourceId}-${index}`} className="rounded-md border border-border bg-background p-3">
                    <p className="font-medium">{citation.sourceTitle ?? citation.sourceId}</p>
                    <p className="text-xs text-muted-foreground">
                      label: {citation.label || "-"} | chunk: {citation.chunkId || "-"}
                    </p>
                    {citation.snippet ? <p className="mt-1 whitespace-pre-wrap">{citation.snippet}</p> : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      ) : null}
    </section>
  );
}
