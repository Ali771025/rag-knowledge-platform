import { type FormEvent, useState } from "react";
import { LabelSelector } from "./label-selector";

interface UrlIngestionPayload {
  url: string;
  domain: string;
  label: string;
  tags: string[];
}

interface UrlIngestionFormProps {
  onSubmit: (payload: UrlIngestionPayload) => Promise<void>;
  isSubmitting?: boolean;
}

export function UrlIngestionForm({ onSubmit, isSubmitting = false }: UrlIngestionFormProps) {
  const [url, setUrl] = useState("");
  const [domain, setDomain] = useState("");
  const [label, setLabel] = useState("");
  const [tagsText, setTagsText] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const tags = tagsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    await onSubmit({
      url: url.trim(),
      domain: domain.trim(),
      label: label.trim(),
      tags
    });

    setUrl("");
    setTagsText("");
  };

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Ingest from URL</h2>
      <p className="mt-1 text-sm text-muted-foreground">Queue a website source for ingestion.</p>

      <form className="mt-3 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-url-input">
            URL
          </label>
          <input
            id="source-url-input"
            type="url"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder="https://example.com/docs"
            required
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-url-domain-input">
            Domain
          </label>
          <input
            id="source-url-domain-input"
            type="text"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            placeholder="e.g. knowledge-base"
            required
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>

        <LabelSelector value={label} onChange={setLabel} disabled={isSubmitting} />

        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-url-tags-input">
            Tags
          </label>
          <input
            id="source-url-tags-input"
            type="text"
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
            placeholder="faq,public,product"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !url.trim() || !domain.trim() || !label.trim()}
          className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Submitting..." : "Ingest URL"}
        </button>
      </form>
    </section>
  );
}
