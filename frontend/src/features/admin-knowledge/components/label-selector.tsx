import { useId } from "react";

interface LabelSelectorProps {
  value: string;
  onChange: (value: string) => void;
  suggestions?: string[];
  placeholder?: string;
  disabled?: boolean;
}

const DEFAULT_SUGGESTIONS = ["product-docs", "support", "engineering", "legal", "billing", "compliance"];

export function LabelSelector({
  value,
  onChange,
  suggestions = DEFAULT_SUGGESTIONS,
  placeholder = "e.g. support-faq",
  disabled = false
}: LabelSelectorProps) {
  const dataListId = useId();

  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-foreground" htmlFor={dataListId}>
        Label
      </label>
      <input
        id={dataListId}
        type="text"
        value={value}
        list={`${dataListId}-suggestions`}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        disabled={disabled}
        required
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-60"
      />
      <datalist id={`${dataListId}-suggestions`}>
        {suggestions.map((item) => (
          <option key={item} value={item} />
        ))}
      </datalist>
      <p className="text-xs text-muted-foreground">Required. Used for chat context and agent memory scoping.</p>
    </div>
  );
}
