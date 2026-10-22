import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import {
  AudioLines,
  BadgeCheck,
  BookOpen,
  Bot,
  Brain,
  ChevronDown,
  ChevronRight,
  Clock,
  Cpu,
  History,
  LayoutDashboard,
  Menu,
  MessageCircle,
  MessageSquareText,
  Mic,
  Orbit,
  Play,
  Plus,
  PlusCircle,
  Radio,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Sparkles,
  Star,
  Trophy,
  UserPlus,
  UserRound,
  Wallet,
  Waves
} from "lucide-react";
import { createQoraConversation, sendChatMessage, sendQoraMessage } from "@/core/api";
import { appRoutes } from "@/app/routes/contracts";
import {
  Button,
  CardShell,
  EmptyState,
  GradientButton,
  GlassCard,
  IconBadge,
  IconButton,
  LoadingDots,
  MotionList,
  MotionPage,
  PageContainer,
  ScreenShell,
  SectionContainer
} from "@/components/ui";
import { MessageList } from "@/components/chat";
import { dsMotionVariants, dsTypography } from "@/design-system";
import { useI18n } from "@/i18n";
import { FUNNEL_STAGES, type AgentMessage, type Conversation, type ConversationMetadata } from "@/types";
import { useActivationStore, useAdminAuthStore, useChatEntryFlowStore, useFunnelStore, useSessionStore, useWalletStore, useWorkspaceConversationsStore } from "@/state";
import { useChatComposerDraftStore } from "@/state/chat-composer-draft-store";
import { funnelService } from "@/services/funnel";
import { parseHistoryChatEntryNavigationState } from "./chat-entry-flow.types";
import { AGENT_LANDING_CARD_CONFIGS } from "./agent-landing-cards.config";
import { intentToPrompt } from "./agent-landing-intents";
import { resolveAgentEntryContext } from "./agent-landing-entry.utils";
import type {
  AgentCapabilityBadge,
  AgentContextItem,
  AgentEntryContext,
  AgentLandingCardIntent,
  AgentLandingCardKey,
  AgentLandingIconKey,
  ChatEntryChoicePanelCopy,
  AgentNavItemConfig,
  AgentPromptPreset,
  AgentQuickAction,
  ChatEligibilityState,
  TypedFunnelItem
} from "./chat-landing.types";
import { evaluateNewChatEligibility } from "./chat-landing.utils";

const funnelStages = new Set(FUNNEL_STAGES);

interface HeaderMenuItemConfig {
  id: "settings" | "agent" | "history" | "dashboard" | "referral" | "profile";
  to: string;
  label: string;
  ariaLabel: string;
  icon: AgentLandingIconKey | "settings";
}

function createMessageId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `chat-message-${Date.now()}`;
}

function toGateMessage(
  reason: ChatEligibilityState["reasonKey"],
  messages: ReturnType<typeof useI18n>["messages"]
): string {
  switch (reason) {
    case "requires_auth":
      return messages.chatLanding.newChatGateRequiresAuth;
    case "requires_activation":
      return messages.chatLanding.newChatGateRequiresActivation;
    case "requires_initial_interaction":
      return messages.chatLanding.newChatGateRequiresInitialInteraction;
    case "requires_registration":
      return messages.chatLanding.newChatGateRequiresRegistration;
    case "requires_first_tasks":
      return messages.chatLanding.newChatGateRequiresFirstTasks;
    default:
      return "";
  }
}

function iconForKey(key: AgentLandingIconKey, className: string) {
  if (key === "audioLines") return <AudioLines className={className} aria-hidden="true" />;
  if (key === "badgeCheck") return <BadgeCheck className={className} aria-hidden="true" />;
  if (key === "bookOpen") return <BookOpen className={className} aria-hidden="true" />;
  if (key === "bot") return <Bot className={className} aria-hidden="true" />;
  if (key === "brain") return <Brain className={className} aria-hidden="true" />;
  if (key === "cpu") return <Cpu className={className} aria-hidden="true" />;
  if (key === "history") return <History className={className} aria-hidden="true" />;
  if (key === "layoutDashboard") return <LayoutDashboard className={className} aria-hidden="true" />;
  if (key === "messageCircle") return <MessageCircle className={className} aria-hidden="true" />;
  if (key === "mic") return <Mic className={className} aria-hidden="true" />;
  if (key === "radio") return <Radio className={className} aria-hidden="true" />;
  if (key === "search") return <Search className={className} aria-hidden="true" />;
  if (key === "shieldCheck") return <ShieldCheck className={className} aria-hidden="true" />;
  if (key === "sparkles") return <Sparkles className={className} aria-hidden="true" />;
  if (key === "stars") return <Star className={className} aria-hidden="true" />;
  if (key === "trophy") return <Trophy className={className} aria-hidden="true" />;
  if (key === "userPlus") return <UserPlus className={className} aria-hidden="true" />;
  if (key === "userRound") return <UserRound className={className} aria-hidden="true" />;
  if (key === "wallet") return <Wallet className={className} aria-hidden="true" />;
  if (key === "waves") return <Waves className={className} aria-hidden="true" />;
  return <Orbit className={className} aria-hidden="true" />;
}

function directionClass(direction: "ltr" | "rtl", ltrClass: string, rtlClass: string): string {
  return direction === "rtl" ? rtlClass : ltrClass;
}

function formatActionText(value: string): string {
  return value.replaceAll("_", " ");
}

function buildCapabilityBadges(i18n: ReturnType<typeof useI18n>["messages"]): AgentCapabilityBadge[] {
  return [
    { id: "rag", label: i18n.chatLanding.capabilityRag, icon: "sparkles" },
    { id: "memory", label: i18n.chatLanding.capabilityMemory, icon: "search" },
    { id: "voice", label: i18n.chatLanding.capabilityVoice, icon: "audioLines" },
    { id: "walletAware", label: i18n.chatLanding.capabilityWalletAware, icon: "wallet" }
  ];
}

function buildHeaderMenuItems(i18n: ReturnType<typeof useI18n>["messages"]): HeaderMenuItemConfig[] {
  return [
    { id: "settings", to: `${appRoutes.profile}?panel=settings`, label: "Setting", ariaLabel: "Setting", icon: "settings" },
    { id: "history", to: appRoutes.history, label: i18n.chatLanding.navHistory, ariaLabel: i18n.chatLanding.navHistory, icon: "history" },
    { id: "agent", to: appRoutes.agent, label: i18n.chatLanding.navAgent, ariaLabel: i18n.chatLanding.navAgent, icon: "messageCircle" },
    { id: "dashboard", to: appRoutes.dashboard, label: i18n.chatLanding.navDashboard, ariaLabel: i18n.chatLanding.navDashboard, icon: "layoutDashboard" },
    { id: "referral", to: appRoutes.referral, label: i18n.chatLanding.navAddFriend, ariaLabel: i18n.chatLanding.navAddFriend, icon: "userPlus" },
    { id: "profile", to: appRoutes.profile, label: i18n.chatLanding.navProfile, ariaLabel: i18n.chatLanding.navProfile, icon: "userRound" }
  ];
}

function buildPromptPresets(i18n: ReturnType<typeof useI18n>["messages"]): AgentPromptPreset[] {
  return [
    {
      id: "walletRisk",
      title: i18n.chatLanding.promptWalletRiskTitle,
      description: i18n.chatLanding.promptWalletRiskDescription,
      prompt: i18n.chatLanding.promptWalletRiskPrompt,
      icon: "shieldCheck"
    },
    {
      id: "ecosystem",
      title: i18n.chatLanding.promptEcosystemTitle,
      description: i18n.chatLanding.promptEcosystemDescription,
      prompt: i18n.chatLanding.promptEcosystemPrompt,
      icon: "bookOpen"
    },
    {
      id: "earning",
      title: i18n.chatLanding.promptEarningTitle,
      description: i18n.chatLanding.promptEarningDescription,
      prompt: i18n.chatLanding.promptEarningPrompt,
      icon: "trophy"
    },
    {
      id: "continue",
      title: i18n.chatLanding.promptContinueTitle,
      description: i18n.chatLanding.promptContinueDescription,
      prompt: i18n.chatLanding.promptContinuePrompt,
      icon: "history"
    }
  ];
}

function buildSideNavItems(i18n: ReturnType<typeof useI18n>["messages"]): AgentNavItemConfig[] {
  return [
    { id: "agent", to: appRoutes.agent, label: i18n.chatLanding.navAgent, ariaLabel: i18n.chatLanding.navAgent, icon: "messageCircle" },
    { id: "history", to: appRoutes.history, label: i18n.chatLanding.navHistory, ariaLabel: i18n.chatLanding.navHistory, icon: "history" },
    {
      id: "dashboard",
      to: appRoutes.dashboard,
      label: i18n.chatLanding.navDashboard,
      ariaLabel: i18n.chatLanding.navDashboard,
      icon: "layoutDashboard"
    },
    {
      id: "referral",
      to: appRoutes.referral,
      label: i18n.chatLanding.navAddFriend,
      ariaLabel: i18n.chatLanding.navAddFriend,
      icon: "userPlus"
    },
    { id: "voice", to: appRoutes.voice, label: i18n.chatLanding.navVoice, ariaLabel: i18n.chatLanding.navVoice, icon: "mic" },
    { id: "profile", to: appRoutes.profile, label: i18n.chatLanding.navProfile, ariaLabel: i18n.chatLanding.navProfile, icon: "userRound" }
  ];
}

