import { useEffect, useRef } from "react";
import { Search } from "lucide-react";

interface SidebarSearchProps {
  query: string;
  compact: boolean;
  onQueryChange: (value: string) => void;
  onClear?: () => void;
}

export function SidebarSearch({ query, compact, onQueryChange, onClear }: SidebarSearchProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (compact) return;

    const onKeyDown = (event: KeyboardEvent) => {
      const key = event.key.toLowerCase();
      const withCommand = event.metaKey || event.ctrlKey;
      if (!withCommand || key !== "k") return;
      event.preventDefault();
      inputRef.current?.focus();
      inputRef.current?.select();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [compact]);

  if (compact) {
    return null;
  }

  return (
    <div className="space-y-1">
      <label htmlFor="workspace-sidebar-search" className="sr-only">
        Search conversations
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" aria-hidden="true" />
        <input
          ref={inputRef}
          id="workspace-sidebar-search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          type="search"
          placeholder="Search chats"
          className="h-10 w-full rounded-lg border border-slate-700 bg-slate-900 pl-9 pr-16 text-sm text-slate-100 placeholder:text-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
        />
        {query.trim().length > 0 ? (
          <button
            type="button"
            onClick={onClear}
            className="absolute right-2 top-1/2 -translate-y-1/2 rounded px-2 py-0.5 text-[11px] text-slate-300 hover:bg-slate-800 hover:text-slate-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
            aria-label="Clear search"
          >
            Clear
          </button>
        ) : (
          <span className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-500">
            Ctrl/Cmd K
          </span>
        )}
      </div>
    </div>
  );
}
