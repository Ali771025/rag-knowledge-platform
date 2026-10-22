import { type FormEvent, useState } from "react";
import { LabelSelector } from "./label-selector";

interface SourceUploaderProps {
  onSubmit: (formData: FormData) => Promise<void>;
  isSubmitting?: boolean;
}

export function SourceUploader({ onSubmit, isSubmitting = false }: SourceUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [domain, setDomain] = useState("");
  const [label, setLabel] = useState("");
  const [tagsText, setTagsText] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append("document", file);
    formData.append("domain", domain);
    formData.append("label", label);

    const tags = tagsText
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

    for (const tag of tags) {
      formData.append("tags[]", tag);
    }

    await onSubmit(formData);
    setFile(null);
    setTagsText("");
  };

  return (
    <section className="rounded-2xl border border-border bg-background p-4 shadow-sm">
      <h2 className="text-base font-semibold text-foreground">Upload Document</h2>
      <p className="mt-1 text-sm text-muted-foreground">Supported: PDF, DOCX, TXT, MD</p>

      <form className="mt-3 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-document-input">
            File
          </label>
          <input
            id="source-document-input"
            type="file"
            accept=".pdf,.docx,.txt,.md,.markdown"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            required
            className="block w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
          />
        </div>

        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-domain-input">
            Domain
          </label>
          <input
            id="source-domain-input"
            type="text"
            value={domain}
            onChange={(event) => setDomain(event.target.value)}
            placeholder="e.g. customer-support"
            required
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>

        <LabelSelector value={label} onChange={setLabel} disabled={isSubmitting} />

        <div className="space-y-1">
          <label className="text-sm font-medium text-foreground" htmlFor="source-tags-input">
            Tags
          </label>
          <input
            id="source-tags-input"
            type="text"
            value={tagsText}
            onChange={(event) => setTagsText(event.target.value)}
            placeholder="comma,separated,tags"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-primary"
          />
        </div>

        <button
          type="submit"
          disabled={isSubmitting || !file || !domain.trim() || !label.trim()}
          className="inline-flex rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSubmitting ? "Uploading..." : "Upload Source"}
        </button>
      </form>
    </section>
  );
}
