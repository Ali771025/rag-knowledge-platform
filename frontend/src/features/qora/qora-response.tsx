import { Award, BookOpen, CheckCircle2, ChevronRight, ShieldAlert, WifiOff } from "lucide-react";
import { recordQoraEvent, startQoraAchievement, type QoraAgentResponse, type QoraCTA } from "@/core/api";

function AgentButton({ cta, onAction, secondary = false }: {
  cta: QoraCTA;
  onAction?: (cta: QoraCTA) => void;
  secondary?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={() => onAction?.(cta)}
      className={[
        "inline-flex min-h-10 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
        secondary ? "border border-white/15 bg-white/5 text-white" : "bg-cyan-300 text-slate-950"
      ].join(" ")}
    >
      {cta.label}
      <ChevronRight className="h-4 w-4 rtl:rotate-180" aria-hidden="true" />
    </button>
  );
}

export function ProgressIndicator({ response }: { response: QoraAgentResponse }) {
  const percent = Math.min((response.progress.step / Math.max(response.progress.total_steps, 1)) * 100, 100);
  return (
    <div className="space-y-1" aria-label={`Step ${response.progress.step} of ${response.progress.total_steps}`}>
      <div className="h-1.5 overflow-hidden rounded-full bg-white/10">
        <div className="h-full bg-cyan-300 transition-[width]" style={{ width: `${percent}%` }} />
      </div>
      <p className="text-xs text-white/55">{response.progress.current_stage.replaceAll("_", " ")}</p>
    </div>
  );
}

export function QualificationOptions({ response, onSelect }: {
  response: QoraAgentResponse;
  onSelect?: (value: string) => void;
}) {
  if (!response.ui.options.length) return null;
  return (
    <div className="grid gap-2 sm:grid-cols-2" role="group">
      {response.ui.options.slice(0, 4).map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onSelect?.(option.value)}
          className="min-h-11 rounded-md border border-white/15 bg-white/5 px-3 text-start text-sm text-white hover:border-cyan-300/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function LevelCard({ response }: { response: QoraAgentResponse }) {
  const card = response.ui.level_card;
  if (!card) return null;
  return (
    <section className="rounded-md border border-white/15 bg-white/5 p-3" aria-label="Level progress">
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 text-sm font-semibold"><Award className="h-4 w-4 text-cyan-300" />Level {card.current_level}</span>
        <span className="text-xs text-white/60">{card.current_points} points</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-black/30">
        <div className="h-full bg-cyan-300" style={{ width: `${card.progress_percent}%` }} />
      </div>
      <p className="mt-2 text-xs text-white/65">{card.progress_hint}</p>
    </section>
  );
}

export function AchievementCard({ response, onAction }: {
  response: QoraAgentResponse;
  onAction?: (cta: QoraCTA) => void;
}) {
  const card = response.ui.achievement_card;
  if (!card) return null;
  return (
    <section className="rounded-md border border-cyan-300/30 bg-cyan-300/5 p-3" aria-label="Next achievement">
      <div className="flex items-start gap-2">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />
        <div className="min-w-0">
          <p className="text-sm font-medium text-white">{card.micro_task.label}</p>
          <p className="mt-1 text-xs text-white/60">Estimated: {card.estimated_points_gain} points</p>
        </div>
      </div>
      <div className="mt-3"><AgentButton cta={card.cta} onAction={onAction} /></div>
    </section>
  );
}

export function SourceCard({ response, onOpen }: {
  response: QoraAgentResponse;
  onOpen?: (sourceId: string) => void;
}) {
  if (!response.sources.length) return null;
  return (
    <div className="space-y-2">
      {response.sources.map((source) => (
        <a
          key={`${source.source_id}:${source.chunk_id ?? "root"}`}
          href={source.url}
          target="_blank"
          rel="noreferrer"
          onClick={() => onOpen?.(source.source_id)}
          className="flex min-h-10 items-center gap-2 rounded-md border border-white/15 bg-white/5 px-3 text-sm text-white hover:border-cyan-300/60"
        >
          <BookOpen className="h-4 w-4 shrink-0 text-cyan-300" aria-hidden="true" />
          <span className="truncate">{source.title ?? source.source_id}</span>
        </a>
      ))}
    </div>
  );
}

export function TrustNotice({ response }: { response: QoraAgentResponse }) {
  if (!response.warnings.includes("insufficient_context")) return null;
  return <p className="flex items-start gap-2 text-xs text-amber-200"><ShieldAlert className="h-4 w-4 shrink-0" />اطلاعات مستند کافی برای ادعای قطعی در دسترس نیست.</p>;
}

export function ComplianceNotice({ response }: { response: QoraAgentResponse }) {
  if (!response.warnings.some((item) => item.includes("compliance"))) return null;
  return <p className="text-xs text-amber-200">این راهنمای عمومی جایگزین بررسی سند رسمی یا مشاوره تخصصی نیست.</p>;
}

export function AgentOfflineState() {
  return <p className="flex items-center gap-2 text-sm text-white/65"><WifiOff className="h-4 w-4" />Agent is unavailable.</p>;
}

export function AgentErrorState({ message }: { message: string }) {
  return <p role="alert" className="text-sm text-red-200">{message}</p>;
}

export function QoraStructuredResponse({ response, onSelect, onAction, onSourceOpen }: {
  response: QoraAgentResponse;
  onSelect?: (value: string) => void;
  onAction?: (cta: QoraCTA) => void;
  onSourceOpen?: (sourceId: string) => void;
}) {
  const selectOption = (value: string) => {
    onSelect?.(value);
    window.dispatchEvent(new CustomEvent("qora:qualification-selected", { detail: { value } }));
  };
  const runAction = (cta: QoraCTA) => {
    onAction?.(cta);
    void recordQoraEvent({
      conversationId: response.conversation_id,
      eventType: "CTA_CLICKED",
      entityType: "CTA",
      entityId: cta.type
    });
    if (cta.type === "START_MICRO_TASK" && response.ui.achievement_card) {
      void startQoraAchievement({
        conversationId: response.conversation_id,
        achievementId: response.ui.achievement_card.achievement_id
      });
    }
    if (cta.target) window.location.assign(cta.target);
  };
  const openSource = (sourceId: string) => {
    onSourceOpen?.(sourceId);
    void recordQoraEvent({
      conversationId: response.conversation_id,
      eventType: "SOURCE_OPENED",
      entityType: "SOURCE",
      entityId: sourceId
    });
  };
  return (
    <div className="mt-3 space-y-3" dir="auto">
      <ProgressIndicator response={response} />
      <QualificationOptions response={response} onSelect={selectOption} />
      <AchievementCard response={response} onAction={runAction} />
      <LevelCard response={response} />
      <SourceCard response={response} onOpen={openSource} />
      <TrustNotice response={response} />
      <ComplianceNotice response={response} />
      {(response.primary_cta || response.secondary_cta) ? (
        <div className="flex flex-wrap gap-2">
          {response.primary_cta ? <AgentButton cta={response.primary_cta} onAction={runAction} /> : null}
          {response.secondary_cta ? <AgentButton cta={response.secondary_cta} onAction={runAction} secondary /> : null}
        </div>
      ) : null}
    </div>
  );
}

export const AgentMessage = QoraStructuredResponse;
export const ProductRecommendationCard = SourceCard;
export const AlternativeProductCard = SourceCard;
export const PrimaryCTA = AgentButton;
export const SecondaryCTA = AgentButton;