function buildMobileNavItems(i18n: ReturnType<typeof useI18n>["messages"]): AgentNavItemConfig[] {
  return [
    { id: "agent", to: appRoutes.agent, label: i18n.chatLanding.navAgent, ariaLabel: i18n.chatLanding.navAgent, icon: "messageCircle" },
    { id: "history", to: appRoutes.history, label: i18n.chatLanding.navHistory, ariaLabel: i18n.chatLanding.navHistory, icon: "history" },
    { id: "voice", to: appRoutes.voice, label: i18n.chatLanding.navVoice, ariaLabel: i18n.chatLanding.navVoice, icon: "mic" },
    {
      id: "referral",
      to: appRoutes.referral,
      label: i18n.chatLanding.navAddFriend,
      ariaLabel: i18n.chatLanding.navAddFriend,
      icon: "userPlus"
    },
    { id: "profile", to: appRoutes.profile, label: i18n.chatLanding.navProfile, ariaLabel: i18n.chatLanding.navProfile, icon: "userRound" }
  ];
}

function buildQuickActions(i18n: ReturnType<typeof useI18n>["messages"]): AgentQuickAction[] {
  return [
    { id: "dashboard", to: appRoutes.dashboard, label: i18n.chatLanding.quickActionDashboard, icon: "layoutDashboard" },
    { id: "history", to: appRoutes.history, label: i18n.chatLanding.quickActionHistory, icon: "history" },
    { id: "referral", to: appRoutes.referral, label: i18n.chatLanding.quickActionReferral, icon: "userPlus" },
    { id: "voice", to: appRoutes.voice, label: i18n.chatLanding.quickActionVoice, icon: "mic" }
  ];
}

function buildContextItems(i18n: ReturnType<typeof useI18n>["messages"]): AgentContextItem[] {
  return [
    {
      id: "capabilities",
      title: i18n.chatLanding.capabilitiesPanelTitle,
      description: i18n.chatLanding.contextCapabilitiesDescription,
      icon: "cpu"
    },
    {
      id: "memory",
      title: i18n.chatLanding.memoryPanelTitle,
      description: i18n.chatLanding.contextMemoryDescription,
      icon: "history"
    },
    {
      id: "security",
      title: i18n.chatLanding.securityPanelTitle,
      description: i18n.chatLanding.contextSecurityDescription,
      icon: "shieldCheck"
    }
  ];
}

