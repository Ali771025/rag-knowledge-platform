import { Fragment, type ReactNode } from "react";
import type { AgentMessage } from "@/types";

interface MessageContentProps {
  message: AgentMessage;
}

interface MarkdownSegment {
  type: "text" | "code";
  value: string;
  language?: string;
}

const SAFE_LINK_PROTOCOLS = new Set(["http:", "https:", "mailto:"]);

function normalizeLanguage(language: string | undefined): string {
  const trimmed = (language ?? "").trim().toLowerCase();
  return trimmed || "text";
}

function splitMarkdownSegments(text: string): MarkdownSegment[] {
  const segments: MarkdownSegment[] = [];
  const codeBlockPattern = /```([a-zA-Z0-9_-]+)?\n([\s\S]*?)```/g;
  let lastIndex = 0;

  for (const match of text.matchAll(codeBlockPattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      segments.push({ type: "text", value: text.slice(lastIndex, index) });
    }

    segments.push({
      type: "code",
      language: normalizeLanguage(match[1]),
      value: match[2] ?? ""
    });
    lastIndex = index + match[0].length;
  }

  if (lastIndex < text.length) {
    segments.push({ type: "text", value: text.slice(lastIndex) });
  }

  return segments;
}

function isSafeHref(rawHref: string): boolean {
  try {
    const url = new URL(rawHref);
    return SAFE_LINK_PROTOCOLS.has(url.protocol);
  } catch {
    return false;
  }
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const tokenPattern = /(`[^`]+`)|(\[([^\]]+)\]\(([^)\s]+)\))|(https?:\/\/[^\s]+)/g;
  let lastIndex = 0;
  let tokenIndex = 0;

  for (const match of text.matchAll(tokenPattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index));
    }

    const [token] = match;
    const inlineCode = match[1];
    const markdownLabel = match[3];
    const markdownHref = match[4];
    const bareHref = match[5];

    if (inlineCode) {
      nodes.push(
        <code
          key={`${keyPrefix}-inline-code-${tokenIndex}`}
          className="rounded-md border border-slate-600/60 bg-slate-900 px-1.5 py-0.5 font-mono text-[0.85em] text-slate-100"
        >
          {inlineCode.slice(1, -1)}
        </code>
      );
    } else if (markdownHref && markdownLabel && isSafeHref(markdownHref)) {
      nodes.push(
        <a
          key={`${keyPrefix}-inline-link-${tokenIndex}`}
          href={markdownHref}
          target="_blank"
          rel="noreferrer noopener"
          className="text-sky-300 underline decoration-sky-300/60 underline-offset-2 hover:text-sky-200"
        >
          {markdownLabel}
        </a>
      );
    } else if (bareHref && isSafeHref(bareHref)) {
      nodes.push(
        <a
          key={`${keyPrefix}-inline-url-${tokenIndex}`}
          href={bareHref}
          target="_blank"
          rel="noreferrer noopener"
          className="text-sky-300 underline decoration-sky-300/60 underline-offset-2 hover:text-sky-200"
        >
          {bareHref}
        </a>
      );
    } else {
      nodes.push(token);
    }

    tokenIndex += 1;
    lastIndex = index + token.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function renderParagraph(lines: string[], key: string): ReactNode {
  return (
    <p key={key} className="text-[15px] leading-7 text-slate-100">
      {lines.map((line, lineIndex) => (
        <Fragment key={`${key}-line-${lineIndex}`}>
          {renderInlineMarkdown(line, `${key}-line-${lineIndex}`)}
          {lineIndex < lines.length - 1 ? <br /> : null}
        </Fragment>
      ))}
    </p>
  );
}

function renderTextSegment(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const lines = text.split("\n");
  let index = 0;
  let nodeIndex = 0;

  while (index < lines.length) {
    const rawLine = lines[index] ?? "";
    const trimmedLine = rawLine.trim();

    if (trimmedLine.length === 0) {
      index += 1;
      continue;
    }

    const unorderedMatch = rawLine.match(/^\s*[-*]\s+(.*)$/);
    if (unorderedMatch) {
      const items: string[] = [unorderedMatch[1] ?? ""];
      index += 1;

      while (index < lines.length) {
        const next = lines[index] ?? "";
        const nextMatch = next.match(/^\s*[-*]\s+(.*)$/);
        if (!nextMatch) break;
        items.push(nextMatch[1] ?? "");
        index += 1;
      }

      nodes.push(
        <ul key={`${keyPrefix}-ul-${nodeIndex}`} className="list-disc space-y-2 pl-6 text-[15px] leading-7 text-slate-100">
          {items.map((item, itemIndex) => (
            <li key={`${keyPrefix}-ul-${nodeIndex}-${itemIndex}`}>{renderInlineMarkdown(item, `${keyPrefix}-ul-item-${itemIndex}`)}</li>
          ))}
        </ul>
      );
      nodeIndex += 1;
      continue;
    }

    const orderedMatch = rawLine.match(/^\s*(\d+)\.\s+(.*)$/);
    if (orderedMatch) {
      const items: string[] = [orderedMatch[2] ?? ""];
      index += 1;

      while (index < lines.length) {
        const next = lines[index] ?? "";
        const nextMatch = next.match(/^\s*\d+\.\s+(.*)$/);
        if (!nextMatch) break;
        items.push(nextMatch[1] ?? "");
        index += 1;
      }

      nodes.push(
        <ol key={`${keyPrefix}-ol-${nodeIndex}`} className="list-decimal space-y-2 pl-6 text-[15px] leading-7 text-slate-100">
          {items.map((item, itemIndex) => (
            <li key={`${keyPrefix}-ol-${nodeIndex}-${itemIndex}`}>{renderInlineMarkdown(item, `${keyPrefix}-ol-item-${itemIndex}`)}</li>
          ))}
        </ol>
      );
      nodeIndex += 1;
      continue;
    }

    const quoteMatch = rawLine.match(/^\s*>\s?(.*)$/);
    if (quoteMatch) {
      const quoteLines: string[] = [quoteMatch[1] ?? ""];
      index += 1;

      while (index < lines.length) {
        const next = lines[index] ?? "";
        const nextQuote = next.match(/^\s*>\s?(.*)$/);
        if (!nextQuote) break;
        quoteLines.push(nextQuote[1] ?? "");
        index += 1;
      }

      nodes.push(
        <blockquote
          key={`${keyPrefix}-quote-${nodeIndex}`}
          className="border-l-2 border-slate-500/60 pl-4 text-[15px] leading-7 text-slate-300"
        >
          {quoteLines.map((line, lineIndex) => (
            <p key={`${keyPrefix}-quote-${nodeIndex}-${lineIndex}`}>{renderInlineMarkdown(line, `${keyPrefix}-quote-line-${lineIndex}`)}</p>
          ))}
        </blockquote>
      );
      nodeIndex += 1;
      continue;
    }

    const paragraphLines: string[] = [rawLine];
    index += 1;

    while (index < lines.length) {
      const next = lines[index] ?? "";
      const nextTrimmed = next.trim();
      if (
        nextTrimmed.length === 0 ||
        /^\s*[-*]\s+/.test(next) ||
        /^\s*\d+\.\s+/.test(next) ||
        /^\s*>\s?/.test(next)
      ) {
        break;
      }
      paragraphLines.push(next);
      index += 1;
    }

    nodes.push(renderParagraph(paragraphLines, `${keyPrefix}-p-${nodeIndex}`));
    nodeIndex += 1;
  }

  return nodes;
}

export function MessageContent({ message }: MessageContentProps) {
  const segments = splitMarkdownSegments(message.text);

  return (
    <div className="space-y-4">
      {segments.map((segment, index) =>
        segment.type === "code" ? (
          <figure key={`code-${index}`} className="overflow-hidden rounded-2xl border border-slate-700/70 bg-slate-950/80">
            <figcaption className="border-b border-slate-700/70 bg-slate-900/70 px-3 py-2 text-[11px] uppercase tracking-wide text-slate-400">
              {segment.language}
            </figcaption>
            <pre className="max-h-72 overflow-auto p-4 text-[13px] leading-6 text-slate-100">
              <code>{segment.value}</code>
            </pre>
          </figure>
        ) : (
          <div key={`text-${index}`} className="space-y-4">
            {renderTextSegment(segment.value, `segment-${index}`)}
          </div>
        )
      )}
    </div>
  );
}
