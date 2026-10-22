import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowLeft, Bot, History, LoaderCircle, Wallet } from "lucide-react";
import { appRoutes } from "@/app/routes/contracts";
import { GradientButton, GlassCard, IconButton, MotionPage, PageContainer, ScreenShell, SectionContainer } from "@/components/ui";
import { VoiceBottomActions, VoiceHeroOrb, VoicePulseButton, VoiceStatusPill, VoiceTranscriptPanel, VoiceWaveform } from "@/components/voice";
import { dsMotionVariants } from "@/design-system";
import { useI18n } from "@/i18n";
import { VoiceService } from "@/services/voice";
import { useChatComposerDraftStore } from "@/state";
import { useVoiceSessionStore } from "@/state/voice-session-store";
import { useConfigStore } from "@/state/config-store";
import { useWalletStore } from "@/state/wallet-store";
import type { VoiceUiState } from "./voice-conversation.types";

function createVoiceSessionId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `voice-${Date.now()}`;
}

function mergeTranscript(finalTranscript: string, partialTranscript: string): string {
  const finalText = finalTranscript.trim();
  const partialText = partialTranscript.trim();
  return [finalText, partialText].filter(Boolean).join(" ").trim();
}

function VoiceHeader({
  onBack,
  walletStatus,
  i18n,
  direction
}: {
  onBack: () => void;
  walletStatus: "disconnected" | "connecting" | "connected";
  i18n: ReturnType<typeof useI18n>["messages"];
  direction: "ltr" | "rtl";
}) {
  const backIconClass = ["h-4 w-4", direction === "rtl" ? "rotate-180" : ""].join(" ");
  return (
    <GlassCard className="relative overflow-hidden p-3 sm:p-4">
      <div className="absolute -left-10 top-0 h-24 w-24 rounded-full bg-cyan-500/20 blur-3xl" aria-hidden="true" />
      <div className="flex items-center justify-between gap-2">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-white/15 bg-[color:var(--voice-surface-soft)] px-3 py-2 text-sm text-[color:var(--voice-text-main)] transition hover:border-[color:var(--voice-border)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--voice-accent-cyan)]"
        >
          <ArrowLeft className={backIconClass} aria-hidden="true" />
          {i18n.voice.returnToChat}
        </button>

        <div className="flex min-w-0 items-center gap-2">
          <span className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[color:var(--voice-border)] bg-[color:var(--voice-surface-soft)] text-[color:var(--voice-accent-cyan)]">
            <Bot className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="truncate text-base font-semibold text-[color:var(--voice-text-main)]">{i18n.chatLanding.appWordmark}</span>
        </div>

        <div className="flex items-center gap-2">
          <Link to={appRoutes.history}>
            <IconButton variant="secondary" aria-label={i18n.voice.historyAriaLabel}>
              <History className="h-5 w-5" aria-hidden="true" />
            </IconButton>
          </Link>
          <IconButton variant="secondary" aria-label={i18n.voice.walletAriaLabel}>
            <Wallet className="h-5 w-5" aria-hidden="true" />
          </IconButton>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-end">
        <span
          className={[
            "inline-flex min-h-8 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px]",
            walletStatus === "connected"
              ? "border-emerald-400/35 bg-emerald-500/15 text-emerald-200"
              : "border-white/20 bg-white/10 text-[color:var(--voice-text-muted)]"
          ].join(" ")}
        >
          {walletStatus === "connecting" ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" aria-hidden="true" /> : <Wallet className="h-3.5 w-3.5" aria-hidden="true" />}
          {walletStatus === "connected" ? i18n.profile.walletConnected : i18n.profile.walletDisconnected}
        </span>
      </div>
    </GlassCard>
  );
}