function HeaderNavigationMenu({
  items,
  currentPath,
  direction,
  conversations,
  activeConversationId,
  onConversationSelect
}: {
  items: HeaderMenuItemConfig[];
  currentPath: string;
  direction: "ltr" | "rtl";
  conversations: Conversation[];
  activeConversationId: string | null;
  onConversationSelect: (conversationId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const shouldReduceMotion = useReducedMotion();
  const panelId = "agent-header-menu";
  const menuIconClass = (item: HeaderMenuItemConfig) =>
    item.icon === "settings" ? <Settings className="h-4 w-4" aria-hidden="true" /> : iconForKey(item.icon, "h-4 w-4");
  const recentConversations = useMemo(
    () =>
      conversations
        .filter((conversation) => conversation.status !== "deleted" && conversation.messages.length > 0)
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
        .slice(0, 6),
    [conversations]
  );
  const getConversationTitle = (conversation: Conversation) => {
    const trimmedTitle = conversation.title.trim();
    if (trimmedTitle && trimmedTitle.toLowerCase() !== "untitled conversation") return trimmedTitle;
    const firstUserMessage = conversation.messages.find((message) => message.role === "user")?.text.trim();
    return firstUserMessage || "New conversation";
  };
  const getConversationPreview = (conversation: Conversation) => {
    const lastMessage = conversation.messages[conversation.messages.length - 1]?.text.trim();
    return lastMessage || "No messages yet";
  };

  const menu = (
    <AnimatePresence>
      {open ? (
        <>
          <motion.button
            type="button"
            aria-label="Close menu overlay"
            className="fixed inset-0 z-[70] bg-black/25 backdrop-blur-[2px]"
            initial={shouldReduceMotion ? false : { opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={shouldReduceMotion ? undefined : { opacity: 0 }}
            transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            onClick={() => setOpen(false)}
          />
          <motion.aside
            id={panelId}
            className="fixed bottom-3 left-3 top-3 z-[80] flex w-[min(88vw,336px)] flex-col overflow-hidden rounded-3xl border border-[color:var(--color-border-glow)] bg-[rgba(7,15,31,0.9)] p-3 shadow-[0_28px_80px_rgba(0,0,0,0.5),0_0_36px_rgba(54,224,255,0.18)] backdrop-blur-2xl sm:bottom-5 sm:left-5 sm:top-5"
            initial={shouldReduceMotion ? false : { opacity: 0, x: -42, y: 0, scale: 0.98, filter: "blur(10px)" }}
            animate={{ opacity: 1, x: 0, y: 0, scale: 1, filter: "blur(0px)" }}
            exit={shouldReduceMotion ? undefined : { opacity: 0, x: -38, y: 0, scale: 0.985, filter: "blur(8px)" }}
            transition={{ duration: 0.34, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={["mb-3 flex items-center justify-between gap-3", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}>
              <div>
                <p className="font-display text-sm font-bold text-[color:var(--color-text-main)]">QORA Menu</p>
                <p className="font-code text-[10px] uppercase tracking-wide text-[color:var(--color-text-muted)]">Gemini style drawer</p>
              </div>
              <IconButton variant="secondary" className="h-9 w-9" onClick={() => setOpen(false)} aria-label="Close menu">
                <Menu className="h-4 w-4 rotate-90" aria-hidden="true" />
              </IconButton>
            </div>

            <nav aria-label="Header navigation" className="shrink-0">
              <ul className="space-y-1.5">
                {items.map((item, index) => {
                  const active = currentPath === item.to || (item.id === "settings" && currentPath === appRoutes.profile);
                  return (
                    <motion.li
                      key={`${item.id}-${item.label}`}
                      initial={shouldReduceMotion ? false : { opacity: 0, x: -8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ duration: 0.18, delay: shouldReduceMotion ? 0 : index * 0.035, ease: [0.22, 1, 0.36, 1] }}
                    >
                      <Link
                        to={item.to}
                        aria-label={item.ariaLabel}
                        aria-current={active ? "page" : undefined}
                        onClick={() => setOpen(false)}
                        className={[
                          "wave-button micro-wiggle flex min-h-11 items-center gap-2 rounded-2xl border px-3 py-2 text-sm transition",
                          direction === "rtl" ? "flex-row-reverse text-right" : "",
                          active
                            ? "border-[color:var(--color-border-glow)] bg-gradient-to-r from-[color:var(--color-accent-cyan)]/20 to-[color:var(--color-accent-violet)]/18 text-[color:var(--color-text-main)] shadow-[0_0_24px_rgba(54,224,255,0.14)]"
                            : "border-white/10 bg-white/[0.04] text-[color:var(--color-text-muted)] hover:border-white/25 hover:bg-white/[0.08] hover:text-[color:var(--color-text-main)]"
                        ].join(" ")}
                      >
                        <span
                          className={[
                            "premium-icon-surface inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-xl",
                            active ? "text-cyan-50" : "text-[color:var(--color-accent-cyan)]"
                          ].join(" ")}
                        >
                          {menuIconClass(item)}
                        </span>
                        <span className="font-heading font-semibold">{item.label}</span>
                      </Link>
                    </motion.li>
                  );
                })}
              </ul>
            </nav>

            <div className="mt-4 min-h-0 flex-1 overflow-hidden rounded-2xl border border-white/10 bg-black/18">
              <div className="flex items-center justify-between border-b border-white/10 px-3 py-2">
                <p className="font-heading text-xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">History</p>
                <History className="h-4 w-4 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
              </div>
              <div className="max-h-full overflow-y-auto p-2">
                {recentConversations.length > 0 ? (
                  <ul className="space-y-1.5">
                    {recentConversations.map((conversation, index) => {
                      const active = activeConversationId === conversation.id;
                      return (
                        <motion.li
                          key={conversation.id}
                          initial={shouldReduceMotion ? false : { opacity: 0, x: -8 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.18, delay: shouldReduceMotion ? 0 : 0.16 + index * 0.035, ease: [0.22, 1, 0.36, 1] }}
                        >
                          <button
                            type="button"
                            onClick={() => {
                              onConversationSelect(conversation.id);
                              setOpen(false);
                            }}
                            className={[
                              "group w-full rounded-2xl border px-3 py-2 text-left transition",
                              active
                                ? "border-[color:var(--color-border-glow)] bg-[color:var(--color-accent-cyan)]/12"
                                : "border-transparent bg-white/[0.03] hover:border-white/15 hover:bg-white/[0.07]"
                            ].join(" ")}
                          >
                            <div className="flex items-center gap-2">
                              <MessageSquareText className="h-4 w-4 shrink-0 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
                              <span className="font-heading min-w-0 truncate text-xs font-semibold text-[color:var(--color-text-main)]">
                                {getConversationTitle(conversation)}
                              </span>
                            </div>
                            <p className="font-body mt-1 line-clamp-2 text-[11px] leading-4 text-[color:var(--color-text-muted)]">
                              {getConversationPreview(conversation)}
                            </p>
                          </button>
                        </motion.li>
                      );
                    })}
                  </ul>
                ) : (
                  <div className="rounded-2xl border border-dashed border-white/15 px-3 py-4 text-center">
                    <p className="font-heading text-xs font-semibold text-[color:var(--color-text-main)]">No history yet</p>
                    <p className="font-body mt-1 text-[11px] text-[color:var(--color-text-muted)]">Your recent work appears here.</p>
                  </div>
                )}
              </div>
            </div>
          </motion.aside>
        </>
      ) : null}
    </AnimatePresence>
  );

  return (
    <>
      <IconButton
        variant="secondary"
        className="h-9 w-9 shrink-0 sm:h-10 sm:w-10"
        aria-label={open ? "Close menu" : "Open menu"}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={() => setOpen((previous) => !previous)}
      >
        <motion.span
          animate={open ? "open" : "closed"}
          className="relative flex h-4 w-5 flex-col justify-between"
          variants={{
            closed: {},
            open: {}
          }}
        >
          <motion.span className="block h-0.5 rounded-full bg-current" transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }} variants={{ closed: { rotate: 0, y: 0, width: 20 }, open: { rotate: 45, y: 7, width: 20 } }} />
          <motion.span className="block h-0.5 rounded-full bg-current" transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }} variants={{ closed: { opacity: 1, x: 0, width: 14 }, open: { opacity: 0, x: -8, width: 8 } }} />
          <motion.span className="block h-0.5 rounded-full bg-current" transition={{ duration: 0.24, ease: [0.22, 1, 0.36, 1] }} variants={{ closed: { rotate: 0, y: 0, width: 18 }, open: { rotate: -45, y: -7, width: 20 } }} />
        </motion.span>
      </IconButton>
      {createPortal(menu, document.body)}
    </>
  );
}

function PremiumHeader({
  walletStatus,
  walletAddress,
  onWalletClick,
  i18n,
  direction,
  menuItems,
  currentPath,
  conversations,
  activeConversationId,
  onConversationSelect
}: {
  walletStatus: "disconnected" | "connecting" | "connected";
  walletAddress: string | null;
  onWalletClick: () => void;
  i18n: ReturnType<typeof useI18n>["messages"];
  direction: "ltr" | "rtl";
  menuItems: HeaderMenuItemConfig[];
  currentPath: string;
  conversations: Conversation[];
  activeConversationId: string | null;
  onConversationSelect: (conversationId: string) => void;
}) {
  const walletLabel =
    walletStatus === "connected"
      ? walletAddress ?? i18n.chatLanding.connectedWalletFallback
      : i18n.chatLanding.connectWallet;
  const shouldRevealWalletCode = walletStatus === "connected" && Boolean(walletAddress);

  return (
    <GlassCard className="relative overflow-hidden p-3 sm:p-4 lg:p-5">
      <div className="pointer-events-none absolute inset-x-6 top-0 h-px bg-gradient-to-r from-transparent via-white/45 to-transparent" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-28 top-0 h-24 w-56 rotate-12 bg-gradient-to-r from-transparent via-[color:var(--color-accent-violet)]/16 to-transparent blur-2xl sm:-right-20 sm:h-28 sm:w-64" aria-hidden="true" />
      <div className={["flex items-center justify-between gap-2 sm:gap-3", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}>
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <HeaderNavigationMenu
            items={menuItems}
            currentPath={currentPath}
            direction={direction}
            conversations={conversations}
            activeConversationId={activeConversationId}
            onConversationSelect={onConversationSelect}
          />
          <span className="premium-icon-surface relative inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--color-border-glow)] text-[color:var(--color-accent-cyan)] sm:h-12 sm:w-12">
            <Sparkles className="absolute right-1.5 top-1.5 h-3 w-3 text-white/80" aria-hidden="true" />
            <Bot className="h-5 w-5 sm:h-6 sm:w-6" aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <p className="font-display truncate text-sm font-bold tracking-wide text-[color:var(--color-text-main)] sm:text-base lg:text-lg">{i18n.chatLanding.appWordmark}</p>
            <span className="font-code inline-flex max-w-full items-center gap-1.5 truncate rounded-full border border-emerald-300/25 bg-emerald-400/10 px-2 py-0.5 text-[10px] text-emerald-100 shadow-[0_0_18px_rgba(16,185,129,0.16)] sm:text-xs">
              <span className="agent-orb-pulse inline-flex h-1.5 w-1.5 rounded-full bg-emerald-300" />
              <Radio className="h-3 w-3" aria-hidden="true" />
              {i18n.chatLanding.onlineStatus}
            </span>
          </div>
        </div>

        <div className={["hidden items-center gap-2 md:flex", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}>
          <GradientButton
            size="md"
            className="shrink-0"
            onClick={onWalletClick}
            disabled={walletStatus === "connected" || walletStatus === "connecting"}
            loading={walletStatus === "connecting"}
            leadingIcon={<Wallet className="h-4 w-4" aria-hidden="true" />}
          >
            {walletStatus === "connected" ? i18n.chatLanding.connectedWalletLabel : i18n.chatLanding.connectWallet}
          </GradientButton>
          {shouldRevealWalletCode ? (
            <div className="wallet-drawer-code w-[198px] rounded-2xl border border-[color:var(--color-border-glow)] px-3 py-2 shadow-[0_16px_34px_rgba(0,0,0,0.3),0_0_22px_rgba(54,224,255,0.14)] backdrop-blur-xl">
              <span className="font-code block text-[10px] uppercase tracking-wide text-[color:var(--color-text-muted)]">wallet code</span>
              <span className="font-code mt-0.5 block truncate text-xs text-[color:var(--color-text-main)]">{walletAddress ?? ""}</span>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-3 flex md:hidden">
        <div className="flex w-full flex-col gap-2">
          <GradientButton
            className="w-full"
            size="md"
            onClick={onWalletClick}
            disabled={walletStatus === "connected" || walletStatus === "connecting"}
            loading={walletStatus === "connecting"}
            leadingIcon={<Wallet className="h-4 w-4" aria-hidden="true" />}
          >
            {walletLabel}
          </GradientButton>
          {shouldRevealWalletCode ? (
            <div className="wallet-drawer-code rounded-2xl border border-[color:var(--color-border-glow)] px-3 py-2 shadow-[0_16px_34px_rgba(0,0,0,0.3),0_0_22px_rgba(54,224,255,0.14)] backdrop-blur-xl">
            <span className="font-code block text-[10px] uppercase tracking-wide text-[color:var(--color-text-muted)]">wallet code</span>
            <span className="font-code mt-0.5 block truncate text-xs text-[color:var(--color-text-main)]">{walletAddress ?? ""}</span>
          </div>
          ) : null}
        </div>
      </div>
    </GlassCard>
  );
}

function SideRail({
  items,
  currentPath,
  i18n
}: {
  items: AgentNavItemConfig[];
  currentPath: string;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  return (
    <GlassCard className="sticky top-4 hidden h-fit p-2 xl:block">
      <nav aria-label={i18n.chatLanding.sideNavAriaLabel}>
        <ul className="space-y-1.5">
          {items.map((item) => {
            const active = currentPath === item.to;
            return (
              <li key={item.id}>
                <Link
                  to={item.to}
                  aria-label={item.ariaLabel}
                  aria-current={active ? "page" : undefined}
                  className={[
                    "micro-wiggle group flex min-h-11 items-center gap-2 rounded-xl border px-3 py-2 text-sm transition",
                    active
                      ? "nav-orbit-active border-[color:var(--color-border-glow)] bg-gradient-to-r from-[color:var(--color-accent-cyan)]/18 via-[color:var(--color-accent-blue)]/14 to-[color:var(--color-accent-violet)]/18 text-[color:var(--color-text-main)] shadow-[0_10px_30px_rgba(54,224,255,0.12)]"
                      : "border-transparent text-[color:var(--color-text-muted)] hover:border-white/15 hover:bg-white/5 hover:text-[color:var(--color-text-main)]"
                  ].join(" ")}
                >
                  <span
                    className={[
                      "inline-flex h-7 w-7 items-center justify-center rounded-lg",
                      active ? "bg-gradient-to-r from-[color:var(--color-accent-cyan)] to-[color:var(--color-accent-violet)] text-slate-950 shadow-[0_0_18px_rgba(54,224,255,0.38)]" : "premium-icon-surface text-[color:var(--color-text-muted)]"
                    ].join(" ")}
                  >
                    {iconForKey(item.icon, "h-4 w-4")}
                  </span>
                  <span className="font-heading font-semibold">{item.label}</span>
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </GlassCard>
  );
}

function AgentHeroOrb({
  i18n,
  capabilityBadges
}: {
  i18n: ReturnType<typeof useI18n>["messages"];
  capabilityBadges: AgentCapabilityBadge[];
}) {
  return (
    <GlassCard className="relative overflow-hidden p-4 sm:p-5 lg:p-6 xl:p-7">
      <div className="absolute inset-x-8 top-0 h-px bg-gradient-to-r from-transparent via-[color:var(--color-accent-cyan)]/70 to-transparent" aria-hidden="true" />
      <div className="absolute left-0 top-8 h-24 w-full bg-[linear-gradient(110deg,transparent,rgba(54,224,255,0.1),transparent)] blur-xl" aria-hidden="true" />
      <div className="grid items-center gap-5 sm:gap-6 lg:grid-cols-[minmax(0,1fr)_240px] lg:text-left xl:grid-cols-[minmax(0,1fr)_270px]">
        <div className="order-2 space-y-4 text-center sm:space-y-5 lg:order-1 lg:text-left">
          <div className="space-y-2">
            <span className="font-code inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.08] px-3 py-1 text-xs font-medium text-[color:var(--color-text-muted)] shadow-[inset_0_1px_0_rgba(255,255,255,0.12)]">
              <Radio className="h-3.5 w-3.5 text-emerald-200" aria-hidden="true" />
              {i18n.chatLanding.onlineStatus}
            </span>
            <h1 className="font-display kinetic-text bg-gradient-to-r from-white via-cyan-100 via-violet-100 to-white bg-clip-text text-[clamp(2rem,8vw,3rem)] font-bold leading-tight text-transparent lg:text-[clamp(2.65rem,4vw,3.5rem)]">{i18n.chatLanding.agentTitle}</h1>
            <p className="font-body mx-auto max-w-2xl text-sm leading-6 text-[color:var(--color-text-muted)] sm:text-base lg:mx-0">{i18n.chatLanding.agentSubtitle}</p>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-2 lg:justify-start">
            {capabilityBadges.map((badge) => (
              <IconBadge key={badge.id} icon={iconForKey(badge.icon, "h-4 w-4")} label={badge.label} />
            ))}
          </div>
        </div>

        <div className="agent-core-float relative order-1 mx-auto lg:order-2">
          <span className="agent-orb-pulse absolute -inset-4 rounded-full border border-cyan-400/30 sm:-inset-5" aria-hidden="true" />
          <span className="agent-orb-pulse absolute -inset-7 rounded-full border border-indigo-400/20 [animation-delay:450ms] sm:-inset-9" aria-hidden="true" />
          <span className="agent-core-rotate absolute -inset-3 rounded-full border border-dashed border-white/15" aria-hidden="true" />
          <span className="agent-core-rotate absolute -inset-9 rounded-full border border-white/8 [animation-duration:22s] sm:-inset-12" aria-hidden="true" />
          <div className="relative inline-flex h-32 w-32 items-center justify-center rounded-full border border-[color:var(--color-border-glow)] bg-[radial-gradient(circle_at_35%_25%,rgba(255,255,255,0.24),transparent_28%),linear-gradient(145deg,rgba(54,224,255,0.3),rgba(93,124,255,0.25),rgba(165,107,255,0.24)),rgba(5,11,22,0.9)] shadow-[0_0_72px_rgba(54,224,255,0.36),inset_0_1px_0_rgba(255,255,255,0.18)] sm:h-40 sm:w-40 lg:h-48 lg:w-48 xl:h-52 xl:w-52">
            <Bot className="h-12 w-12 text-cyan-100 drop-shadow-[0_0_18px_rgba(54,224,255,0.45)] lg:h-16 lg:w-16" aria-hidden="true" />
            <span className="premium-icon-surface absolute -right-1 top-4 rounded-full p-1.5 text-violet-100">
              <Brain className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="premium-icon-surface absolute bottom-4 -left-1 rounded-full p-1.5 text-cyan-100">
              <Cpu className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="premium-icon-surface absolute -bottom-1 right-5 rounded-full p-1.5 text-blue-100">
              <Waves className="h-4 w-4" aria-hidden="true" />
            </span>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}

function PromptGrid({
  prompts,
  disabled,
  onSelect,
  i18n
}: {
  prompts: AgentPromptPreset[];
  disabled: boolean;
  onSelect: (prompt: string) => void;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <GlassCard className="p-3 sm:p-4">
      <div className="mb-3">
        <h2 className="font-heading text-sm font-semibold text-[color:var(--color-text-main)] sm:text-base">{i18n.chatLanding.promptSectionTitle}</h2>
        <p className="font-body mt-1 text-xs text-[color:var(--color-text-muted)] sm:text-sm">{i18n.chatLanding.promptSectionDescription}</p>
      </div>
      <MotionList className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
        {prompts.map((prompt) => (
          <motion.button
            key={prompt.id}
            type="button"
            variants={shouldReduceMotion ? undefined : dsMotionVariants.card}
            onClick={() => onSelect(prompt.prompt)}
            disabled={disabled}
            className="premium-interactive wave-button micro-wiggle group min-h-24 rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),transparent),var(--color-surface-soft)] p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent-cyan)] disabled:cursor-not-allowed disabled:opacity-55"
          >
            <div className="premium-icon-surface mb-2 inline-flex h-9 w-9 items-center justify-center rounded-xl text-[color:var(--color-accent-cyan)]">
              {iconForKey(prompt.icon, "h-4 w-4")}
            </div>
            <p className="font-heading text-sm font-semibold text-[color:var(--color-text-main)]">{prompt.title}</p>
            <p className="font-body mt-1 text-xs text-[color:var(--color-text-muted)]">{prompt.description}</p>
          </motion.button>
        ))}
      </MotionList>
    </GlassCard>
  );
}

function MessageListPanel({
  messages,
  isSubmitting,
  scrollContainerRef,
  bottomAnchorRef,
  i18n
}: {
  messages: AgentMessage[];
  isSubmitting: boolean;
  scrollContainerRef: React.RefObject<HTMLDivElement>;
  bottomAnchorRef: React.RefObject<HTMLDivElement>;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  return (
    <GlassCard className="flex min-h-[320px] flex-1 flex-col overflow-hidden p-3 sm:min-h-[360px] sm:p-4 lg:min-h-[420px]">
      <div className="mb-3 flex items-center justify-between border-b border-white/10 pb-2">
        <span className="font-code inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">
          <MessageCircle className="h-4 w-4 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
          {i18n.chatLanding.onlineStatus}
        </span>
        <span className="agent-orb-pulse inline-flex h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.85)]" aria-hidden="true" />
      </div>
      <div ref={scrollContainerRef} className="min-h-0 flex-1 overflow-auto overscroll-contain">
        {messages.length === 0 ? (
          <EmptyState title={i18n.chatLanding.emptyTitle} description={i18n.chatLanding.emptyDescription} />
        ) : (
          <MessageList messages={messages} bottomAnchorRef={bottomAnchorRef} />
        )}
      </div>
      {messages.length > 0 ? (
        <div className="font-code mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 px-1 text-xs text-[color:var(--color-text-muted)]">
          <span className="inline-flex items-center gap-1">
            <Clock className="h-3.5 w-3.5" aria-hidden="true" />
            {i18n.chatLanding.chatMetaNow}
          </span>
          <span className="inline-flex items-center gap-1">
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            {i18n.chatLanding.chatMetaSources}
          </span>
          <span className="inline-flex items-center gap-1">
            <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
            {i18n.chatLanding.chatMetaFeedback}
          </span>
        </div>
      ) : null}
      {isSubmitting ? (
        <div className="mt-2 flex items-center gap-2 px-1 pb-1 text-sm text-[color:var(--color-text-muted)]" role="status" aria-live="polite">
          <LoadingDots label={i18n.chatLanding.typingStatus} />
          <span>{i18n.chatLanding.typingStatus}</span>
        </div>
      ) : null}
    </GlassCard>
  );
}

function Composer({
  value,
  disabled,
  onChange,
  onSend,
  onVoice,
  onComposerFocus,
  i18n
}: {
  value: string;
  disabled: boolean;
  onChange: (next: string) => void;
  onSend: () => void;
  onVoice: () => void;
  onComposerFocus: () => void;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  return (
    <GlassCard className="p-2 sm:p-3">
      <div className="grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-end gap-1.5 sm:gap-2">
        <IconButton variant="secondary" className="h-10 w-10 sm:h-11 sm:w-11" aria-label={i18n.chatLanding.addAction}>
          <Plus className="h-5 w-5" aria-hidden="true" />
        </IconButton>
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onPointerDown={(event) => {
            onComposerFocus();
            if (event.currentTarget !== document.activeElement) {
              event.preventDefault();
              event.currentTarget.focus({ preventScroll: true });
            }
          }}
          onFocus={() => {
            onComposerFocus();
            window.requestAnimationFrame(onComposerFocus);
          }}
          placeholder={i18n.chatLanding.messagePlaceholder}
          aria-label={i18n.chatLanding.inputAriaLabel}
          className="font-body min-h-10 w-full min-w-0 resize-none rounded-2xl border border-white/10 bg-black/25 px-3 py-2 text-sm text-[color:var(--color-text-main)] shadow-[inset_0_1px_0_rgba(255,255,255,0.08)] outline-none transition placeholder:text-[color:var(--color-text-muted)] focus:border-[color:var(--color-border-glow)] focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent-cyan)] sm:min-h-11"
          disabled={disabled}
          rows={1}
          onKeyDown={(event) => {
            if (event.key !== "Enter" || event.shiftKey || event.nativeEvent.isComposing) return;
            event.preventDefault();
            onSend();
          }}
        />
        <IconButton variant="secondary" className="h-10 w-10 sm:h-11 sm:w-11" onClick={onVoice} aria-label={i18n.chatLanding.micAriaLabel}>
          <Mic className="h-5 w-5" aria-hidden="true" />
        </IconButton>
        <GradientButton
          className="h-10 min-h-10 w-10 rounded-xl px-0 sm:h-11 sm:w-auto sm:min-h-11 sm:px-4 [&>span]:hidden sm:[&>span]:inline"
          size="md"
          onClick={onSend}
          disabled={disabled || !value.trim()}
          loading={disabled}
          leadingIcon={disabled ? undefined : <Send className="h-4 w-4" aria-hidden="true" />}
          aria-label={i18n.chatLanding.sendAriaLabel}
        >
          {i18n.chatLanding.send}
        </GradientButton>
      </div>
    </GlassCard>
  );
}

function ChatEntryChoicePanel({
  onContinue,
  onStartNew,
  disabled,
  copy,
  direction
}: {
  onContinue: () => void;
  onStartNew: () => void;
  disabled: boolean;
  copy: ChatEntryChoicePanelCopy;
  direction: "ltr" | "rtl";
}) {
  const chevronClass = direction === "rtl" ? "h-4 w-4 rotate-180" : "h-4 w-4";

  return (
    <GlassCard className="p-4 sm:p-5">
      <div className="space-y-2">
        <h3 className="font-heading text-base font-semibold text-[color:var(--color-text-main)] sm:text-lg">{copy.title}</h3>
        <p className="font-body text-sm text-[color:var(--color-text-muted)]">{copy.description}</p>
        <span className="font-code inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 text-xs text-[color:var(--color-text-muted)]">
          <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" />
          {copy.selectedTopicLabel}
        </span>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <GradientButton
          size="md"
          onClick={onContinue}
          disabled={disabled}
          leadingIcon={<Play className="h-4 w-4" aria-hidden="true" />}
        >
          {copy.continueAction}
        </GradientButton>
        <Button
          variant="secondary"
          size="md"
          onClick={onStartNew}
          disabled={disabled}
          className={["min-h-11 border-white/20 bg-[color:var(--color-surface-soft)] text-[color:var(--color-text-main)] hover:bg-white/10", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}
        >
          <PlusCircle className="h-4 w-4" aria-hidden="true" />
          {copy.startNewAction}
          <ChevronRight className={chevronClass} aria-hidden="true" />
        </Button>
      </div>
    </GlassCard>
  );
}

function FunnelVisualizer({
  items,
  showOutline,
  i18n
}: {
  items: TypedFunnelItem[];
  showOutline: boolean;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  const shouldReduceMotion = useReducedMotion();

  return (
    <CardShell className="p-3">
      <p className={[dsTypography.sectionTitle, "font-heading flex items-center gap-2 text-[color:var(--color-text-main)]"].join(" ")}>
        <Orbit className="h-4 w-4 text-[color:var(--color-accent-cyan)]" aria-hidden="true" />
        {i18n.chatLanding.funnelTitle}
      </p>
      <div className="mt-2 min-h-24">
        <div className={`rounded-xl border border-dashed border-[color:var(--color-border-glow)] bg-black/10 p-2 ${showOutline ? "border-[color:var(--color-accent-cyan)]" : ""}`}>
          <ul className="flex flex-wrap gap-2">
            {items.map((item) => (
              <motion.li
                key={item.id}
                variants={shouldReduceMotion ? undefined : dsMotionVariants.listItem}
                initial={shouldReduceMotion ? false : "hidden"}
                animate="visible"
                className="font-code rounded-full border border-white/15 bg-[color:var(--color-surface-soft)] px-2.5 py-1 text-xs text-[color:var(--color-text-main)]"
              >
                {item.label}
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </CardShell>
  );
}

function ContextPanel({
  items,
  quickActions,
  walletStatus,
  walletAddress,
  i18n,
  direction
}: {
  items: AgentContextItem[];
  quickActions: AgentQuickAction[];
  walletStatus: "disconnected" | "connecting" | "connected";
  walletAddress: string | null;
  i18n: ReturnType<typeof useI18n>["messages"];
  direction: "ltr" | "rtl";
}) {
  return (
    <GlassCard className="hidden h-fit p-3 2xl:block">
      <div className={["mb-3 flex items-center justify-between", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}>
        <p className="font-heading text-sm font-semibold text-[color:var(--color-text-main)]">{i18n.chatLanding.contextPanelTitle}</p>
        <ChevronDown className={directionClass(direction, "h-4 w-4 text-[color:var(--color-text-muted)]", "h-4 w-4 rotate-180 text-[color:var(--color-text-muted)]")} aria-hidden="true" />
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div key={item.id} className="premium-interactive micro-wiggle rounded-xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),transparent),var(--color-surface-soft)] p-3">
            <span className="premium-icon-surface inline-flex h-8 w-8 items-center justify-center rounded-lg text-[color:var(--color-accent-cyan)]">
              {iconForKey(item.icon, "h-4 w-4")}
            </span>
            <p className="font-heading mt-2 text-sm font-semibold text-[color:var(--color-text-main)]">{item.title}</p>
            <p className="font-body mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{item.description}</p>
          </div>
        ))}
      </div>
      <div className="mt-3 border-t border-white/10 pt-3">
        <p className="font-body mb-2 text-xs text-[color:var(--color-text-muted)]">
          {walletStatus === "connected" ? i18n.profile.walletConnectedStatus : i18n.profile.walletDisconnectedStatus}
        </p>
        {walletStatus === "connected" && walletAddress ? (
          <p className="font-code mb-3 truncate rounded-lg border border-white/10 bg-black/20 px-2 py-1 text-xs text-[color:var(--color-text-main)]">{walletAddress}</p>
        ) : null}
        <p className="font-code text-xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">{i18n.chatLanding.quickActionsTitle}</p>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {quickActions.map((action) => (
            <Link
              key={action.id}
              to={action.to}
              className={[
                "premium-interactive micro-wiggle font-heading inline-flex min-h-11 items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-2 py-2 text-xs text-[color:var(--color-text-main)] hover:border-[color:var(--color-border-glow)]",
                direction === "rtl" ? "flex-row-reverse" : ""
              ].join(" ")}
            >
              {iconForKey(action.icon, "h-4 w-4")}
              {action.label}
            </Link>
          ))}
        </div>
      </div>
    </GlassCard>
  );
}

function MobileBottomNav({
  items,
  currentPath,
  i18n
}: {
  items: AgentNavItemConfig[];
  currentPath: string;
  i18n: ReturnType<typeof useI18n>["messages"];
}) {
  const nav = (
    <nav className="fixed inset-x-0 bottom-2 z-50 mx-auto flex w-[min(calc(100%_-_1rem),520px)] justify-center px-2 sm:bottom-3 lg:hidden" aria-label={i18n.chatLanding.mobileNavAriaLabel}>
      <GlassCard className="w-full rounded-2xl p-1.5 sm:p-2">
        <ul className="grid grid-cols-5 gap-1.5 sm:gap-2">
          {items.map((item) => {
            const active = currentPath === item.to;
            return (
              <li key={item.id} className="min-w-0">
                <Link
                  to={item.to}
                  aria-current={active ? "page" : undefined}
                  aria-label={item.ariaLabel}
                  className="wave-button micro-wiggle group inline-flex min-h-10 w-full flex-col items-center justify-center gap-0.5 rounded-xl px-0.5 sm:min-h-11 sm:gap-1"
                >
                  <span
                    className={[
                      "inline-flex h-8 w-8 items-center justify-center rounded-lg transition",
                      active
                        ? "bg-gradient-to-r from-[color:var(--color-accent-cyan)] to-[color:var(--color-accent-violet)] text-slate-950 shadow-[0_0_18px_rgba(54,224,255,0.38)]"
                        : "premium-icon-surface text-[color:var(--color-text-muted)]"
                    ].join(" ")}
                  >
                    {iconForKey(item.icon, "h-4 w-4")}
                  </span>
                  <span
                    className={[
                      "max-w-full truncate px-0.5 text-[8.5px] sm:text-[10px]",
                      active ? "font-heading font-semibold text-[color:var(--color-text-main)]" : "font-body text-[color:var(--color-text-muted)]"
                    ].join(" ")}
                  >
                    {item.label}
                  </span>
                </Link>
              </li>
            );
          })}
        </ul>
      </GlassCard>
    </nav>
  );

  return createPortal(nav, document.body);
}

function getInviteTokenFromSearch(search: string): string | null {
  const params = new URLSearchParams(search);
  const inviteToken =
    params.get("invite") ??
    params.get("inviteToken") ??
    params.get("ref") ??
    params.get("referral") ??
    params.get("code");

  if (!inviteToken) {
    return null;
  }

  const trimmed = inviteToken.trim();
  return trimmed.length > 0 ? trimmed : null;
}

type AgentCardGateReason = "auth" | "wallet" | "activation" | "onboarding" | null;

function resolveCardGateReason(input: {
  requiresAuth: boolean;
  requiresWallet: boolean;
  isAuthenticated: boolean;
  walletStatus: "disconnected" | "connecting" | "connected";
  activationStatus: "unknown" | "active" | "inactive";
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
}): AgentCardGateReason {
  if (input.requiresAuth && !input.isAuthenticated) {
    return "auth";
  }

  if (input.requiresWallet && input.walletStatus !== "connected") {
    return "wallet";
  }

  if (input.activationStatus !== "active") {
    return "activation";
  }

  if (!input.initialInteractionCompleted || !input.registrationCompleted || !input.firstTasksReceived) {
    return "onboarding";
  }

  return null;
}

function AgentLandingCardGrid({
  isAuthenticated,
  walletStatus,
  activationStatus,
  initialInteractionCompleted,
  registrationCompleted,
  firstTasksReceived,
  onWalletClick,
  onIntent,
  onNavigate,
  i18n,
  direction
}: {
  isAuthenticated: boolean;
  walletStatus: "disconnected" | "connecting" | "connected";
  activationStatus: "unknown" | "active" | "inactive";
  initialInteractionCompleted: boolean;
  registrationCompleted: boolean;
  firstTasksReceived: boolean;
  onWalletClick: () => void;
  onIntent: (intent: AgentLandingCardIntent) => void;
  onNavigate: (to: string) => void;
  i18n: ReturnType<typeof useI18n>["messages"];
  direction: "ltr" | "rtl";
}) {
  const getCardCopy = (cardKey: AgentLandingCardKey) => i18n.agentLanding.cards[cardKey];
  const chevronClass = direction === "rtl" ? "h-3.5 w-3.5 rotate-180" : "h-3.5 w-3.5";
  const shouldReduceMotion = useReducedMotion();

  return (
    <GlassCard className="p-3 sm:p-4">
      <div className="mb-3">
        <h2 className="font-heading text-sm font-semibold text-[color:var(--color-text-main)] sm:text-base">{i18n.agentLanding.cardsSectionTitle}</h2>
        <p className="font-body mt-1 text-xs text-[color:var(--color-text-muted)] sm:text-sm">{i18n.agentLanding.cardsSectionSubtitle}</p>
      </div>
      <MotionList className="grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
        {AGENT_LANDING_CARD_CONFIGS.map((card) => {
          const cardCopy = getCardCopy(card.key);
          const gateReason = resolveCardGateReason({
            requiresAuth: Boolean(card.requiresAuth),
            requiresWallet: Boolean(card.requiresWallet),
            isAuthenticated,
            walletStatus,
            activationStatus,
            initialInteractionCompleted,
            registrationCompleted,
            firstTasksReceived
          });
          const CardIcon = card.icon;
          const gateDescription =
            gateReason === "wallet"
              ? i18n.agentLanding.gating.walletRequired
              : gateReason === "activation"
                ? i18n.agentLanding.gating.activationRequired
                : gateReason === "onboarding"
                  ? i18n.agentLanding.gating.onboardingRequired
                  : gateReason === "auth"
                    ? i18n.chatLanding.newChatGateRequiresAuth
                    : null;
          const gateActionLabel =
            gateReason === "wallet"
              ? i18n.agentLanding.gating.connectWallet
              : gateReason === "activation"
                ? i18n.agentLanding.gating.completeActivation
                : gateReason === "onboarding"
                  ? i18n.agentLanding.gating.continueOnboarding
                  : gateReason === "auth"
                    ? i18n.agentLanding.gating.connectWallet
                    : null;

          return (
            <motion.button
              key={card.key}
              type="button"
              variants={shouldReduceMotion ? undefined : dsMotionVariants.card}
              onClick={() => {
                if (gateReason === "wallet") {
                  onWalletClick();
                  return;
                }

                if (gateReason === "auth" || gateReason === "activation" || gateReason === "onboarding") {
                  onNavigate(appRoutes.profile);
                  return;
                }

                if (card.route) {
                  onNavigate(card.route);
                  return;
                }

                onIntent(card.actionIntent);
              }}
              className="premium-interactive wave-button micro-wiggle group rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.08),transparent_46%),var(--color-surface-soft)] p-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--color-accent-cyan)]"
              aria-label={`${cardCopy.title} ${i18n.agentLanding.cardOpenAction}`}
            >
              <span className="premium-icon-surface inline-flex h-10 w-10 items-center justify-center rounded-xl text-[color:var(--color-accent-cyan)]">
                <CardIcon className="h-5 w-5" aria-hidden="true" />
              </span>
              <p className="font-heading mt-3 text-sm font-semibold text-[color:var(--color-text-main)]">{cardCopy.title}</p>
              <p className="font-body mt-1 text-xs leading-5 text-[color:var(--color-text-muted)]">{cardCopy.description}</p>
              {gateDescription && gateActionLabel ? (
                <div className="mt-3 rounded-xl border border-amber-300/20 bg-amber-400/10 p-2">
                  <p className="font-body text-xs text-amber-100">{gateDescription}</p>
                  <p className="font-heading mt-1 text-xs font-medium text-amber-200">{gateActionLabel}</p>
                </div>
              ) : (
                <span className={["font-code mt-3 inline-flex items-center gap-1 text-xs font-medium text-[color:var(--color-accent-cyan)]", direction === "rtl" ? "flex-row-reverse" : ""].join(" ")}>
                  {i18n.agentLanding.cardOpenAction}
                  <ChevronRight className={chevronClass} aria-hidden="true" />
                </span>
              )}
            </motion.button>
          );
        })}
      </MotionList>
    </GlassCard>
  );
}

function InviteOnboardingAgentLanding({
  isSubmitting,
  onAction,
  i18n,
  direction
}: {
  isSubmitting: boolean;
  onAction: (actionKey: "start" | "nextStep" | "howToStart" | "wantToJoin") => void;
  i18n: ReturnType<typeof useI18n>["messages"];
  direction: "ltr" | "rtl";
}) {
  const actionConfigs = [
    { id: "start", label: i18n.agentLanding.onboarding.start, icon: Sparkles },
    { id: "nextStep", label: i18n.agentLanding.onboarding.nextStep, icon: ChevronRight },
    { id: "howToStart", label: i18n.agentLanding.onboarding.howToStart, icon: BookOpen },
    { id: "wantToJoin", label: i18n.agentLanding.onboarding.wantToJoin, icon: UserPlus }
  ] as const;

  return (
    <GlassCard className="p-4 sm:p-5 lg:p-6">
      <div className="text-center">
        <span className="premium-icon-surface mx-auto mb-3 inline-flex h-11 w-11 items-center justify-center rounded-2xl text-[color:var(--color-accent-cyan)]">
          <Sparkles className="h-5 w-5" aria-hidden="true" />
        </span>
        <p className="font-heading text-lg font-semibold text-[color:var(--color-text-main)]">{i18n.agentLanding.onboarding.title}</p>
        <p className="font-body mt-1 text-sm text-[color:var(--color-text-muted)]">{i18n.agentLanding.onboarding.subtitle}</p>
      </div>
      <div className="mt-4">
        <p className="font-code mb-2 text-xs font-semibold uppercase tracking-wide text-[color:var(--color-text-muted)]">{i18n.agentLanding.onboarding.actionsTitle}</p>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-2 2xl:grid-cols-4">
          {actionConfigs.map((action) => {
            const ActionIcon = action.icon;
            return (
              <Button
                key={action.id}
                variant="secondary"
                size="md"
                disabled={isSubmitting}
                onClick={() => onAction(action.id)}
                className={["micro-wiggle min-h-11 justify-start border-white/15 bg-[color:var(--color-surface-soft)] text-[color:var(--color-text-main)] hover:bg-white/10", direction === "rtl" ? "flex-row-reverse justify-end" : ""].join(" ")}
              >
                <ActionIcon className="h-4 w-4" aria-hidden="true" />
                {formatActionText(action.label)}
              </Button>
            );
          })}
        </div>
      </div>
    </GlassCard>
  );
}

export function ChatLandingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();
  const { messages: i18nMessages, direction } = useI18n();
  const inviteToken = useMemo(() => getInviteTokenFromSearch(location.search), [location.search]);
  const isAuthenticated = useAdminAuthStore((state) => state.isAuthenticated);
  const walletStatus = useWalletStore((state) => state.status);
  const walletAddress = useWalletStore((state) => state.address);
  const setWalletStatus = useWalletStore((state) => state.setStatus);
  const setWalletAddress = useWalletStore((state) => state.setAddress);
  const conversations = useWorkspaceConversationsStore((state) => state.conversations);
  const activeConversationId = useWorkspaceConversationsStore((state) => state.activeConversationId);
  const createConversation = useWorkspaceConversationsStore((state) => state.createConversation);
  const appendMessage = useWorkspaceConversationsStore((state) => state.appendMessage);
  const setActiveConversation = useWorkspaceConversationsStore((state) => state.setActiveConversation);
  const activationStatus = useActivationStore((state) => state.status);
  const initialInteractionCompleted = useActivationStore((state) => state.initialInteractionCompleted);
  const registrationCompleted = useActivationStore((state) => state.registrationCompleted);
  const firstTasksReceived = useActivationStore((state) => state.firstTasksReceived);
  const funnelStage = useSessionStore((state) => state.funnelStage);
  const setFunnelStage = useFunnelStore((state) => state.setStage);
  const draft = useChatComposerDraftStore((state) => state.draft);
  const clearDraft = useChatComposerDraftStore((state) => state.clearDraft);
  const chatEntryMode = useChatEntryFlowStore((state) => state.chatEntryMode);
  const chatEntrySource = useChatEntryFlowStore((state) => state.chatEntrySource);
  const selectedTopicId = useChatEntryFlowStore((state) => state.selectedTopicId);
  const selectedTopicLabel = useChatEntryFlowStore((state) => state.selectedTopicLabel);
  const selectedConversationId = useChatEntryFlowStore((state) => state.selectedConversationId);
  const startHistoryChoice = useChatEntryFlowStore((state) => state.startHistoryChoice);
  const setChatEntryMode = useChatEntryFlowStore((state) => state.setMode);
  const clearChatEntryFlow = useChatEntryFlowStore((state) => state.clear);

  const [value, setValue] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [funnelItems, setFunnelItems] = useState<TypedFunnelItem[]>([]);
  const [showFunnelOutline, setShowFunnelOutline] = useState(false);
  const messageScrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);
  const pageScrollRestoreRef = useRef<{ top: number; stickToBottom: boolean } | null>(null);

  useEffect(() => {
    const applyQualification = (event: Event) => {
      const value = (event as CustomEvent<{ value?: string }>).detail?.value;
      if (value) setValue(value);
    };
    window.addEventListener("qora:qualification-selected", applyQualification);
    return () => window.removeEventListener("qora:qualification-selected", applyQualification);
  }, []);

  const activeConversation = useMemo(
    () => conversations.find((conversation) => conversation.id === activeConversationId) ?? null,
    [activeConversationId, conversations]
  );
  const conversationMessages = activeConversation?.messages ?? [];
  const shouldShowHistoryChoice = chatEntrySource === "history" && chatEntryMode === "history-choice";
  const canResolveHistoryChoice = Boolean(selectedTopicId && selectedTopicLabel);

  const eligibility = useMemo(
    () =>
      evaluateNewChatEligibility({
        isAuthenticated,
        activationStatus,
        initialInteractionCompleted,
        registrationCompleted,
        firstTasksReceived
      }),
    [activationStatus, firstTasksReceived, initialInteractionCompleted, isAuthenticated, registrationCompleted]
  );

  const capabilityBadges = useMemo(() => buildCapabilityBadges(i18nMessages), [i18nMessages]);
  const promptPresets = useMemo(() => buildPromptPresets(i18nMessages), [i18nMessages]);
  const headerMenuItems = useMemo(() => buildHeaderMenuItems(i18nMessages), [i18nMessages]);
  const sideNavItems = useMemo(() => buildSideNavItems(i18nMessages), [i18nMessages]);
  const mobileNavItems = useMemo(() => buildMobileNavItems(i18nMessages), [i18nMessages]);
  const quickActions = useMemo(() => buildQuickActions(i18nMessages), [i18nMessages]);
  const contextItems = useMemo(() => buildContextItems(i18nMessages), [i18nMessages]);
  const chatEntryChoiceCopy: ChatEntryChoicePanelCopy = useMemo(
    () => ({
      title: i18nMessages.chatLanding.historyEntryTitle,
      description: i18nMessages.chatLanding.historyEntryDescription,
      selectedTopicLabel: selectedTopicLabel ?? i18nMessages.chatLanding.historyEntryTopicFallback,
      continueAction: i18nMessages.chatLanding.historyEntryContinue,
      startNewAction: i18nMessages.chatLanding.historyEntryStartNew
    }),
    [i18nMessages, selectedTopicLabel]
  );
  const hasConversationHistory = conversations.length > 1 || conversations.some((conversation) => conversation.messages.length > 0);
  const entryContext: AgentEntryContext = useMemo(
    () =>
      resolveAgentEntryContext({
        inviteToken,
        isAuthenticated,
        activationStatus,
        initialInteractionCompleted,
        registrationCompleted,
        firstTasksReceived,
        hasConversationHistory
      }),
    [
      activationStatus,
      firstTasksReceived,
      hasConversationHistory,
      initialInteractionCompleted,
      inviteToken,
      isAuthenticated,
      registrationCompleted
    ]
  );
  const onboardingContextLabel =
    entryContext === "invite-onboarding"
      ? i18nMessages.agentLanding.entryContext.inviteOnboarding
      : entryContext === "returning-user"
        ? i18nMessages.agentLanding.entryContext.returningUser
        : i18nMessages.agentLanding.entryContext.postRegistration;
  const isRtl = direction === "rtl";

  const restorePageScrollPosition = () => {
    const restorePageScroll = pageScrollRestoreRef.current;
    if (!restorePageScroll) return;

    const maxScrollTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    window.scrollTo(0, restorePageScroll.stickToBottom ? maxScrollTop : Math.min(restorePageScroll.top, maxScrollTop));
  };

  const capturePageScrollPosition = () => {
    const maxScrollTop = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    pageScrollRestoreRef.current = {
      top: window.scrollY,
      stickToBottom: maxScrollTop - window.scrollY < 160
    };
  };

  const keepComposerInPlace = () => {
    if (!pageScrollRestoreRef.current) {
      capturePageScrollPosition();
    }
    window.requestAnimationFrame(restorePageScrollPosition);
    window.setTimeout(restorePageScrollPosition, 80);
  };

  useEffect(() => {
    if (!draft.trim()) return;
    setValue(draft);
    clearDraft();
  }, [clearDraft, draft]);

  useEffect(() => {
    const parsedState = parseHistoryChatEntryNavigationState(location.state);
    if (!parsedState) return;

    startHistoryChoice({
      selectedTopicId: parsedState.selectedTopicId,
      selectedTopicLabel: parsedState.selectedTopicLabel,
      selectedConversationId: parsedState.selectedConversationId
    });
  }, [location.state, startHistoryChoice]);

  useEffect(() => {
    if (activeConversationId || shouldShowHistoryChoice) return;
    createConversation();
  }, [activeConversationId, createConversation, shouldShowHistoryChoice]);

  useEffect(() => {
    if (chatEntrySource !== "history") return;
    if (!canResolveHistoryChoice) {
      clearChatEntryFlow();
    }
  }, [canResolveHistoryChoice, chatEntrySource, clearChatEntryFlow]);

  useLayoutEffect(() => {
    const scrollContainer = messageScrollContainerRef.current;
    const restorePageScroll = pageScrollRestoreRef.current;

    window.requestAnimationFrame(() => {
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }

      if (restorePageScroll) {
        restorePageScrollPosition();
        window.setTimeout(restorePageScrollPosition, 80);
        window.setTimeout(restorePageScrollPosition, 240);
      }
    });
  }, [conversationMessages.length, isSubmitting, shouldReduceMotion]);

  const handleWalletClick = () => {
    if (walletStatus === "connected") return;
    setWalletStatus("connecting");
    window.setTimeout(() => {
      setWalletAddress("0xA11...F9C");
      setWalletStatus("connected");
    }, 350);
  };

  const handleStartNewChat = () => {
    if (!eligibility.canStartNewChat) return;
    createConversation();
    setValue("");
    setFunnelItems([]);
    setShowFunnelOutline(false);
    setFunnelStage("ENTRY");
    clearChatEntryFlow();
  };

  const handleVoiceRoute = () => {
    navigate(appRoutes.voice);
  };

  const handleMenuConversationSelect = (conversationId: string) => {
    setActiveConversation(conversationId);
    clearChatEntryFlow();
    navigate(appRoutes.agent);
  };

  const handleContinueFromHistory = () => {
    if (!selectedConversationId) {
      if (activeConversationId) {
        setChatEntryMode("continue");
        return;
      }
      const metadata: ConversationMetadata | undefined = selectedTopicId
        ? {
            topicId: selectedTopicId,
            topicLabel: selectedTopicLabel ?? undefined
          }
        : undefined;
      createConversation({
        metadata
      });
      setChatEntryMode("continue");
      return;
    }

    setActiveConversation(selectedConversationId);
    setChatEntryMode("continue");
  };

  const handleStartNewFromHistory = () => {
    const metadata: ConversationMetadata | undefined = selectedTopicId
      ? {
          topicId: selectedTopicId,
          topicLabel: selectedTopicLabel ?? undefined
        }
      : undefined;

    createConversation({
      metadata
    });
    setValue("");
    setFunnelItems([]);
    setShowFunnelOutline(false);
    setChatEntryMode("new");
  };

  const handleSend = async () => {
    const trimmed = value.trim();
    if (!trimmed || isSubmitting) return;
    if (!pageScrollRestoreRef.current) {
      capturePageScrollPosition();
    }
    let targetConversationId = activeConversationId;
    if (!targetConversationId) {
      targetConversationId = createConversation();
    }
    if (!targetConversationId) return;

    const userMessage: AgentMessage = {
      id: createMessageId(),
      role: "user",
      text: trimmed,
      createdAt: new Date().toISOString()
    };
    appendMessage(targetConversationId, userMessage);
    setValue("");
    setIsSubmitting(true);
    window.requestAnimationFrame(restorePageScrollPosition);
    if (chatEntrySource === "history" && chatEntryMode !== "history-choice") {
      clearChatEntryFlow();
    }

    try {
      const existingQoraConversationId = activeConversation?.messages
        .map((item) => item.metadata?.qoraConversationId)
        .find((item): item is string => typeof item === "string" && item.length > 0);
      const qoraConversationId = isAuthenticated
        ? existingQoraConversationId ?? await createQoraConversation()
        : null;
      const qoraResponse = qoraConversationId
        ? await sendQoraMessage({
            conversationId: qoraConversationId,
            message: trimmed,
            language: direction === "rtl" ? "fa" : "en"
          })
        : null;
      const legacyResponse = qoraResponse ? null : await sendChatMessage({ message: trimmed });
      const response = qoraResponse ?? legacyResponse!;
      const agentMessage: AgentMessage = {
        id: createMessageId(),
        role: "agent",
        text: response.message,
        createdAt: legacyResponse?.timestamp ?? new Date().toISOString(),
        isStreaming: false,
        metadata: qoraResponse ? {
          qoraConversationId: qoraResponse.conversation_id,
          qoraResponse
        } : undefined
      };
      appendMessage(targetConversationId, agentMessage);

      if (legacyResponse?.funnelStage && funnelStages.has(legacyResponse.funnelStage as (typeof FUNNEL_STAGES)[number])) {
        setFunnelStage(legacyResponse.funnelStage as (typeof FUNNEL_STAGES)[number]);
      }

      const discovered = qoraResponse ? [] : await funnelService.discoverItems({
        assistantMessage: response.message,
        funnelStage: legacyResponse?.funnelStage ?? funnelStage
      });

      setFunnelItems([]);
      setShowFunnelOutline(false);
      for (let index = 0; index < discovered.length; index += 1) {
        const item = discovered[index];
        if (!item) continue;
        await new Promise<void>((resolve) => {
          window.setTimeout(() => {
            setFunnelItems((prev) => [...prev, item]);
            resolve();
          }, 85);
        });
      }

      if (discovered.length > 0) {
        window.setTimeout(() => {
          setShowFunnelOutline(true);
        }, 160);
      }
    } catch {
      appendMessage(targetConversationId, {
        id: createMessageId(),
        role: "system",
        text: direction === "rtl" ? "ارتباط با QORA برقرار نشد. دوباره تلاش کنید." : "QORA is unavailable. Please retry.",
        createdAt: new Date().toISOString(),
        metadata: { errorState: true }
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCardIntent = (intent: AgentLandingCardIntent) => {
    setValue(intentToPrompt(intent));
  };

  const handleOnboardingAction = (actionKey: "start" | "nextStep" | "howToStart" | "wantToJoin") => {
    const actionPrompt =
      actionKey === "start"
        ? "how to start"
        : actionKey === "nextStep"
          ? "next step"
          : actionKey === "howToStart"
            ? "how to start"
            : "want to join";
    setValue(actionPrompt);
  };

  return (
    <ScreenShell className="agent-premium-surface">
      <div className="agent-command-ambient" aria-hidden="true" />
      <div className="agent-command-grid" aria-hidden="true" />
      <div className="agent-constellation-field" aria-hidden="true" />
      <div className="agent-scanline" aria-hidden="true" />
      <PageContainer className="agent-page-container py-3 sm:py-5 lg:py-6">
        <MotionPage>
        <SectionContainer className="relative z-10 mx-auto flex min-h-[calc(100dvh-1.5rem)] w-full max-w-[1540px] flex-col gap-3 pb-24 sm:gap-4 lg:pb-6">
          <motion.div
            variants={shouldReduceMotion ? undefined : dsMotionVariants.fadeIn}
            initial={shouldReduceMotion ? false : "hidden"}
            animate="visible"
          >
            <PremiumHeader
              walletStatus={walletStatus}
              walletAddress={walletAddress}
              onWalletClick={handleWalletClick}
              i18n={i18nMessages}
              direction={direction}
              menuItems={headerMenuItems}
              currentPath={location.pathname}
              conversations={conversations}
              activeConversationId={activeConversationId}
              onConversationSelect={handleMenuConversationSelect}
            />
          </motion.div>

          <div className="grid min-h-0 flex-1 gap-3 xl:gap-4 2xl:grid-cols-[minmax(0,1fr)_300px]">
            <div className="hidden">
              <SideRail items={sideNavItems} currentPath={location.pathname} i18n={i18nMessages} />
            </div>

            <div className="min-h-0 space-y-3 xl:space-y-4">
              <AgentHeroOrb i18n={i18nMessages} capabilityBadges={capabilityBadges} />

              <div className="grid gap-3">
                <div className={["flex flex-wrap items-start justify-between gap-2 sm:gap-3", isRtl ? "sm:flex-row-reverse" : ""].join(" ")}>
                  <div className="min-w-0 flex-1">
                    <Button
                      variant="secondary"
                      size="md"
                      onClick={handleStartNewChat}
                      disabled={!eligibility.canStartNewChat}
                      title={!eligibility.canStartNewChat ? toGateMessage(eligibility.reasonKey, i18nMessages) : undefined}
                      className="min-h-11"
                    >
                      <Plus className="h-4 w-4" aria-hidden="true" />
                      {i18nMessages.chatLanding.newChat}
                    </Button>
                    {!eligibility.canStartNewChat ? (
                      <p className="font-body mt-1 text-xs text-[color:var(--color-text-muted)]">{toGateMessage(eligibility.reasonKey, i18nMessages)}</p>
                    ) : null}
                    <span
                      className={[
                        "font-code mt-2 inline-flex items-center rounded-full border border-white/15 bg-white/5 px-2 py-0.5 text-[10px] text-[color:var(--color-text-muted)] sm:text-xs",
                        isRtl ? "sm:flex-row-reverse" : ""
                      ].join(" ")}
                    >
                      {onboardingContextLabel}
                    </span>
                  </div>
                  <div className="flex w-full items-center gap-2 sm:w-auto">
                    <Link to={appRoutes.history}>
                      <Button variant="ghost" size="md" className="min-h-11 w-full sm:w-auto">
                        <History className="h-4 w-4" aria-hidden="true" />
                        {i18nMessages.chatLanding.conversationHistory}
                      </Button>
                    </Link>
                    <IconButton variant="secondary" aria-label={i18nMessages.chatLanding.profileAriaLabel}>
                      <ChevronDown className={directionClass(direction, "h-4 w-4", "h-4 w-4 rotate-180")} aria-hidden="true" />
                    </IconButton>
                  </div>
                </div>

                {entryContext === "invite-onboarding" ? (
                  <InviteOnboardingAgentLanding
                    isSubmitting={isSubmitting}
                    onAction={handleOnboardingAction}
                    i18n={i18nMessages}
                    direction={direction}
                  />
                ) : (
                  <>
                    <PromptGrid
                      prompts={promptPresets}
                      disabled={isSubmitting}
                      onSelect={(prompt) => setValue(prompt)}
                      i18n={i18nMessages}
                    />

                    <AgentLandingCardGrid
                      isAuthenticated={isAuthenticated}
                      walletStatus={walletStatus}
                      activationStatus={activationStatus}
                      initialInteractionCompleted={initialInteractionCompleted}
                      registrationCompleted={registrationCompleted}
                      firstTasksReceived={firstTasksReceived}
                      onWalletClick={handleWalletClick}
                      onIntent={handleCardIntent}
                      onNavigate={(to) => navigate(to)}
                      i18n={i18nMessages}
                      direction={direction}
                    />
                  </>
                )}

                {shouldShowHistoryChoice ? (
                  <ChatEntryChoicePanel
                    copy={chatEntryChoiceCopy}
                    disabled={!canResolveHistoryChoice || isSubmitting}
                    onContinue={handleContinueFromHistory}
                    onStartNew={handleStartNewFromHistory}
                    direction={direction}
                  />
                ) : null}

                <MessageListPanel
                  messages={conversationMessages}
                  isSubmitting={isSubmitting}
                  scrollContainerRef={messageScrollContainerRef}
                  bottomAnchorRef={bottomAnchorRef}
                  i18n={i18nMessages}
                />

                <FunnelVisualizer items={funnelItems} showOutline={showFunnelOutline} i18n={i18nMessages} />

                {!shouldShowHistoryChoice ? (
                  <Composer
                    value={value}
                    disabled={isSubmitting}
                    onChange={setValue}
                    onSend={() => {
                      void handleSend();
                    }}
                    onVoice={handleVoiceRoute}
                    onComposerFocus={keepComposerInPlace}
                    i18n={i18nMessages}
                  />
                ) : null}
              </div>
            </div>

            <ContextPanel
              items={contextItems}
              quickActions={quickActions}
              walletStatus={walletStatus}
              walletAddress={walletAddress}
              i18n={i18nMessages}
              direction={direction}
            />
          </div>
        </SectionContainer>
        </MotionPage>
      </PageContainer>

      <MobileBottomNav items={mobileNavItems} currentPath={location.pathname} i18n={i18nMessages} />
    </ScreenShell>
  );
}
