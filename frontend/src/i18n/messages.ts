import type { AppLocale } from "./locales";

export interface MessagesSchema {
  common: {
    appName: string;
  };
  language: {
    pageTitle: string;
    pageSubtitle: string;
    continueCta: string;
    selectedA11y: string;
    radioGroupLabel: string;
    switcherLabel: string;
    syncInProgress: string;
    syncFailed: string;
  };
  voice: {
    pageTitle: string;
    pageSubtitle: string;
    liveTranscriptTitle: string;
    liveTranscriptPlaceholder: string;
    close: string;
    walletAriaLabel: string;
    historyAriaLabel: string;
    returnToChat: string;
    switchToTyping: string;
    startListening: string;
    stopListening: string;
    startLabel: string;
    stopLabel: string;
    listeningStatus: string;
    processingStatus: string;
    speakingStatus: string;
    idleStatus: string;
    permissionDeniedStatus: string;
    errorStatus: string;
    micPermissionPrompt: string;
    transcriptEmptyState: string;
    transcriptPartialLabel: string;
    transcriptFinalLabel: string;
    ttsToggleOn: string;
    ttsToggleOff: string;
      visualizerLabel: string;
  };
  chatLanding: {
    newChat: string;
    appWordmark: string;
    onlineStatus: string;
    agentTitle: string;
    agentSubtitle: string;
    connectedWalletLabel: string;
    connectWallet: string;
    connectedWalletFallback: string;
    conversationHistory: string;
    profileAriaLabel: string;
    menuAriaLabel: string;
    sideNavAriaLabel: string;
    mobileNavAriaLabel: string;
    contextPanelTitle: string;
    capabilitiesPanelTitle: string;
    memoryPanelTitle: string;
    securityPanelTitle: string;
    contextCapabilitiesDescription: string;
    contextMemoryDescription: string;
    contextSecurityDescription: string;
    quickActionsTitle: string;
    quickActionDashboard: string;
    quickActionHistory: string;
    quickActionReferral: string;
    quickActionVoice: string;
    capabilityRag: string;
    capabilityMemory: string;
    capabilityVoice: string;
    capabilityWalletAware: string;
    promptWalletRiskTitle: string;
    promptWalletRiskDescription: string;
    promptWalletRiskPrompt: string;
    promptEcosystemTitle: string;
    promptEcosystemDescription: string;
    promptEcosystemPrompt: string;
    promptEarningTitle: string;
    promptEarningDescription: string;
    promptEarningPrompt: string;
    promptContinueTitle: string;
    promptContinueDescription: string;
    promptContinuePrompt: string;
    promptSectionTitle: string;
    promptSectionDescription: string;
    emptyTitle: string;
    emptyDescription: string;
    chatMetaNow: string;
    chatMetaSources: string;
    chatMetaFeedback: string;
    funnelTitle: string;
    addAction: string;
    micAriaLabel: string;
    sendAriaLabel: string;
    inputAriaLabel: string;
    messagePlaceholder: string;
    send: string;
    voice: string;
    navAgent: string;
    navHistory: string;
    navDashboard: string;
    navAddFriend: string;
    navVoice: string;
    navProfile: string;
    newChatGateRequiresAuth: string;
    newChatGateRequiresActivation: string;
    newChatGateRequiresInitialInteraction: string;
    newChatGateRequiresRegistration: string;
    newChatGateRequiresFirstTasks: string;
    typingStatus: string;
    historyPlaceholderTitle: string;
    historyPlaceholderDescription: string;
    referralPlaceholderTitle: string;
    referralPlaceholderDescription: string;
    historyEntryTitle: string;
    historyEntryDescription: string;
    historyEntryTopicFallback: string;
    historyEntryContinue: string;
    historyEntryStartNew: string;
  };
  agentLanding: {
    cardsSectionTitle: string;
    cardsSectionSubtitle: string;
    cardOpenAction: string;
    cards: {
      myStatusNextBestAction: {
        title: string;
        description: string;
      };
      earnViaMicrotasks: {
        title: string;
        description: string;
      };
      securityRiskCheck: {
        title: string;
        description: string;
      };
      investingStrategy: {
        title: string;
        description: string;
      };
      referralTeamGrowth: {
        title: string;
        description: string;
      };
      qora101EcosystemGuide: {
        title: string;
        description: string;
      };
      helpTroubleshooting: {
        title: string;
        description: string;
      };
    };
    onboarding: {
      title: string;
      subtitle: string;
      start: string;
      nextStep: string;
      howToStart: string;
      wantToJoin: string;
      actionsTitle: string;
    };
    gating: {
      connectWallet: string;
      completeActivation: string;
      continueOnboarding: string;
      walletRequired: string;
      activationRequired: string;
      onboardingRequired: string;
    };
    entryContext: {
      inviteOnboarding: string;
      postRegistration: string;
      returningUser: string;
    };
  };
  history: {
    pageTitle: string;
    pageSubtitle: string;
    backToChat: string;
    searchPlaceholder: string;
    searchAriaLabel: string;
    clearSearch: string;
    groupToday: string;
    groupYesterday: string;
    groupLast7Days: string;
    groupLast30Days: string;
    groupOlder: string;
    statusActive: string;
    statusArchived: string;
    openConversationAria: string;
    untitledConversation: string;
    noPreview: string;
    emptyTitle: string;
    emptyDescription: string;
    emptySearchTitle: string;
    emptySearchDescription: string;
    loadingLabel: string;
    errorTitle: string;
    errorMessage: string;
    retry: string;
    topicGroupsAriaLabel: string;
    topicConversationCountLabel: string;
    topicLatestActivityLabel: string;
    recentConversationsLabel: string;
    openTopicAction: string;
  };
  referral: {
    pageTitle: string;
    pageSubtitle: string;
    backToChat: string;
    totalInvitesLabel: string;
    activatedQoraLabel: string;
    firstMicroTaskLabel: string;
    firstAchievementLabel: string;
    createPanelTitle: string;
    createPanelSubtitle: string;
    addLinkButton: string;
    draftTitle: string;
    defaultDraftLabel: string;
    draftLabel: string;
    draftUrlPreview: string;
    selectColorLabel: string;
    doneButton: string;
    customizeButton: string;
    tagColors: {
      blue: string;
      violet: string;
      cyan: string;
      green: string;
      orange: string;
      pink: string;
      gold: string;
      gray: string;
    };
    statusButton: string;
    chatButton: string;
    agentContextAttached: string;
    chatDisabledUntilWallet: string;
    statusPanelPlaceholder: string;
    chatPanelPlaceholder: string;
    chatPanelTitle: string;
    chatLoadingLabel: string;
    chatEmptyTitle: string;
    chatEmptyDescription: string;
    chatLoadError: string;
    chatSendErrorTitle: string;
    chatInputPlaceholder: string;
    chatSendButton: string;
    chatSendAriaLabel: string;
    chatUnreadBadgeLabel: string;
    chatReferrerLabel: string;
    chatInviteeLabel: string;
    chatDeliverySent: string;
    chatDeliveryDelivered: string;
    chatDeliveryRead: string;
    chatShowOriginal: string;
    chatShowTranslation: string;
    chatOriginalTextLabel: string;
    chatTranslatedTextLabel: string;
    chatTranslationUnavailable: string;
    chatTranslationLoading: string;
    chatTranslationFailed: string;
    createLinkSuccessTitle: string;
    createLinkErrorTitle: string;
    createCustomizedLinkSuccessTitle: string;
    createCustomizedLinkErrorTitle: string;
    linkUpdatedTitle: string;
    linkUpdateErrorTitle: string;
    statusLoadWarningTitle: string;
    statusCreated: string;
    statusInviteOpened: string;
    statusWalletConnected: string;
    statusQoraActivated: string;
    statusFirstMicrotaskCompleted: string;
    statusFirstAchievementUnlocked: string;
    copyButton: string;
    shareButton: string;
    copySuccessTitle: string;
    copyErrorTitle: string;
    shareSuccessTitle: string;
    shareUnavailableTitle: string;
    shareErrorTitle: string;
    noDataTitle: string;
    noDataDescription: string;
    statusTimeline: {
      panelTitle: string;
      invited: string;
      connectedWallet: string;
      activatedQora: string;
      firstMicrotask: string;
      firstAchievement: string;
      completed: string;
      current: string;
      upcoming: string;
      noActivity: string;
    };
    personalizationWizard: {
      title: string;
      subtitle: string;
      progressA11yLabel: string;
      closeAriaLabel: string;
      backButton: string;
      nextButton: string;
      doneButton: string;
      optionalBadge: string;
      multiSelectHint: string;
      requiredAnswerError: string;
      unsavedTitle: string;
      unsavedDescription: string;
      unsavedStayButton: string;
      unsavedDiscardButton: string;
      steps: {
        inviteeRelationship: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            friend: string;
            family: string;
            colleague: string;
            community: string;
            other: string;
          };
        };
        familiarityLevel: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            knowWell: string;
            somewhat: string;
            justMet: string;
            onlineOnly: string;
            dontKnow: string;
          };
        };
        invitationReason: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            learnAndEarn: string;
            ecosystemAccess: string;
            guidedOnboarding: string;
            teamGrowth: string;
            curiousExplore: string;
          };
        };
        primaryMotivation: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            earnRewards: string;
            learnWeb3: string;
            productivity: string;
            communityStatus: string;
            curiosity: string;
          };
        };
        web3FamiliarityLevel: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            newcomer: string;
            basic: string;
            intermediate: string;
            advanced: string;
            dontKnow: string;
          };
        };
        previousWeb3ToolExperience: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            none: string;
            walletOnly: string;
            defiOrNft: string;
            daoOrGovernance: string;
            multipleTools: string;
          };
        };
        readinessToTakeAction: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            readyNow: string;
            thisWeek: string;
            needGuidance: string;
            researching: string;
            unsure: string;
          };
        };
        concernsAndFrictions: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            security: string;
            fundSafety: string;
            complexity: string;
            timeCommitment: string;
            fees: string;
            privacy: string;
            noConcerns: string;
          };
        };
        previousNegativeExperience: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            none: string;
            scamAttempt: string;
            lostFunds: string;
            highFees: string;
            confusingUx: string;
            dontKnow: string;
          };
        };
        preferredInformationStyle: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            simpleSteps: string;
            visualExamples: string;
            comparisons: string;
            dataDriven: string;
            conversational: string;
          };
        };
        suggestedEcosystemSection: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            gettingStarted: string;
            microtasks: string;
            achievements: string;
            walletSecurity: string;
            community: string;
          };
        };
        conversionLikelihood: {
          title: string;
          tooltip: string;
          question: string;
          options: {
            veryHigh: string;
            high: string;
            medium: string;
            low: string;
            veryLow: string;
          };
        };
        additionalNote: {
          title: string;
          tooltip: string;
          question: string;
          placeholder: string;
        };
      };
    };
    loadingLabel: string;
    errorTitle: string;
    errorMessage: string;
    retry: string;
    statsTitle: string;
    totalReferralsLabel: string;
    totalRewardsLabel: string;
    valueUnavailable: string;
  };
  profile: {
    pageTitle: string;
    pageSubtitle: string;
    backToChat: string;
    summaryTitle: string;
    fullNameLabel: string;
    emailLabel: string;
    valueUnavailable: string;
    activationTitle: string;
    activationActive: string;
    activationInactive: string;
    activationUnknown: string;
    initialInteractionLabel: string;
    registrationLabel: string;
    firstTasksLabel: string;
    preferencesTitle: string;
    languageLabel: string;
    walletTitle: string;
    connectWallet: string;
    disconnectWallet: string;
    walletConnectedStatus: string;
    walletDisconnectedStatus: string;
    walletConnected: string;
    walletDisconnected: string;
    languageSaved: string;
    sessionTitle: string;
    sessionDescription: string;
    logoutAction: string;
    loggedOut: string;
    loadingLabel: string;
    errorTitle: string;
    errorMessage: string;
    retry: string;
  };
  dashboard: {
    pageTitle: string;
    pageSubtitle: string;
    backToChat: string;
    loadingLabel: string;
    errorTitle: string;
    errorMessage: string;
    retry: string;
    gatedTitle: string;
    gatedDescription: string;
    emptyTitle: string;
    emptyDescription: string;
    statusIdle: string;
    statusInProgress: string;
    statusComplete: string;
    statusBlocked: string;
    priorityLabel: string;
    progressLabel: string;
    priorityLow: string;
    priorityMedium: string;
    priorityHigh: string;
    activationOverviewTitle: string;
    activationOverviewActiveSummary: string;
    activationOverviewPendingSummary: string;
    conversationHubTitle: string;
    conversationHubSummary: string;
    networkGrowthTitle: string;
    networkGrowthSummary: string;
    historyReviewTitle: string;
    historyReviewSummary: string;
    goToChat: string;
    openProfile: string;
    openChat: string;
    openReferral: string;
    openHistory: string;
  };
  locales: {
    en: {
      nativeName: string;
      englishName: string;
    };
    fa: {
      nativeName: string;
      englishName: string;
    };
    ar: {
      nativeName: string;
      englishName: string;
    };
  };
}