export function VoiceConversationPage() {
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const { messages, direction } = useI18n();
  const config = useConfigStore();
  const locale = config.language;
  const walletStatus = useWalletStore((state) => state.status);
  const setVoiceStatus = useVoiceSessionStore((state) => state.setStatus);
  const voiceStart = useVoiceSessionStore((state) => state.start);
  const voiceComplete = useVoiceSessionStore((state) => state.complete);
  const voiceReset = useVoiceSessionStore((state) => state.reset);
  const setDraft = useChatComposerDraftStore((state) => state.setDraft);

  const [uiState, setUiState] = useState<VoiceUiState>("idle");
  const [volumeLevel, setVolumeLevel] = useState(0);
  const [partialTranscript, setPartialTranscript] = useState("");
  const [finalTranscript, setFinalTranscript] = useState("");
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [lastSpokenTranscript, setLastSpokenTranscript] = useState("");

  const voiceServiceRef = useRef<VoiceService | null>(null);

  useEffect(() => {
    const service = new VoiceService({
      onStateChange: (state) => {
        setUiState(state);
        if (state === "listening") setVoiceStatus("recording");
        if (state === "processing") setVoiceStatus("processing");
        if (state === "speaking") setVoiceStatus("speaking");
        if (state === "idle") setVoiceStatus("idle");
        if (state === "error" || state === "permission_denied") setVoiceStatus("error");
      },
      onTranscriptUpdate: (payload) => {
        setPartialTranscript(payload.partialTranscript);
        setFinalTranscript(payload.finalTranscript);
      },
      onError: () => {
        setUiState("error");
      },
      onVolume: (value) => {
        setVolumeLevel(value);
      }
    });
    service.setLocale(locale);
    service.setTtsEnabled(ttsEnabled);
    voiceServiceRef.current = service;

    return () => {
      service.reset();
      voiceReset();
      voiceServiceRef.current = null;
    };
  }, [locale, setVoiceStatus, ttsEnabled, voiceReset]);

  useEffect(() => {
    voiceServiceRef.current?.setLocale(locale);
  }, [locale]);

  useEffect(() => {
    voiceServiceRef.current?.setTtsEnabled(ttsEnabled);
  }, [ttsEnabled]);

  const transcriptForChat = useMemo(() => mergeTranscript(finalTranscript, partialTranscript), [finalTranscript, partialTranscript]);
  const isListening = uiState === "listening";
  const isActionDisabled = uiState === "processing";

  const safelyStopListening = () => {
    if (!voiceServiceRef.current) return;
    voiceServiceRef.current.stopListening();
    voiceComplete();
  };

  const handleStart = async () => {
    const service = voiceServiceRef.current;
    if (!service) return;
    const sessionId = createVoiceSessionId();
    voiceStart(sessionId);
    await service.startListening();
  };

  const handleStop = () => {
    safelyStopListening();
  };

  useEffect(() => {
    if (!ttsEnabled) return;
    const service = voiceServiceRef.current;
    if (!service) return;
    const spokenCandidate = finalTranscript.trim();
    if (!spokenCandidate || spokenCandidate === lastSpokenTranscript) return;

    setLastSpokenTranscript(spokenCandidate);
    void service.speak(spokenCandidate);
  }, [finalTranscript, lastSpokenTranscript, ttsEnabled]);

  const handleSwitchToTyping = () => {
    safelyStopListening();
    if (transcriptForChat) {
      setDraft(transcriptForChat);
    }
    navigate(appRoutes.agent, { replace: false });
  };

  const handleReturnToChat = () => {
    safelyStopListening();
    navigate(appRoutes.agent, { replace: true });
  };

  const handleClose = () => {
    safelyStopListening();
    navigate(appRoutes.agent, { replace: false });
  };

  return (
    <ScreenShell className="voice-premium-surface">
      <PageContainer className="py-4 sm:py-6">
        <MotionPage>
        <SectionContainer className="mx-auto w-full max-w-[1280px] space-y-3 pb-20 sm:pb-14">
          <motion.div
            variants={shouldReduceMotion ? undefined : dsMotionVariants.fadeIn}
            initial={shouldReduceMotion ? false : "hidden"}
            animate="visible"
          >
            <VoiceHeader onBack={handleReturnToChat} walletStatus={walletStatus} i18n={messages} direction={direction} />
          </motion.div>

          <div className="grid gap-3 lg:grid-cols-[1fr_minmax(0,760px)_1fr]">
            <div className="hidden rounded-3xl border border-white/10 bg-[color:var(--voice-surface)] p-4 lg:block" aria-hidden="true" />

            <GlassCard className="p-4 sm:p-6">
              <motion.header
                className="text-center"
                variants={shouldReduceMotion ? undefined : dsMotionVariants.fadeIn}
                initial={shouldReduceMotion ? false : "hidden"}
                animate="visible"
              >
                <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--voice-text-main)] sm:text-3xl">{messages.voice.pageTitle}</h1>
                <p className="mx-auto mt-2 max-w-2xl text-sm text-[color:var(--voice-text-muted)] sm:text-base">{messages.voice.pageSubtitle}</p>
              </motion.header>

              <div className="mt-4 space-y-4 sm:mt-5 sm:space-y-5">
                <VoiceStatusPill state={uiState} />

                <VoiceHeroOrb state={uiState} />

                <VoicePulseButton
                  state={uiState}
                  disabled={isActionDisabled || uiState === "permission_denied"}
                  onStart={() => {
                    void handleStart();
                  }}
                  onStop={handleStop}
                />

                <VoiceWaveform activeState={uiState} level={volumeLevel} />

                {uiState === "permission_denied" ? (
                  <p className="text-center text-sm text-rose-300">{messages.voice.micPermissionPrompt}</p>
                ) : null}

                <VoiceTranscriptPanel partialTranscript={partialTranscript} finalTranscript={finalTranscript} />

                <div className="flex flex-wrap items-center justify-center gap-2">
                  <button
                    type="button"
                    onClick={() => setTtsEnabled((prev) => !prev)}
                    className="inline-flex min-h-10 items-center rounded-xl border border-white/15 bg-[color:var(--voice-surface-soft)] px-3 text-xs text-[color:var(--voice-text-main)] transition hover:border-[color:var(--voice-border)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--voice-accent-cyan)]"
                  >
                    {ttsEnabled ? messages.voice.ttsToggleOn : messages.voice.ttsToggleOff}
                  </button>
                  <GradientButton size="sm" disabled={!isListening} onClick={handleStop}>
                    {messages.voice.stopLabel}
                  </GradientButton>
                </div>
              </div>
            </GlassCard>

            <div className="hidden rounded-3xl border border-white/10 bg-[color:var(--voice-surface)] p-4 lg:block" aria-hidden="true" />
          </div>

          <VoiceBottomActions onReturn={handleReturnToChat} onSwitchToTyping={handleSwitchToTyping} onClose={handleClose} />
        </SectionContainer>
        </MotionPage>
      </PageContainer>
    </ScreenShell>
  );
}
