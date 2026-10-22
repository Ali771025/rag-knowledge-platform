import { SuggestedPromptCard } from "./suggested-prompt-card";

export interface WelcomePrompt {
  id: string;
  title: string;
  prompt: string;
  description?: string;
}

interface SuggestedPromptGridProps {
  prompts: WelcomePrompt[];
  disabled?: boolean;
  onSelectPrompt: (prompt: WelcomePrompt) => void;
}

export function SuggestedPromptGrid({ prompts, disabled = false, onSelectPrompt }: SuggestedPromptGridProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {prompts.map((prompt) => (
        <SuggestedPromptCard
          key={prompt.id}
          title={prompt.title}
          prompt={prompt.prompt}
          description={prompt.description}
          disabled={disabled}
          onSelect={() => onSelectPrompt(prompt)}
        />
      ))}
    </div>
  );
}