const messages: Record<AppLocale, MessagesSchema> = {
  en: {
    common: {
      appName: "RAGAi"
    },
    language: {
      pageTitle: "Choose your language",
      pageSubtitle: "Pick your preferred language for the full app experience.",
      continueCta: "Continue",
      selectedA11y: "Selected language",
      radioGroupLabel: "Available languages",
      switcherLabel: "Language",
      syncInProgress: "Saving language preference…",
      syncFailed: "Server and local language differed. We reconciled your preference safely."
    },
    voice: {
      pageTitle: "Voice Conversation",
      pageSubtitle: "Speak naturally and continue in chat anytime.",
      liveTranscriptTitle: "Live Transcript",
      liveTranscriptPlaceholder: "Start speaking to see transcript…",
      close: "Close voice mode",
      walletAriaLabel: "Wallet",
      historyAriaLabel: "History",
      returnToChat: "Return to Chat",
      switchToTyping: "Switch to Typing",
      startListening: "Start listening",
      stopListening: "Stop listening",
      startLabel: "Start",
      stopLabel: "Stop",
      listeningStatus: "Listening",
      processingStatus: "Processing",
      speakingStatus: "Speaking",
      idleStatus: "Idle",
      permissionDeniedStatus: "Microphone permission denied",
      errorStatus: "Voice error",
      micPermissionPrompt: "Allow microphone access to start voice conversation.",
      transcriptEmptyState: "No transcript yet.",
      transcriptPartialLabel: "Partial",
      transcriptFinalLabel: "Final",
      ttsToggleOn: "Voice reply on",
      ttsToggleOff: "Voice reply off",
      visualizerLabel: "Voice activity pulse"
    },
    chatLanding: {
      newChat: "New Chat",
      appWordmark: "QORA",
      onlineStatus: "AI Agent Online",
      agentTitle: "QORA Agent",
      agentSubtitle: "Ready to analyze, guide, and automate your Web3 workflow.",
      connectedWalletLabel: "Wallet Connected",
      connectWallet: "CONNECT WALLET",
      connectedWalletFallback: "Wallet Connected",
      conversationHistory: "Conversation History",
      profileAriaLabel: "Open profile",
      menuAriaLabel: "Open menu",
      sideNavAriaLabel: "Agent navigation",
      mobileNavAriaLabel: "Mobile navigation",
      contextPanelTitle: "Context",
      capabilitiesPanelTitle: "Active Capabilities",
      memoryPanelTitle: "Recent Memory",
      securityPanelTitle: "Security & Wallet",
      contextCapabilitiesDescription: "RAG, memory retrieval, and voice orchestration are ready.",
      contextMemoryDescription: "Resume your latest topic and keep thread continuity.",
      contextSecurityDescription: "Wallet-aware checks and identity safeguards are active.",
      quickActionsTitle: "Quick Actions",
      quickActionDashboard: "Dashboard",
      quickActionHistory: "History",
      quickActionReferral: "Referral",
      quickActionVoice: "Voice",
      capabilityRag: "RAG",
      capabilityMemory: "Memory",
      capabilityVoice: "Voice",
      capabilityWalletAware: "Wallet-aware",
      promptWalletRiskTitle: "Analyze wallet risk",
      promptWalletRiskDescription: "Scan exposure and security posture.",
      promptWalletRiskPrompt: "Analyze my wallet risk and summarize key vulnerabilities.",
      promptEcosystemTitle: "Explain QORA ecosystem",
      promptEcosystemDescription: "Get a concise ecosystem briefing.",
      promptEcosystemPrompt: "Explain the QORA ecosystem and how each module works together.",
      promptEarningTitle: "Find earning opportunities",
      promptEarningDescription: "Discover practical growth paths.",
      promptEarningPrompt: "Find earning opportunities based on my current Web3 profile.",
      promptContinueTitle: "Continue previous topic",
      promptContinueDescription: "Resume from the latest context.",
      promptContinuePrompt: "Continue my previous topic and propose next best actions.",
      promptSectionTitle: "Suggested Prompts",
      promptSectionDescription: "Start with a guided prompt or type your own request.",
      emptyTitle: "Start your first conversation",
      emptyDescription: "Ask a question or share your goal to begin.",
      chatMetaNow: "Now",
      chatMetaSources: "sources",
      chatMetaFeedback: "Feedback",
      funnelTitle: "Funnel Discovery",
      addAction: "Add action",
      micAriaLabel: "Open voice input",
      sendAriaLabel: "Send message",
      inputAriaLabel: "Message input",
      messagePlaceholder: "Type your message...",
      send: "Send",
      voice: "Voice",
      navAgent: "Agent",
      navHistory: "History",
      navDashboard: "Dashboard",
      navAddFriend: "Add Friend",
      navVoice: "Voice",
      navProfile: "Profile",
      newChatGateRequiresAuth: "Complete sign-in first.",
      newChatGateRequiresActivation: "Activation is required before starting a new chat.",
      newChatGateRequiresInitialInteraction: "Complete initial interaction first.",
      newChatGateRequiresRegistration: "Registration step is still pending.",
      newChatGateRequiresFirstTasks: "Wait until first tasks are received.",
      typingStatus: "Assistant is thinking...",
      historyPlaceholderTitle: "History",
      historyPlaceholderDescription: "Conversation history page will be available here.",
      referralPlaceholderTitle: "Referral",
      referralPlaceholderDescription: "Referral page is ready for the next phase.",
      historyEntryTitle: "Resume this topic",
      historyEntryDescription: "Choose how you want to continue this topic before composing your next message.",
      historyEntryTopicFallback: "Selected topic",
      historyEntryContinue: "Continue Conversation",
      historyEntryStartNew: "Start New Conversation"
    },
    agentLanding: {
      cardsSectionTitle: "Agent Modules",
      cardsSectionSubtitle: "Choose a module to continue with guided QORA actions.",
      cardOpenAction: "Open",
      cards: {
        myStatusNextBestAction: {
          title: "My Status & Next Best Action",
          description: "Review your current progress and receive your highest-impact next move."
        },
        earnViaMicrotasks: {
          title: "Earn via Microtasks",
          description: "Discover available microtasks and optimize your earning path."
        },
        securityRiskCheck: {
          title: "Security & Risk Check",
          description: "Run wallet-aware checks to spot risks and protect your account."
        },
        investingStrategy: {
          title: "Investing Strategy",
          description: "Get strategy-focused guidance tailored to your Web3 profile."
        },
        referralTeamGrowth: {
          title: "Referral & Team Growth",
          description: "Grow your network and track invitation-based expansion."
        },
        qora101EcosystemGuide: {
          title: "QORA 101 / Ecosystem Guide",
          description: "Learn core QORA flows, concepts, and ecosystem fundamentals."
        },
        helpTroubleshooting: {
          title: "Help & Troubleshooting",
          description: "Get support for blockers, errors, and setup troubleshooting."
        }
      },
      onboarding: {
        title: "Welcome to QORA Agent",
        subtitle: "Start with guided onboarding to unlock your personalized workspace journey.",
        start: "how_to_start",
        nextStep: "next_step",
        howToStart: "how_to_start",
        wantToJoin: "want_to_join",
        actionsTitle: "Onboarding Actions"
      },
      gating: {
        connectWallet: "Connect Wallet",
        completeActivation: "Complete Activation",
        continueOnboarding: "Continue Onboarding",
        walletRequired: "This module requires a connected wallet.",
        activationRequired: "This module unlocks after account activation.",
        onboardingRequired: "Complete onboarding milestones to unlock this module."
      },
      entryContext: {
        inviteOnboarding: "Invite Onboarding",
        postRegistration: "Post Registration",
        returningUser: "Returning User"
      }
    },
    history: {
      pageTitle: "Conversation History",
      pageSubtitle: "Browse previous chats and reopen any conversation.",
      backToChat: "Back to Chat",
      searchPlaceholder: "Search conversations...",
      searchAriaLabel: "Search conversation history",
      clearSearch: "Clear",
      groupToday: "Today",
      groupYesterday: "Yesterday",
      groupLast7Days: "Previous 7 days",
      groupLast30Days: "Previous 30 days",
      groupOlder: "Older",
      statusActive: "Active",
      statusArchived: "Archived",
      openConversationAria: "Open conversation",
      untitledConversation: "Untitled conversation",
      noPreview: "No preview available.",
      emptyTitle: "No conversations yet",
      emptyDescription: "Start a chat to build your history.",
      emptySearchTitle: "No matches found",
      emptySearchDescription: "Try a different search term.",
      loadingLabel: "Loading conversation history...",
      errorTitle: "Could not load history",
      errorMessage: "Something went wrong while loading your conversation history.",
      retry: "Retry",
      topicGroupsAriaLabel: "Topic groups",
      topicConversationCountLabel: "conversations",
      topicLatestActivityLabel: "Latest activity",
      recentConversationsLabel: "Recent conversations",
      openTopicAction: "Open topic"
    },
    referral: {
      pageTitle: "Invite Friends",
      pageSubtitle: "Share your invite and bring friends to RAGAi.",
      backToChat: "Back to Chat",
      totalInvitesLabel: "Total Invite",
      activatedQoraLabel: "Activated QORA",
      firstMicroTaskLabel: "First Micro-task",
      firstAchievementLabel: "First Achievement",
      createPanelTitle: "Create Invite Link",
      createPanelSubtitle: "Start a regular invite now or prepare customization for later.",
      addLinkButton: "Add Link",
      draftTitle: "Draft Invite Link",
      defaultDraftLabel: "My Referral Link",
      draftLabel: "Link Label",
      draftUrlPreview: "Short Link Preview",
      selectColorLabel: "Tag Color",
      doneButton: "Done",
      customizeButton: "Customize",
      tagColors: {
        blue: "Blue",
        violet: "Violet",
        cyan: "Cyan",
        green: "Green",
        orange: "Orange",
        pink: "Pink",
        gold: "Gold",
        gray: "Gray"
      },
      statusButton: "Status",
      chatButton: "Chat",
      agentContextAttached: "Agent context attached",
      chatDisabledUntilWallet: "Chat unlocks after wallet connection",
      statusPanelPlaceholder: "Status details will expand here as referral events stream in.",
      chatPanelPlaceholder: "Referral chat thread preview will appear here in the next phase.",
      chatPanelTitle: "Referral chat",
      chatLoadingLabel: "Loading referral chat",
      chatEmptyTitle: "No messages yet",
      chatEmptyDescription: "Start the referral conversation once the invitee is ready.",
      chatLoadError: "Could not load referral chat.",
      chatSendErrorTitle: "Could not send message",
      chatInputPlaceholder: "Write a message",
      chatSendButton: "Send",
      chatSendAriaLabel: "Send referral chat message",
      chatUnreadBadgeLabel: "Unread messages",
      chatReferrerLabel: "Referrer",
      chatInviteeLabel: "Invitee",
      chatDeliverySent: "Sent",
      chatDeliveryDelivered: "Delivered",
      chatDeliveryRead: "Read",
      chatShowOriginal: "View original",
      chatShowTranslation: "Show translation",
      chatOriginalTextLabel: "Original",
      chatTranslatedTextLabel: "Translated",
      chatTranslationUnavailable: "Translation is not available yet.",
      chatTranslationLoading: "Translation loading",
      chatTranslationFailed: "Translation failed",
      createLinkSuccessTitle: "Invite link created",
      createLinkErrorTitle: "Could not create invite link",
      createCustomizedLinkSuccessTitle: "Customized invite link created",
      createCustomizedLinkErrorTitle: "Could not create customized invite link",
      linkUpdatedTitle: "Invite link updated",
      linkUpdateErrorTitle: "Could not update invite link",
      statusLoadWarningTitle: "Could not load detailed status",
      statusCreated: "Created",
      statusInviteOpened: "Invite Opened",
      statusWalletConnected: "Wallet Connected",
      statusQoraActivated: "QORA Activated",
      statusFirstMicrotaskCompleted: "First Micro-task Completed",
      statusFirstAchievementUnlocked: "First Achievement Unlocked",
      copyButton: "Copy",
      shareButton: "Share",
      copySuccessTitle: "Invite copied",
      copyErrorTitle: "Could not copy invite",
      shareSuccessTitle: "Share opened",
      shareUnavailableTitle: "Sharing unavailable on this device",
      shareErrorTitle: "Could not share invite",
      noDataTitle: "No referral data yet",
      noDataDescription: "Your invite data will appear once available.",
      statusTimeline: {
        panelTitle: "Progress Timeline",
        invited: "Invited",
        connectedWallet: "Connected Wallet",
        activatedQora: "Activated QORA",
        firstMicrotask: "First Micro-task",
        firstAchievement: "First Achievement",
        completed: "Completed",
        current: "Current",
        upcoming: "Upcoming",
        noActivity: "No activity yet"
      },
      personalizationWizard: {
        title: "Customize Invite Context",
        subtitle: "Guide the agent with invitee context before sharing.",
        progressA11yLabel: "Wizard progress",
        closeAriaLabel: "Close personalization wizard",
        backButton: "Back",
        nextButton: "Next",
        doneButton: "Done",
        optionalBadge: "Optional",
        multiSelectHint: "Select one or more options",
        requiredAnswerError: "Please select an answer to continue.",
        unsavedTitle: "Discard customization?",
        unsavedDescription: "You have unsaved personalization answers.",
        unsavedStayButton: "Keep editing",
        unsavedDiscardButton: "Discard",
        steps: {
          inviteeRelationship: {
            title: "Relationship",
            tooltip: "Helps tone and context for this invite.",
            question: "What is your relationship with this invitee?",
            options: {
              friend: "Friend",
              family: "Family",
              colleague: "Colleague",
              community: "Community contact",
              other: "Other"
            }
          },
          familiarityLevel: {
            title: "Familiarity",
            tooltip: "Used to calibrate guidance depth.",
            question: "How well do you know this invitee?",
            options: {
              knowWell: "I know them well",
              somewhat: "Somewhat",
              justMet: "Just met recently",
              onlineOnly: "Only online",
              dontKnow: "I don't know"
            }
          },
          invitationReason: {
            title: "Invitation Reason",
            tooltip: "Clarifies why the invite matters now.",
            question: "Why are you inviting this person?",
            options: {
              learnAndEarn: "Learn and earn",
              ecosystemAccess: "Access QORA ecosystem",
              guidedOnboarding: "Get guided onboarding",
              teamGrowth: "Grow team/network",
              curiousExplore: "Just exploring"
            }
          },
          primaryMotivation: {
            title: "Primary Motivation",
            tooltip: "Supports personalized onboarding intent.",
            question: "What will motivate them most?",
            options: {
              earnRewards: "Earn rewards",
              learnWeb3: "Learn Web3",
              productivity: "Productivity gains",
              communityStatus: "Community status",
              curiosity: "Curiosity"
            }
          },
          web3FamiliarityLevel: {
            title: "Web3 Familiarity",
            tooltip: "Determines complexity of suggested content.",
            question: "What is their Web3 familiarity level?",
            options: {
              newcomer: "Newcomer",
              basic: "Basic",
              intermediate: "Intermediate",
              advanced: "Advanced",
              dontKnow: "I don't know"
            }
          },
          previousWeb3ToolExperience: {
            title: "Tool Experience",
            tooltip: "Maps prior exposure to relevant onboarding paths.",
            question: "What Web3 tools have they used before?",
            options: {
              none: "None",
              walletOnly: "Wallet only",
              defiOrNft: "DeFi or NFT apps",
              daoOrGovernance: "DAO/governance tools",
              multipleTools: "Multiple tools"
            }
          },
          readinessToTakeAction: {
            title: "Readiness",
            tooltip: "Helps sequence activation nudges.",
            question: "How ready are they to take action?",
            options: {
              readyNow: "Ready now",
              thisWeek: "Likely this week",
              needGuidance: "Need step-by-step guidance",
              researching: "Still researching",
              unsure: "Not sure"
            }
          },
          concernsAndFrictions: {
            title: "Concerns",
            tooltip: "Identify blockers to reduce drop-off risk.",
            question: "Which concerns or frictions might block them?",
            options: {
              security: "Security risks",
              fundSafety: "Fund safety",
              complexity: "Too complex",
              timeCommitment: "Time commitment",
              fees: "Transaction fees",
              privacy: "Privacy concerns",
              noConcerns: "No major concerns"
            }
          },
          previousNegativeExperience: {
            title: "Negative Experience",
            tooltip: "Supports safer and trust-aware messaging.",
            question: "Have they had any negative Web3 experience?",
            options: {
              none: "No",
              scamAttempt: "Scam/phishing attempt",
              lostFunds: "Lost funds",
              highFees: "Unexpected high fees",
              confusingUx: "Confusing user experience",
              dontKnow: "I don't know"
            }
          },
          preferredInformationStyle: {
            title: "Info Style",
            tooltip: "Formats guidance to match preference.",
            question: "How do they prefer receiving information?",
            options: {
              simpleSteps: "Simple steps",
              visualExamples: "Visual examples",
              comparisons: "Comparisons",
              dataDriven: "Data-driven",
              conversational: "Conversational"
            }
          },
          suggestedEcosystemSection: {
            title: "Suggested Section",
            tooltip: "Directs invitee to the most relevant section first.",
            question: "Which ecosystem section should they start with?",
            options: {
              gettingStarted: "Getting Started",
              microtasks: "Microtasks",
              achievements: "Achievements",
              walletSecurity: "Wallet Security",
              community: "Community"
            }
          },
          conversionLikelihood: {
            title: "Conversion Likelihood",
            tooltip: "Used for referral prioritization.",
            question: "How likely are they to convert?",
            options: {
              veryHigh: "Very high",
              high: "High",
              medium: "Medium",
              low: "Low",
              veryLow: "Very low"
            }
          },
          additionalNote: {
            title: "Additional Note",
            tooltip: "Optional context that can help the agent.",
            question: "Anything else we should know?",
            placeholder: "Add extra context for this invitee..."
          }
        }
      },
      loadingLabel: "Loading invite details...",
      errorTitle: "Could not load referral data",
      errorMessage: "Something went wrong while loading your invite details.",
      retry: "Retry",
      statsTitle: "Referral Stats",
      totalReferralsLabel: "Total referrals",
      totalRewardsLabel: "Total rewards",
      valueUnavailable: "Unavailable"
    },
    profile: {
      pageTitle: "Profile",
      pageSubtitle: "Manage language, activation, wallet status, and account session.",
      backToChat: "Back to Chat",
      summaryTitle: "Profile Summary",
      fullNameLabel: "Full name",
      emailLabel: "Email",
      valueUnavailable: "Unavailable",
      activationTitle: "Activation Status",
      activationActive: "Active",
      activationInactive: "Inactive",
      activationUnknown: "Unknown",
      initialInteractionLabel: "Initial interaction completed",
      registrationLabel: "Registration completed",
      firstTasksLabel: "First tasks received",
      preferencesTitle: "Preferences",
      languageLabel: "Language",
      walletTitle: "Wallet",
      connectWallet: "Connect Wallet",
      disconnectWallet: "Disconnect",
      walletConnectedStatus: "Wallet is connected.",
      walletDisconnectedStatus: "Wallet is not connected.",
      walletConnected: "Wallet connected",
      walletDisconnected: "Wallet disconnected",
      languageSaved: "Language updated",
      sessionTitle: "Session",
      sessionDescription: "Sign out safely and disconnect local wallet state.",
      logoutAction: "Logout",
      loggedOut: "Logged out",
      loadingLabel: "Loading profile...",
      errorTitle: "Could not load profile",
      errorMessage: "Something went wrong while loading your profile settings.",
      retry: "Retry"
    },
    dashboard: {
      pageTitle: "Dashboard",
      pageSubtitle: "Post-activation cards for next actions and progress tracking.",
      backToChat: "Back to Chat",
      loadingLabel: "Loading dashboard...",
      errorTitle: "Could not load dashboard",
      errorMessage: "Something went wrong while loading dashboard cards.",
      retry: "Retry",
      gatedTitle: "Activation required",
      gatedDescription: "Complete activation in Profile to unlock dashboard cards.",
      emptyTitle: "No dashboard cards yet",
      emptyDescription: "Your cards will appear here when available.",
      statusIdle: "Idle",
      statusInProgress: "In progress",
      statusComplete: "Complete",
      statusBlocked: "Blocked",
      priorityLabel: "Priority",
      progressLabel: "Progress",
      priorityLow: "Low",
      priorityMedium: "Medium",
      priorityHigh: "High",
      activationOverviewTitle: "Activation Overview",
      activationOverviewActiveSummary: "Your account is active and ready for advanced workflows.",
      activationOverviewPendingSummary: "Complete activation milestones to unlock the full dashboard experience.",
      conversationHubTitle: "Conversation Hub",
      conversationHubSummary: "Continue your assistant conversation and expand discovered funnel signals.",
      networkGrowthTitle: "Invite and Grow",
      networkGrowthSummary: "Share referral access with teammates and monitor collaboration growth.",
      historyReviewTitle: "Conversation Review",
      historyReviewSummary: "Revisit previous conversations and resume high-priority threads.",
      goToChat: "Go to Chat",
      openProfile: "Open Profile",
      openChat: "Open Chat",
      openReferral: "Open Referral",
      openHistory: "Open History"
    },
    locales: {
      en: {
        nativeName: "English",
        englishName: "English"
      },
      fa: {
        nativeName: "فارسی",
        englishName: "Persian"
      },
      ar: {
        nativeName: "العربية",
        englishName: "Arabic"
      }
    }
  },
  ar: {
    common: {
      appName: "RAGAi"
    },
    language: {
      pageTitle: "اختر لغتك",
      pageSubtitle: "اختر لغتك المفضلة لتجربة التطبيق بالكامل.",
      continueCta: "متابعة",
      selectedA11y: "اللغة المحددة",
      radioGroupLabel: "اللغات المتاحة",
      switcherLabel: "اللغة",
      syncInProgress: "جارٍ حفظ تفضيل اللغة…",
      syncFailed: "اختلفت لغة الخادم واللغة المحلية. تمت التسوية بأمان حسب التفضيل."
    },
    voice: {
      pageTitle: "محادثة صوتية",
      pageSubtitle: "تحدث بشكل طبيعي وتابع في الدردشة في أي وقت.",
      liveTranscriptTitle: "النص المباشر",
      liveTranscriptPlaceholder: "ابدأ التحدث لعرض النص…",
      close: "إغلاق الوضع الصوتي",
      walletAriaLabel: "المحفظة",
      historyAriaLabel: "السجل",
      returnToChat: "العودة إلى الدردشة",
      switchToTyping: "التحويل إلى الكتابة",
      startListening: "ابدأ الاستماع",
      stopListening: "إيقاف الاستماع",
      startLabel: "بدء",
      stopLabel: "إيقاف",
      listeningStatus: "يستمع",
      processingStatus: "يعالج",
      speakingStatus: "يتحدث",
      idleStatus: "خامل",
      permissionDeniedStatus: "تم رفض إذن الميكروفون",
      errorStatus: "خطأ صوتي",
      micPermissionPrompt: "اسمح بالوصول إلى الميكروفون لبدء المحادثة الصوتية.",
      transcriptEmptyState: "لا يوجد نص بعد.",
      transcriptPartialLabel: "جزئي",
      transcriptFinalLabel: "نهائي",
      ttsToggleOn: "الرد الصوتي مفعّل",
      ttsToggleOff: "الرد الصوتي معطّل",
      visualizerLabel: "نبض النشاط الصوتي"
    },
    chatLanding: {
      newChat: "محادثة جديدة",
      appWordmark: "QORA",
      onlineStatus: "وكيل الذكاء الاصطناعي متصل",
      agentTitle: "وكيل QORA",
      agentSubtitle: "جاهز للتحليل والإرشاد وأتمتة سير عمل Web3.",
      connectedWalletLabel: "المحفظة متصلة",
      connectWallet: "ربط المحفظة",
      connectedWalletFallback: "المحفظة متصلة",
      conversationHistory: "سجل المحادثات",
      profileAriaLabel: "فتح الملف الشخصي",
      menuAriaLabel: "فتح القائمة",
      sideNavAriaLabel: "تنقل الوكيل",
      mobileNavAriaLabel: "تنقل الهاتف",
      contextPanelTitle: "السياق",
      capabilitiesPanelTitle: "القدرات النشطة",
      memoryPanelTitle: "الذاكرة الأخيرة",
      securityPanelTitle: "الأمان والمحفظة",
      contextCapabilitiesDescription: "قدرات RAG واسترجاع الذاكرة والتنسيق الصوتي جاهزة.",
      contextMemoryDescription: "استأنف آخر موضوع مع الحفاظ على استمرارية المحادثة.",
      contextSecurityDescription: "فحوصات واعية بالمحفظة وحماية الهوية مفعّلة.",
      quickActionsTitle: "إجراءات سريعة",
      quickActionDashboard: "لوحة التحكم",
      quickActionHistory: "السجل",
      quickActionReferral: "الإحالة",
      quickActionVoice: "صوت",
      capabilityRag: "RAG",
      capabilityMemory: "ذاكرة",
      capabilityVoice: "صوت",
      capabilityWalletAware: "واعي بالمحفظة",
      promptWalletRiskTitle: "حلّل مخاطر المحفظة",
      promptWalletRiskDescription: "قيّم التعرض الأمني والمخاطر.",
      promptWalletRiskPrompt: "حلّل مخاطر محفظتي وقدّم ملخصًا لأهم نقاط الضعف.",
      promptEcosystemTitle: "اشرح منظومة QORA",
      promptEcosystemDescription: "احصل على شرح موجز للمنظومة.",
      promptEcosystemPrompt: "اشرح منظومة QORA وكيف تتكامل مكوّناتها.",
      promptEarningTitle: "ابحث عن فرص ربح",
      promptEarningDescription: "اكتشف مسارات نمو عملية.",
      promptEarningPrompt: "ابحث عن فرص ربح مناسبة لملفي الحالي في Web3.",
      promptContinueTitle: "تابع الموضوع السابق",
      promptContinueDescription: "استكمل من آخر سياق محفوظ.",
      promptContinuePrompt: "تابع الموضوع السابق واقترح أفضل الإجراءات التالية.",
      promptSectionTitle: "مطالبات مقترحة",
      promptSectionDescription: "ابدأ بمطالبة موجهة أو اكتب طلبك الخاص.",
      emptyTitle: "ابدأ محادثتك الأولى",
      emptyDescription: "اطرح سؤالًا أو شارك هدفك للبدء.",
      chatMetaNow: "الآن",
      chatMetaSources: "مصادر",
      chatMetaFeedback: "ملاحظات",
      funnelTitle: "اكتشاف مسار التحويل",
      addAction: "إضافة إجراء",
      micAriaLabel: "فتح الإدخال الصوتي",
      sendAriaLabel: "إرسال الرسالة",
      inputAriaLabel: "إدخال الرسالة",
      messagePlaceholder: "اكتب رسالتك...",
      send: "إرسال",
      voice: "صوت",
      navAgent: "الوكيل",
      navHistory: "السجل",
      navDashboard: "لوحة التحكم",
      navAddFriend: "إضافة صديق",
      navVoice: "صوت",
      navProfile: "الملف الشخصي",
      newChatGateRequiresAuth: "أكمل تسجيل الدخول أولًا.",
      newChatGateRequiresActivation: "التفعيل مطلوب قبل بدء محادثة جديدة.",
      newChatGateRequiresInitialInteraction: "أكمل التفاعل الأولي أولًا.",
      newChatGateRequiresRegistration: "خطوة التسجيل ما زالت قيد الانتظار.",
      newChatGateRequiresFirstTasks: "انتظر حتى استلام المهام الأولى.",
      typingStatus: "المساعد يفكر...",
      historyPlaceholderTitle: "السجل",
      historyPlaceholderDescription: "ستتوفر صفحة سجل المحادثات هنا.",
      referralPlaceholderTitle: "الإحالة",
      referralPlaceholderDescription: "صفحة الإحالة جاهزة للمرحلة التالية.",
      historyEntryTitle: "متابعة هذا الموضوع",
      historyEntryDescription: "اختر طريقة متابعة هذا الموضوع قبل كتابة رسالتك التالية.",
      historyEntryTopicFallback: "الموضوع المحدد",
      historyEntryContinue: "متابعة المحادثة",
      historyEntryStartNew: "بدء محادثة جديدة"
    },
    agentLanding: {
      cardsSectionTitle: "وحدات الوكيل",
      cardsSectionSubtitle: "اختر وحدة لمتابعة الإجراءات الموجهة مع QORA.",
      cardOpenAction: "فتح",
      cards: {
        myStatusNextBestAction: {
          title: "حالتي وأفضل إجراء تالٍ",
          description: "راجع تقدمك الحالي واحصل على الخطوة التالية الأعلى أثرًا."
        },
        earnViaMicrotasks: {
          title: "اربح عبر المهام المصغّرة",
          description: "اكتشف المهام المصغّرة المتاحة وحسّن مسار الأرباح."
        },
        securityRiskCheck: {
          title: "فحص الأمان والمخاطر",
          description: "شغّل فحوصات واعية بالمحفظة لاكتشاف المخاطر وحماية الحساب."
        },
        investingStrategy: {
          title: "استراتيجية الاستثمار",
          description: "احصل على توجيه استثماري مخصص لملفك في Web3."
        },
        referralTeamGrowth: {
          title: "الإحالة ونمو الفريق",
          description: "وسّع شبكتك وتابع النمو القائم على الدعوات."
        },
        qora101EcosystemGuide: {
          title: "QORA 101 / دليل المنظومة",
          description: "تعرّف على تدفقات QORA الأساسية ومفاهيم المنظومة."
        },
        helpTroubleshooting: {
          title: "المساعدة وحل المشكلات",
          description: "احصل على دعم للعوائق والأخطاء ومشكلات الإعداد."
        }
      },
      onboarding: {
        title: "مرحبًا بك في وكيل QORA",
        subtitle: "ابدأ بإعداد موجّه لفتح رحلتك الشخصية داخل مساحة العمل.",
        start: "كيف أبدأ",
        nextStep: "الخطوة التالية",
        howToStart: "كيف أبدأ",
        wantToJoin: "أريد الانضمام",
        actionsTitle: "إجراءات الإعداد"
      },
      gating: {
        connectWallet: "ربط المحفظة",
        completeActivation: "إكمال التفعيل",
        continueOnboarding: "متابعة الإعداد",
        walletRequired: "هذه الوحدة تتطلب محفظة متصلة.",
        activationRequired: "يتم فتح هذه الوحدة بعد تفعيل الحساب.",
        onboardingRequired: "أكمل مراحل الإعداد لفتح هذه الوحدة."
      },
      entryContext: {
        inviteOnboarding: "إعداد المدعوين",
        postRegistration: "بعد التسجيل",
        returningUser: "مستخدم عائد"
      }
    },
    history: {
      pageTitle: "سجل المحادثات",
      pageSubtitle: "استعرض المحادثات السابقة وافتح أي محادثة من جديد.",
      backToChat: "العودة إلى الدردشة",
      searchPlaceholder: "ابحث في المحادثات...",
      searchAriaLabel: "البحث في سجل المحادثات",
      clearSearch: "مسح",
      groupToday: "اليوم",
      groupYesterday: "الأمس",
      groupLast7Days: "آخر 7 أيام",
      groupLast30Days: "آخر 30 يومًا",
      groupOlder: "الأقدم",
      statusActive: "نشطة",
      statusArchived: "مؤرشفة",
      openConversationAria: "فتح المحادثة",
      untitledConversation: "محادثة بدون عنوان",
      noPreview: "لا توجد معاينة متاحة.",
      emptyTitle: "لا توجد محادثات بعد",
      emptyDescription: "ابدأ دردشة لبناء سجل المحادثات.",
      emptySearchTitle: "لا توجد نتائج مطابقة",
      emptySearchDescription: "جرّب عبارة بحث مختلفة.",
      loadingLabel: "جارٍ تحميل سجل المحادثات...",
      errorTitle: "تعذر تحميل السجل",
      errorMessage: "حدث خطأ أثناء تحميل سجل المحادثات.",
      retry: "إعادة المحاولة",
      topicGroupsAriaLabel: "مجموعات المواضيع",
      topicConversationCountLabel: "محادثات",
      topicLatestActivityLabel: "آخر نشاط",
      recentConversationsLabel: "المحادثات الأخيرة",
      openTopicAction: "فتح الموضوع"
    },
    referral: {
      pageTitle: "دعوة الأصدقاء",
      pageSubtitle: "شارك رابط الدعوة وادعُ أصدقاءك إلى RAGAi.",
      backToChat: "العودة إلى الدردشة",
      totalInvitesLabel: "إجمالي الدعوات",
      activatedQoraLabel: "تفعيل QORA",
      firstMicroTaskLabel: "أول مهمة مصغرة",
      firstAchievementLabel: "أول إنجاز",
      createPanelTitle: "إنشاء رابط دعوة",
      createPanelSubtitle: "ابدأ رابط دعوة عادي الآن أو جهّز التخصيص لاحقًا.",
      addLinkButton: "إضافة رابط",
      draftTitle: "مسودة رابط الدعوة",
      defaultDraftLabel: "رابط الإحالة الخاص بي",
      draftLabel: "عنوان الرابط",
      draftUrlPreview: "معاينة الرابط المختصر",
      selectColorLabel: "لون الوسم",
      doneButton: "تم",
      customizeButton: "تخصيص",
      tagColors: {
        blue: "أزرق",
        violet: "بنفسجي",
        cyan: "سماوي",
        green: "أخضر",
        orange: "برتقالي",
        pink: "وردي",
        gold: "ذهبي",
        gray: "رمادي"
      },
      statusButton: "الحالة",
      chatButton: "الدردشة",
      agentContextAttached: "سياق الوكيل مرفق",
      chatDisabledUntilWallet: "تُفعّل الدردشة بعد ربط المحفظة",
      statusPanelPlaceholder: "ستظهر تفاصيل الحالة هنا مع تدفق أحداث الإحالة.",
      chatPanelPlaceholder: "ستظهر معاينة محادثة الإحالة هنا في المرحلة التالية.",
      chatPanelTitle: "دردشة الإحالة",
      chatLoadingLabel: "جارٍ تحميل دردشة الإحالة",
      chatEmptyTitle: "لا توجد رسائل بعد",
      chatEmptyDescription: "ابدأ محادثة الإحالة عندما يكون المدعو جاهزًا.",
      chatLoadError: "تعذر تحميل دردشة الإحالة.",
      chatSendErrorTitle: "تعذر إرسال الرسالة",
      chatInputPlaceholder: "اكتب رسالة",
      chatSendButton: "إرسال",
      chatSendAriaLabel: "إرسال رسالة دردشة الإحالة",
      chatUnreadBadgeLabel: "رسائل غير مقروءة",
      chatReferrerLabel: "الداعي",
      chatInviteeLabel: "المدعو",
      chatDeliverySent: "أُرسلت",
      chatDeliveryDelivered: "تم التسليم",
      chatDeliveryRead: "مقروءة",
      chatShowOriginal: "عرض الأصل",
      chatShowTranslation: "عرض الترجمة",
      chatOriginalTextLabel: "الأصل",
      chatTranslatedTextLabel: "مترجم",
      chatTranslationUnavailable: "الترجمة غير متاحة بعد.",
      chatTranslationLoading: "جارٍ تحميل الترجمة",
      chatTranslationFailed: "فشلت الترجمة",
      createLinkSuccessTitle: "تم إنشاء رابط الدعوة",
      createLinkErrorTitle: "تعذر إنشاء رابط الدعوة",
      createCustomizedLinkSuccessTitle: "تم إنشاء رابط دعوة مخصص",
      createCustomizedLinkErrorTitle: "تعذر إنشاء رابط الدعوة المخصص",
      linkUpdatedTitle: "تم تحديث رابط الدعوة",
      linkUpdateErrorTitle: "تعذر تحديث رابط الدعوة",
      statusLoadWarningTitle: "تعذر تحميل تفاصيل الحالة",
      statusCreated: "تم الإنشاء",
      statusInviteOpened: "تم فتح الدعوة",
      statusWalletConnected: "تم ربط المحفظة",
      statusQoraActivated: "تم تفعيل QORA",
      statusFirstMicrotaskCompleted: "اكتملت أول مهمة مصغرة",
      statusFirstAchievementUnlocked: "تم فتح أول إنجاز",
      copyButton: "نسخ",
      shareButton: "مشاركة",
      copySuccessTitle: "تم نسخ الدعوة",
      copyErrorTitle: "تعذر نسخ الدعوة",
      shareSuccessTitle: "تم فتح المشاركة",
      shareUnavailableTitle: "المشاركة غير متاحة على هذا الجهاز",
      shareErrorTitle: "تعذر مشاركة الدعوة",
      noDataTitle: "لا توجد بيانات إحالة بعد",
      noDataDescription: "ستظهر بيانات الدعوة عند توفرها.",
      statusTimeline: {
        panelTitle: "الجدول الزمني للتقدم",
        invited: "تمت الدعوة",
        connectedWallet: "تم ربط المحفظة",
        activatedQora: "تم تفعيل QORA",
        firstMicrotask: "أول مهمة مصغرة",
        firstAchievement: "أول إنجاز",
        completed: "مكتمل",
        current: "الحالي",
        upcoming: "قادم",
        noActivity: "لا يوجد نشاط بعد"
      },
      personalizationWizard: {
        title: "تخصيص سياق الدعوة",
        subtitle: "زوّد الوكيل بسياق المدعو قبل المشاركة.",
        progressA11yLabel: "تقدم المعالج",
        closeAriaLabel: "إغلاق معالج التخصيص",
        backButton: "رجوع",
        nextButton: "التالي",
        doneButton: "تم",
        optionalBadge: "اختياري",
        multiSelectHint: "اختر خيارًا واحدًا أو أكثر",
        requiredAnswerError: "يرجى اختيار إجابة للمتابعة.",
        unsavedTitle: "تجاهل التخصيص؟",
        unsavedDescription: "لديك إجابات تخصيص غير محفوظة.",
        unsavedStayButton: "متابعة التحرير",
        unsavedDiscardButton: "تجاهل",
        steps: {
          inviteeRelationship: {
            title: "العلاقة",
            tooltip: "يساعد على تحديد نبرة وسياق الدعوة.",
            question: "ما علاقتك بهذا المدعو؟",
            options: {
              friend: "صديق",
              family: "فرد من العائلة",
              colleague: "زميل",
              community: "معرفة من المجتمع",
              other: "أخرى"
            }
          },
          familiarityLevel: {
            title: "مدى المعرفة",
            tooltip: "يُستخدم لضبط عمق التوجيه.",
            question: "إلى أي مدى تعرف هذا الشخص؟",
            options: {
              knowWell: "أعرفه جيدًا",
              somewhat: "إلى حد ما",
              justMet: "تعرفت عليه مؤخرًا",
              onlineOnly: "عبر الإنترنت فقط",
              dontKnow: "لا أعرف"
            }
          },
          invitationReason: {
            title: "سبب الدعوة",
            tooltip: "يوضح أهمية الدعوة الآن.",
            question: "لماذا تدعو هذا الشخص؟",
            options: {
              learnAndEarn: "التعلّم والربح",
              ecosystemAccess: "الوصول إلى منظومة QORA",
              guidedOnboarding: "إعداد موجّه",
              teamGrowth: "تنمية الفريق/الشبكة",
              curiousExplore: "الاستكشاف فقط"
            }
          },
          primaryMotivation: {
            title: "الدافع الأساسي",
            tooltip: "يدعم نية الإعداد الشخصي.",
            question: "ما الذي سيحفّزه أكثر؟",
            options: {
              earnRewards: "كسب المكافآت",
              learnWeb3: "تعلم Web3",
              productivity: "تحسين الإنتاجية",
              communityStatus: "المكانة المجتمعية",
              curiosity: "الفضول"
            }
          },
          web3FamiliarityLevel: {
            title: "الإلمام بـ Web3",
            tooltip: "يحدد درجة تعقيد المحتوى المقترح.",
            question: "ما مستوى خبرته في Web3؟",
            options: {
              newcomer: "مبتدئ جدًا",
              basic: "أساسي",
              intermediate: "متوسط",
              advanced: "متقدم",
              dontKnow: "لا أعرف"
            }
          },
          previousWeb3ToolExperience: {
            title: "خبرة الأدوات",
            tooltip: "يربط التجربة السابقة بمسار الإعداد المناسب.",
            question: "ما الأدوات التي استخدمها سابقًا في Web3؟",
            options: {
              none: "لا شيء",
              walletOnly: "محفظة فقط",
              defiOrNft: "تطبيقات DeFi أو NFT",
              daoOrGovernance: "أدوات DAO/الحوكمة",
              multipleTools: "عدة أدوات"
            }
          },
          readinessToTakeAction: {
            title: "الجاهزية",
            tooltip: "يساعد على ترتيب تنبيهات التفعيل.",
            question: "ما مدى جاهزيته لاتخاذ إجراء؟",
            options: {
              readyNow: "جاهز الآن",
              thisWeek: "غالبًا هذا الأسبوع",
              needGuidance: "يحتاج إرشادًا خطوة بخطوة",
              researching: "ما زال يبحث",
              unsure: "غير متأكد"
            }
          },
          concernsAndFrictions: {
            title: "المخاوف",
            tooltip: "تحديد العوائق يقلل احتمال الانسحاب.",
            question: "ما المخاوف أو العوائق المحتملة؟",
            options: {
              security: "مخاطر الأمان",
              fundSafety: "سلامة الأموال",
              complexity: "التعقيد",
              timeCommitment: "الوقت المطلوب",
              fees: "رسوم المعاملات",
              privacy: "الخصوصية",
              noConcerns: "لا توجد مخاوف كبيرة"
            }
          },
          previousNegativeExperience: {
            title: "تجربة سلبية سابقة",
            tooltip: "يدعم الرسائل الأكثر أمانًا وبناءً للثقة.",
            question: "هل مرّ بتجربة سلبية في Web3؟",
            options: {
              none: "لا",
              scamAttempt: "محاولة احتيال/تصيد",
              lostFunds: "فقدان أموال",
              highFees: "رسوم مرتفعة غير متوقعة",
              confusingUx: "تجربة استخدام مربكة",
              dontKnow: "لا أعرف"
            }
          },
          preferredInformationStyle: {
            title: "أسلوب المعلومات",
            tooltip: "يكيّف طريقة الشرح حسب التفضيل.",
            question: "كيف يفضّل تلقي المعلومات؟",
            options: {
              simpleSteps: "خطوات بسيطة",
              visualExamples: "أمثلة مرئية",
              comparisons: "مقارنات",
              dataDriven: "مبني على البيانات",
              conversational: "أسلوب حواري"
            }
          },
          suggestedEcosystemSection: {
            title: "قسم مقترح",
            tooltip: "يوجه المدعو إلى القسم الأنسب أولًا.",
            question: "أي قسم في المنظومة يجب أن يبدأ به؟",
            options: {
              gettingStarted: "البدء",
              microtasks: "المهام المصغرة",
              achievements: "الإنجازات",
              walletSecurity: "أمان المحفظة",
              community: "المجتمع"
            }
          },
          conversionLikelihood: {
            title: "احتمال التحويل",
            tooltip: "يستخدم لترتيب أولويات الإحالات.",
            question: "ما احتمال تحوله إلى مستخدم فعّال؟",
            options: {
              veryHigh: "مرتفع جدًا",
              high: "مرتفع",
              medium: "متوسط",
              low: "منخفض",
              veryLow: "منخفض جدًا"
            }
          },
          additionalNote: {
            title: "ملاحظة إضافية",
            tooltip: "سياق إضافي اختياري يفيد الوكيل.",
            question: "هل توجد ملاحظة إضافية؟",
            placeholder: "أضف أي سياق إضافي عن هذا المدعو..."
          }
        }
      },
      loadingLabel: "جارٍ تحميل بيانات الدعوة...",
      errorTitle: "تعذر تحميل بيانات الإحالة",
      errorMessage: "حدث خطأ أثناء تحميل بيانات الدعوة.",
      retry: "إعادة المحاولة",
      statsTitle: "إحصاءات الإحالة",
      totalReferralsLabel: "إجمالي الإحالات",
      totalRewardsLabel: "إجمالي المكافآت",
      valueUnavailable: "غير متاح"
    },
    profile: {
      pageTitle: "الملف الشخصي",
      pageSubtitle: "إدارة اللغة، حالة التفعيل، حالة المحفظة، وجلسة الحساب.",
      backToChat: "العودة إلى الدردشة",
      summaryTitle: "ملخص الملف الشخصي",
      fullNameLabel: "الاسم الكامل",
      emailLabel: "البريد الإلكتروني",
      valueUnavailable: "غير متاح",
      activationTitle: "حالة التفعيل",
      activationActive: "مفعّل",
      activationInactive: "غير مفعّل",
      activationUnknown: "غير معروف",
      initialInteractionLabel: "اكتمل التفاعل الأولي",
      registrationLabel: "اكتمل التسجيل",
      firstTasksLabel: "تم استلام أول المهام",
      preferencesTitle: "التفضيلات",
      languageLabel: "اللغة",
      walletTitle: "المحفظة",
      connectWallet: "ربط المحفظة",
      disconnectWallet: "فصل",
      walletConnectedStatus: "المحفظة متصلة.",
      walletDisconnectedStatus: "المحفظة غير متصلة.",
      walletConnected: "تم ربط المحفظة",
      walletDisconnected: "تم فصل المحفظة",
      languageSaved: "تم تحديث اللغة",
      sessionTitle: "الجلسة",
      sessionDescription: "سجّل الخروج بأمان وافصل حالة المحفظة المحلية.",
      logoutAction: "تسجيل الخروج",
      loggedOut: "تم تسجيل الخروج",
      loadingLabel: "جارٍ تحميل الملف الشخصي...",
      errorTitle: "تعذر تحميل الملف الشخصي",
      errorMessage: "حدث خطأ أثناء تحميل إعدادات الملف الشخصي.",
      retry: "إعادة المحاولة"
    },
    dashboard: {
      pageTitle: "لوحة التحكم",
      pageSubtitle: "بطاقات ما بعد التفعيل للإجراءات التالية وتتبع التقدم.",
      backToChat: "العودة إلى الدردشة",
      loadingLabel: "جارٍ تحميل لوحة التحكم...",
      errorTitle: "تعذر تحميل لوحة التحكم",
      errorMessage: "حدث خطأ أثناء تحميل بطاقات لوحة التحكم.",
      retry: "إعادة المحاولة",
      gatedTitle: "التفعيل مطلوب",
      gatedDescription: "أكمل التفعيل في الملف الشخصي لفتح بطاقات لوحة التحكم.",
      emptyTitle: "لا توجد بطاقات بعد",
      emptyDescription: "ستظهر بطاقاتك هنا عند توفرها.",
      statusIdle: "خامل",
      statusInProgress: "قيد التنفيذ",
      statusComplete: "مكتمل",
      statusBlocked: "محظور",
      priorityLabel: "الأولوية",
      progressLabel: "التقدم",
      priorityLow: "منخفضة",
      priorityMedium: "متوسطة",
      priorityHigh: "عالية",
      activationOverviewTitle: "نظرة عامة على التفعيل",
      activationOverviewActiveSummary: "حسابك مفعل وجاهز لسير العمل المتقدم.",
      activationOverviewPendingSummary: "أكمل مراحل التفعيل لفتح تجربة لوحة التحكم كاملة.",
      conversationHubTitle: "مركز المحادثات",
      conversationHubSummary: "تابع المحادثة مع المساعد ووسع إشارات مسار التحويل المكتشفة.",
      networkGrowthTitle: "الدعوة والنمو",
      networkGrowthSummary: "شارك دعوة الإحالة مع الفريق وتابع نمو التعاون.",
      historyReviewTitle: "مراجعة المحادثات",
      historyReviewSummary: "راجع المحادثات السابقة واستأنف المسارات ذات الأولوية.",
      goToChat: "اذهب إلى الدردشة",
      openProfile: "افتح الملف الشخصي",
      openChat: "افتح الدردشة",
      openReferral: "افتح الإحالة",
      openHistory: "افتح السجل"
    },
    locales: {
      en: {
        nativeName: "English",
        englishName: "الإنجليزية"
      },
      fa: {
        nativeName: "فارسی",
        englishName: "الفارسية"
      },
      ar: {
        nativeName: "العربية",
        englishName: "العربية"
      }
    }
  },
  fa: {
    common: {
      appName: "RAGAi"
    },
    language: {
      pageTitle: "زبان خود را انتخاب کنید",
      pageSubtitle: "برای کل تجربه برنامه زبان دلخواهتان را انتخاب کنید.",
      continueCta: "ادامه",
      selectedA11y: "زبان انتخاب‌شده",
      radioGroupLabel: "زبان‌های موجود",
      switcherLabel: "زبان",
      syncInProgress: "در حال ذخیره ترجیح زبان…",
      syncFailed: "زبان سرور و محلی متفاوت بود. ترجیح شما به‌صورت امن یکسان‌سازی شد."
    },
    voice: {
      pageTitle: "گفت‌وگوی صوتی",
      pageSubtitle: "طبیعی صحبت کنید و هر زمان به چت برگردید.",
      liveTranscriptTitle: "رونوشت زنده",
      liveTranscriptPlaceholder: "برای دیدن رونوشت شروع به صحبت کنید…",
      close: "بستن حالت صوتی",
      walletAriaLabel: "کیف پول",
      historyAriaLabel: "تاریخچه",
      returnToChat: "بازگشت به چت",
      switchToTyping: "تبدیل به تایپ",
      startListening: "شروع شنیدن",
      stopListening: "توقف شنیدن",
      startLabel: "شروع",
      stopLabel: "توقف",
      listeningStatus: "در حال شنیدن",
      processingStatus: "در حال پردازش",
      speakingStatus: "در حال پاسخ صوتی",
      idleStatus: "آماده",
      permissionDeniedStatus: "دسترسی میکروفون رد شد",
      errorStatus: "خطای صوتی",
      micPermissionPrompt: "برای شروع گفت‌وگوی صوتی دسترسی میکروفون را بدهید.",
      transcriptEmptyState: "هنوز رونوشتی وجود ندارد.",
      transcriptPartialLabel: "موقت",
      transcriptFinalLabel: "نهایی",
      ttsToggleOn: "پاسخ صوتی روشن",
      ttsToggleOff: "پاسخ صوتی خاموش",
      visualizerLabel: "پالس فعالیت صدا"
    },
    chatLanding: {
      newChat: "چت جدید",
      appWordmark: "QORA",
      onlineStatus: "ایجنت هوش مصنوعی آنلاین است",
      agentTitle: "ایجنت QORA",
      agentSubtitle: "آماده تحلیل، راهنمایی و خودکارسازی جریان کاری Web3 شما.",
      connectedWalletLabel: "کیف پول متصل است",
      connectWallet: "اتصال کیف پول",
      connectedWalletFallback: "کیف پول متصل است",
      conversationHistory: "تاریخچه گفتگو",
      profileAriaLabel: "باز کردن پروفایل",
      menuAriaLabel: "باز کردن منو",
      sideNavAriaLabel: "ناوبری ایجنت",
      mobileNavAriaLabel: "ناوبری موبایل",
      contextPanelTitle: "کانتکست",
      capabilitiesPanelTitle: "قابلیت‌های فعال",
      memoryPanelTitle: "حافظه اخیر",
      securityPanelTitle: "امنیت و کیف پول",
      contextCapabilitiesDescription: "قابلیت‌های RAG، بازیابی حافظه و هماهنگی صوتی آماده هستند.",
      contextMemoryDescription: "آخرین موضوع را ادامه دهید و پیوستگی گفتگو را حفظ کنید.",
      contextSecurityDescription: "بررسی‌های آگاه از کیف پول و محافظت هویت فعال است.",
      quickActionsTitle: "اقدام‌های سریع",
      quickActionDashboard: "داشبورد",
      quickActionHistory: "تاریخچه",
      quickActionReferral: "دعوت",
      quickActionVoice: "صدا",
      capabilityRag: "RAG",
      capabilityMemory: "حافظه",
      capabilityVoice: "صدا",
      capabilityWalletAware: "آگاه از کیف پول",
      promptWalletRiskTitle: "تحلیل ریسک کیف پول",
      promptWalletRiskDescription: "ریسک و وضعیت امنیتی را بررسی کنید.",
      promptWalletRiskPrompt: "ریسک کیف پول من را تحلیل کن و آسیب‌پذیری‌های اصلی را خلاصه کن.",
      promptEcosystemTitle: "توضیح اکوسیستم QORA",
      promptEcosystemDescription: "یک مرور خلاصه از اکوسیستم بگیر.",
      promptEcosystemPrompt: "اکوسیستم QORA را توضیح بده و بگو هر بخش چگونه با هم کار می‌کند.",
      promptEarningTitle: "یافتن فرصت‌های درآمدی",
      promptEarningDescription: "مسیرهای رشد کاربردی را پیدا کن.",
      promptEarningPrompt: "بر اساس پروفایل فعلی Web3 من فرصت‌های درآمدی پیدا کن.",
      promptContinueTitle: "ادامه موضوع قبلی",
      promptContinueDescription: "از آخرین کانتکست ادامه بده.",
      promptContinuePrompt: "موضوع قبلی من را ادامه بده و بهترین اقدام بعدی را پیشنهاد کن.",
      promptSectionTitle: "پرامپت‌های پیشنهادی",
      promptSectionDescription: "با یک پرامپت هدایت‌شده شروع کنید یا درخواست خودتان را بنویسید.",
      emptyTitle: "اولین گفتگوی خود را شروع کنید",
      emptyDescription: "برای شروع یک سوال بپرسید یا هدفتان را بنویسید.",
      chatMetaNow: "اکنون",
      chatMetaSources: "منبع",
      chatMetaFeedback: "بازخورد",
      funnelTitle: "کشف قیف",
      addAction: "افزودن اقدام",
      micAriaLabel: "باز کردن ورودی صوتی",
      sendAriaLabel: "ارسال پیام",
      inputAriaLabel: "ورودی پیام",
      messagePlaceholder: "پیام خود را بنویسید...",
      send: "ارسال",
      voice: "صدا",
      navAgent: "ایجنت",
      navHistory: "تاریخچه",
      navDashboard: "داشبورد",
      navAddFriend: "افزودن دوست",
      navVoice: "صدا",
      navProfile: "پروفایل",
      newChatGateRequiresAuth: "ابتدا وارد حساب شوید.",
      newChatGateRequiresActivation: "برای شروع چت جدید فعال‌سازی لازم است.",
      newChatGateRequiresInitialInteraction: "ابتدا تعامل اولیه را تکمیل کنید.",
      newChatGateRequiresRegistration: "مرحله ثبت‌نام هنوز کامل نشده است.",
      newChatGateRequiresFirstTasks: "تا دریافت اولین وظایف صبر کنید.",
      typingStatus: "دستیار در حال فکر کردن است...",
      historyPlaceholderTitle: "تاریخچه",
      historyPlaceholderDescription: "صفحه تاریخچه گفتگو در این بخش نمایش داده می‌شود.",
      referralPlaceholderTitle: "دعوت",
      referralPlaceholderDescription: "صفحه دعوت برای فاز بعدی آماده است.",
      historyEntryTitle: "ادامه این موضوع",
      historyEntryDescription: "پیش از نوشتن پیام بعدی، روش ادامه این موضوع را انتخاب کنید.",
      historyEntryTopicFallback: "موضوع انتخاب‌شده",
      historyEntryContinue: "ادامه گفتگو",
      historyEntryStartNew: "شروع گفتگوی جدید"
    },
    agentLanding: {
      cardsSectionTitle: "ماژول‌های ایجنت",
      cardsSectionSubtitle: "برای ادامه مسیر با راهنمایی QORA یک ماژول را انتخاب کنید.",
      cardOpenAction: "باز کردن",
      cards: {
        myStatusNextBestAction: {
          title: "وضعیت من / اقدام بعدی",
          description: "پیشرفت فعلی‌تان را ببینید و بهترین اقدام بعدی را دریافت کنید."
        },
        earnViaMicrotasks: {
          title: "کسب درآمد با میکروتسک",
          description: "میکروتسک‌های قابل انجام را پیدا کنید و مسیر درآمد را بهینه کنید."
        },
        securityRiskCheck: {
          title: "امنیت و بررسی ریسک",
          description: "با بررسی‌های آگاه از کیف پول، ریسک‌ها را شناسایی و حساب را ایمن کنید."
        },
        investingStrategy: {
          title: "استراتژی سرمایه‌گذاری",
          description: "راهنمایی سرمایه‌گذاری متناسب با پروفایل Web3 خود دریافت کنید."
        },
        referralTeamGrowth: {
          title: "دعوت و رشد شبکه",
          description: "شبکه خود را گسترش دهید و رشد مبتنی بر دعوت را دنبال کنید."
        },
        qora101EcosystemGuide: {
          title: "QORA 101 / راهنمای اکوسیستم",
          description: "مبانی QORA، مفاهیم کلیدی و جریان‌های اصلی اکوسیستم را یاد بگیرید."
        },
        helpTroubleshooting: {
          title: "کمک و عیب‌یابی",
          description: "برای خطاها، موانع و مشکلات راه‌اندازی پشتیبانی بگیرید."
        }
      },
      onboarding: {
        title: "به ایجنت QORA خوش آمدید",
        subtitle: "با راهنمای شروع مرحله‌ای، مسیر شخصی‌سازی‌شده خود را فعال کنید.",
        start: "چطور شروع کنم",
        nextStep: "قدم بعدی",
        howToStart: "چطور شروع کنم",
        wantToJoin: "می‌خواهم عضو شوم",
        actionsTitle: "اقدام‌های شروع"
      },
      gating: {
        connectWallet: "اتصال کیف پول",
        completeActivation: "تکمیل فعال‌سازی",
        continueOnboarding: "ادامه شروع",
        walletRequired: "این ماژول به کیف پول متصل نیاز دارد.",
        activationRequired: "این ماژول پس از فعال‌سازی حساب باز می‌شود.",
        onboardingRequired: "برای دسترسی به این ماژول، مراحل شروع را کامل کنید."
      },
      entryContext: {
        inviteOnboarding: "ورود از دعوت‌نامه",
        postRegistration: "پس از ثبت‌نام",
        returningUser: "کاربر بازگشتی"
      }
    },
    history: {
      pageTitle: "تاریخچه گفتگو",
      pageSubtitle: "گفتگوهای قبلی را ببینید و هرکدام را دوباره باز کنید.",
      backToChat: "بازگشت به چت",
      searchPlaceholder: "جستجو در گفتگوها...",
      searchAriaLabel: "جستجو در تاریخچه گفتگو",
      clearSearch: "پاک کردن",
      groupToday: "امروز",
      groupYesterday: "دیروز",
      groupLast7Days: "۷ روز گذشته",
      groupLast30Days: "۳۰ روز گذشته",
      groupOlder: "قدیمی‌تر",
      statusActive: "فعال",
      statusArchived: "بایگانی‌شده",
      openConversationAria: "باز کردن گفتگو",
      untitledConversation: "گفتگوی بدون عنوان",
      noPreview: "پیش‌نمایشی موجود نیست.",
      emptyTitle: "هنوز گفتگویی وجود ندارد",
      emptyDescription: "برای ساخت تاریخچه، یک چت جدید شروع کنید.",
      emptySearchTitle: "موردی پیدا نشد",
      emptySearchDescription: "عبارت جستجوی دیگری را امتحان کنید.",
      loadingLabel: "در حال بارگذاری تاریخچه گفتگو...",
      errorTitle: "بارگذاری تاریخچه انجام نشد",
      errorMessage: "در بارگذاری تاریخچه گفتگو خطایی رخ داد.",
      retry: "تلاش دوباره",
      topicGroupsAriaLabel: "گروه‌های موضوعی",
      topicConversationCountLabel: "گفتگو",
      topicLatestActivityLabel: "آخرین فعالیت",
      recentConversationsLabel: "گفتگوهای اخیر",
      openTopicAction: "باز کردن موضوع"
    },
    referral: {
      pageTitle: "دعوت دوستان",
      pageSubtitle: "لینک دعوت خود را به اشتراک بگذارید و دوستانتان را به RAGAi دعوت کنید.",
      backToChat: "بازگشت به چت",
      totalInvitesLabel: "کل دعوت‌ها",
      activatedQoraLabel: "فعال‌سازی QORA",
      firstMicroTaskLabel: "اولین میکروتسک",
      firstAchievementLabel: "اولین دستاورد",
      createPanelTitle: "ایجاد لینک دعوت",
      createPanelSubtitle: "همین حالا یک لینک دعوت عادی بسازید یا سفارشی‌سازی را برای بعد آماده کنید.",
      addLinkButton: "افزودن لینک",
      draftTitle: "پیش‌نویس لینک دعوت",
      defaultDraftLabel: "لینک ارجاع من",
      draftLabel: "برچسب لینک",
      draftUrlPreview: "پیش‌نمایش لینک کوتاه",
      selectColorLabel: "رنگ تگ",
      doneButton: "تکمیل",
      customizeButton: "سفارشی‌سازی",
      tagColors: {
        blue: "آبی",
        violet: "بنفش",
        cyan: "فیروزه‌ای",
        green: "سبز",
        orange: "نارنجی",
        pink: "صورتی",
        gold: "طلایی",
        gray: "خاکستری"
      },
      statusButton: "وضعیت",
      chatButton: "چت",
      agentContextAttached: "زمینه عامل پیوست شد",
      chatDisabledUntilWallet: "چت پس از اتصال کیف پول فعال می‌شود",
      statusPanelPlaceholder: "جزئیات وضعیت با ورود رویدادهای ارجاع اینجا نمایش داده می‌شود.",
      chatPanelPlaceholder: "پیش‌نمایش چت ارجاع در مرحله بعد اینجا نمایش داده می‌شود.",
      chatPanelTitle: "چت ارجاع",
      chatLoadingLabel: "در حال بارگذاری چت ارجاع",
      chatEmptyTitle: "هنوز پیامی وجود ندارد",
      chatEmptyDescription: "وقتی دعوت‌شونده آماده بود گفت‌وگوی ارجاع را شروع کنید.",
      chatLoadError: "بارگذاری چت ارجاع انجام نشد.",
      chatSendErrorTitle: "ارسال پیام انجام نشد",
      chatInputPlaceholder: "پیام بنویسید",
      chatSendButton: "ارسال",
      chatSendAriaLabel: "ارسال پیام چت ارجاع",
      chatUnreadBadgeLabel: "پیام‌های خوانده‌نشده",
      chatReferrerLabel: "دعوت‌کننده",
      chatInviteeLabel: "دعوت‌شونده",
      chatDeliverySent: "ارسال شد",
      chatDeliveryDelivered: "تحویل شد",
      chatDeliveryRead: "خوانده شد",
      chatShowOriginal: "مشاهده متن اصلی",
      chatShowTranslation: "نمایش ترجمه",
      chatOriginalTextLabel: "متن اصلی",
      chatTranslatedTextLabel: "ترجمه‌شده",
      chatTranslationUnavailable: "ترجمه هنوز آماده نیست.",
      chatTranslationLoading: "در حال بارگذاری ترجمه",
      chatTranslationFailed: "ترجمه انجام نشد",
      createLinkSuccessTitle: "لینک دعوت ایجاد شد",
      createLinkErrorTitle: "ایجاد لینک دعوت انجام نشد",
      createCustomizedLinkSuccessTitle: "لینک دعوت سفارشی ایجاد شد",
      createCustomizedLinkErrorTitle: "ایجاد لینک دعوت سفارشی انجام نشد",
      linkUpdatedTitle: "لینک دعوت به‌روزرسانی شد",
      linkUpdateErrorTitle: "به‌روزرسانی لینک دعوت انجام نشد",
      statusLoadWarningTitle: "بارگذاری جزئیات وضعیت انجام نشد",
      statusCreated: "ایجاد شد",
      statusInviteOpened: "دعوت باز شد",
      statusWalletConnected: "کیف پول متصل شد",
      statusQoraActivated: "QORA فعال شد",
      statusFirstMicrotaskCompleted: "اولین میکروتسک تکمیل شد",
      statusFirstAchievementUnlocked: "اولین دستاورد باز شد",
      copyButton: "کپی",
      shareButton: "اشتراک‌گذاری",
      copySuccessTitle: "دعوت کپی شد",
      copyErrorTitle: "کپی دعوت انجام نشد",
      shareSuccessTitle: "اشتراک‌گذاری باز شد",
      shareUnavailableTitle: "اشتراک‌گذاری در این دستگاه پشتیبانی نمی‌شود",
      shareErrorTitle: "اشتراک‌گذاری دعوت انجام نشد",
      noDataTitle: "هنوز داده دعوت وجود ندارد",
      noDataDescription: "وقتی داده دعوت آماده باشد در اینجا نمایش داده می‌شود.",
      statusTimeline: {
        panelTitle: "خط زمان پیشرفت",
        invited: "دعوت شد",
        connectedWallet: "اتصال کیف پول",
        activatedQora: "فعال‌سازی QORA",
        firstMicrotask: "اولین میکروتسک",
        firstAchievement: "اولین دستاورد",
        completed: "تکمیل‌شده",
        current: "فعلی",
        upcoming: "پیش‌رو",
        noActivity: "هنوز فعالیتی ثبت نشده"
      },
      personalizationWizard: {
        title: "سفارشی‌سازی کانتکست دعوت",
        subtitle: "قبل از اشتراک‌گذاری، کانتکست مدعو را برای ایجنت مشخص کنید.",
        progressA11yLabel: "پیشرفت ویزارد",
        closeAriaLabel: "بستن ویزارد شخصی‌سازی",
        backButton: "قبلی",
        nextButton: "بعدی",
        doneButton: "تکمیل",
        optionalBadge: "اختیاری",
        multiSelectHint: "یک یا چند گزینه را انتخاب کنید",
        requiredAnswerError: "برای ادامه یک پاسخ انتخاب کنید.",
        unsavedTitle: "از تغییرات صرف‌نظر شود؟",
        unsavedDescription: "پاسخ‌های شخصی‌سازی ذخیره نشده‌اند.",
        unsavedStayButton: "ادامه ویرایش",
        unsavedDiscardButton: "صرف‌نظر",
        steps: {
          inviteeRelationship: {
            title: "نوع رابطه",
            tooltip: "به تنظیم لحن و کانتکست دعوت کمک می‌کند.",
            question: "رابطه شما با این مدعو چیست؟",
            options: {
              friend: "دوست",
              family: "خانواده",
              colleague: "همکار",
              community: "آشنای جامعه",
              other: "سایر"
            }
          },
          familiarityLevel: {
            title: "میزان آشنایی",
            tooltip: "برای تنظیم عمق راهنمایی استفاده می‌شود.",
            question: "چقدر این فرد را می‌شناسید؟",
            options: {
              knowWell: "خیلی خوب می‌شناسم",
              somewhat: "تا حدی",
              justMet: "تازگی آشنا شده‌ام",
              onlineOnly: "فقط آنلاین",
              dontKnow: "نمی‌دانم"
            }
          },
          invitationReason: {
            title: "دلیل دعوت",
            tooltip: "مشخص می‌کند چرا این دعوت مهم است.",
            question: "چرا این شخص را دعوت می‌کنید؟",
            options: {
              learnAndEarn: "یادگیری و درآمد",
              ecosystemAccess: "دسترسی به اکوسیستم QORA",
              guidedOnboarding: "آن‌بوردینگ هدایت‌شده",
              teamGrowth: "رشد تیم/شبکه",
              curiousExplore: "فقط برای بررسی"
            }
          },
          primaryMotivation: {
            title: "انگیزه اصلی",
            tooltip: "برای شخصی‌سازی هدف آن‌بوردینگ استفاده می‌شود.",
            question: "چه چیزی بیشترین انگیزه را برای او ایجاد می‌کند؟",
            options: {
              earnRewards: "کسب پاداش",
              learnWeb3: "یادگیری Web3",
              productivity: "افزایش بهره‌وری",
              communityStatus: "جایگاه اجتماعی",
              curiosity: "کنجکاوی"
            }
          },
          web3FamiliarityLevel: {
            title: "آشنایی با Web3",
            tooltip: "سطح پیچیدگی محتوای پیشنهادی را تعیین می‌کند.",
            question: "سطح آشنایی او با Web3 چقدر است؟",
            options: {
              newcomer: "تازه‌کار",
              basic: "مبتدی",
              intermediate: "متوسط",
              advanced: "پیشرفته",
              dontKnow: "نمی‌دانم"
            }
          },
          previousWeb3ToolExperience: {
            title: "تجربه ابزارها",
            tooltip: "تجربه قبلی را به مسیر مناسب آن‌بوردینگ وصل می‌کند.",
            question: "قبلاً از چه ابزارهای Web3 استفاده کرده است؟",
            options: {
              none: "هیچ‌کدام",
              walletOnly: "فقط کیف پول",
              defiOrNft: "ابزارهای DeFi یا NFT",
              daoOrGovernance: "ابزارهای DAO/حاکمیت",
              multipleTools: "چند ابزار مختلف"
            }
          },
          readinessToTakeAction: {
            title: "آمادگی اقدام",
            tooltip: "برای ترتیب‌دهی نودج‌های فعال‌سازی استفاده می‌شود.",
            question: "چقدر برای اقدام آماده است؟",
            options: {
              readyNow: "الان آماده است",
              thisWeek: "احتمالاً این هفته",
              needGuidance: "به راهنمایی گام‌به‌گام نیاز دارد",
              researching: "هنوز در حال بررسی است",
              unsure: "مطمئن نیست"
            }
          },
          concernsAndFrictions: {
            title: "نگرانی‌ها",
            tooltip: "شناسایی موانع، ریسک ریزش را کاهش می‌دهد.",
            question: "چه نگرانی‌ها یا اصطکاک‌هایی ممکن است مانع شوند؟",
            options: {
              security: "ریسک‌های امنیتی",
              fundSafety: "امنیت دارایی",
              complexity: "پیچیدگی زیاد",
              timeCommitment: "زمان مورد نیاز",
              fees: "کارمزدها",
              privacy: "نگرانی حریم خصوصی",
              noConcerns: "نگرانی مهمی ندارد"
            }
          },
          previousNegativeExperience: {
            title: "تجربه منفی قبلی",
            tooltip: "به پیام‌رسانی امن‌تر و اعتمادمحور کمک می‌کند.",
            question: "آیا قبلاً تجربه منفی در Web3 داشته است؟",
            options: {
              none: "خیر",
              scamAttempt: "تلاش کلاهبرداری/فیشینگ",
              lostFunds: "از دست دادن دارایی",
              highFees: "کارمزد غیرمنتظره بالا",
              confusingUx: "تجربه کاربری گیج‌کننده",
              dontKnow: "نمی‌دانم"
            }
          },
          preferredInformationStyle: {
            title: "سبک اطلاعات",
            tooltip: "روش ارائه محتوا را با ترجیح کاربر هماهنگ می‌کند.",
            question: "ترجیح می‌دهد اطلاعات را چگونه دریافت کند؟",
            options: {
              simpleSteps: "گام‌های ساده",
              visualExamples: "نمونه‌های تصویری",
              comparisons: "مقایسه‌ای",
              dataDriven: "داده‌محور",
              conversational: "مکالمه‌ای"
            }
          },
          suggestedEcosystemSection: {
            title: "بخش پیشنهادی",
            tooltip: "او را اول به مرتبط‌ترین بخش هدایت می‌کند.",
            question: "بهتر است از کدام بخش اکوسیستم شروع کند؟",
            options: {
              gettingStarted: "شروع کار",
              microtasks: "میکروتسک‌ها",
              achievements: "دستاوردها",
              walletSecurity: "امنیت کیف پول",
              community: "جامعه"
            }
          },
          conversionLikelihood: {
            title: "احتمال تبدیل",
            tooltip: "برای اولویت‌بندی دعوت‌ها استفاده می‌شود.",
            question: "احتمال تبدیل او را چقدر می‌دانید؟",
            options: {
              veryHigh: "خیلی زیاد",
              high: "زیاد",
              medium: "متوسط",
              low: "کم",
              veryLow: "خیلی کم"
            }
          },
          additionalNote: {
            title: "یادداشت تکمیلی",
            tooltip: "کانتکست اختیاری که به ایجنت کمک می‌کند.",
            question: "نکته دیگری هست که باید بدانیم؟",
            placeholder: "اگر لازم است، کانتکست بیشتری درباره این مدعو اضافه کنید..."
          }
        }
      },
      loadingLabel: "در حال بارگذاری اطلاعات دعوت...",
      errorTitle: "بارگذاری اطلاعات دعوت انجام نشد",
      errorMessage: "در بارگذاری اطلاعات دعوت خطایی رخ داد.",
      retry: "تلاش دوباره",
      statsTitle: "آمار دعوت",
      totalReferralsLabel: "تعداد دعوت‌ها",
      totalRewardsLabel: "مجموع پاداش‌ها",
      valueUnavailable: "ناموجود"
    },
    profile: {
      pageTitle: "پروفایل",
      pageSubtitle: "مدیریت زبان، وضعیت فعال‌سازی، وضعیت کیف پول و نشست حساب.",
      backToChat: "بازگشت به چت",
      summaryTitle: "خلاصه پروفایل",
      fullNameLabel: "نام کامل",
      emailLabel: "ایمیل",
      valueUnavailable: "ناموجود",
      activationTitle: "وضعیت فعال‌سازی",
      activationActive: "فعال",
      activationInactive: "غیرفعال",
      activationUnknown: "نامشخص",
      initialInteractionLabel: "تعامل اولیه تکمیل شده",
      registrationLabel: "ثبت‌نام تکمیل شده",
      firstTasksLabel: "اولین وظایف دریافت شده",
      preferencesTitle: "تنظیمات",
      languageLabel: "زبان",
      walletTitle: "کیف پول",
      connectWallet: "اتصال کیف پول",
      disconnectWallet: "قطع اتصال",
      walletConnectedStatus: "کیف پول متصل است.",
      walletDisconnectedStatus: "کیف پول متصل نیست.",
      walletConnected: "کیف پول متصل شد",
      walletDisconnected: "کیف پول قطع شد",
      languageSaved: "زبان به‌روزرسانی شد",
      sessionTitle: "نشست",
      sessionDescription: "با خیال راحت خارج شوید و وضعیت کیف پول محلی را قطع کنید.",
      logoutAction: "خروج",
      loggedOut: "خارج شدید",
      loadingLabel: "در حال بارگذاری پروفایل...",
      errorTitle: "بارگذاری پروفایل انجام نشد",
      errorMessage: "در بارگذاری تنظیمات پروفایل خطایی رخ داد.",
      retry: "تلاش دوباره"
    },
    dashboard: {
      pageTitle: "داشبورد",
      pageSubtitle: "کارت‌های پس از فعال‌سازی برای اقدام بعدی و پایش پیشرفت.",
      backToChat: "بازگشت به چت",
      loadingLabel: "در حال بارگذاری داشبورد...",
      errorTitle: "بارگذاری داشبورد انجام نشد",
      errorMessage: "در بارگذاری کارت‌های داشبورد خطایی رخ داد.",
      retry: "تلاش دوباره",
      gatedTitle: "نیاز به فعال‌سازی",
      gatedDescription: "برای باز شدن کارت‌های داشبورد، فعال‌سازی را در پروفایل کامل کنید.",
      emptyTitle: "هنوز کارتی وجود ندارد",
      emptyDescription: "وقتی کارت‌ها آماده شوند اینجا نمایش داده می‌شوند.",
      statusIdle: "آماده",
      statusInProgress: "در حال انجام",
      statusComplete: "تکمیل",
      statusBlocked: "مسدود",
      priorityLabel: "اولویت",
      progressLabel: "پیشرفت",
      priorityLow: "کم",
      priorityMedium: "متوسط",
      priorityHigh: "زیاد",
      activationOverviewTitle: "نمای کلی فعال‌سازی",
      activationOverviewActiveSummary: "حساب شما فعال است و برای جریان‌های پیشرفته آماده است.",
      activationOverviewPendingSummary: "مراحل فعال‌سازی را کامل کنید تا تجربه کامل داشبورد باز شود.",
      conversationHubTitle: "مرکز گفتگو",
      conversationHubSummary: "گفتگو با دستیار را ادامه دهید و سیگنال‌های قیف کشف‌شده را گسترش دهید.",
      networkGrowthTitle: "دعوت و رشد",
      networkGrowthSummary: "دعوت‌نامه را با هم‌تیمی‌ها به اشتراک بگذارید و رشد همکاری را دنبال کنید.",
      historyReviewTitle: "مرور گفتگوها",
      historyReviewSummary: "گفتگوهای قبلی را مرور کنید و مسیرهای مهم را ادامه دهید.",
      goToChat: "رفتن به چت",
      openProfile: "باز کردن پروفایل",
      openChat: "باز کردن چت",
      openReferral: "باز کردن دعوت",
      openHistory: "باز کردن تاریخچه"
    },
    locales: {
      en: {
        nativeName: "English",
        englishName: "English"
      },
      fa: {
        nativeName: "فارسی",
        englishName: "Persian"
      },
      ar: {
        nativeName: "العربية",
        englishName: "Arabic"
      }
    }
  }
};

export function getMessages(locale: AppLocale): MessagesSchema {
  return messages[locale];
}
