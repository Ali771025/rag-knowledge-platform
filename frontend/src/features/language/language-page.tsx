import { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { motion, useReducedMotion } from "framer-motion";
import { appRoutes } from "@/app/routes/contracts";
import { CardShell, PageContainer, ScreenShell, SectionContainer, Button } from "@/components/ui";
import { LanguageSwitcher } from "@/components/i18n";
import { dsMotionVariants, dsTypography } from "@/design-system";
import { type AppLocale, useI18n } from "@/i18n";
import { routeForPostLanguageEntry, useLanguageStore } from "@/state/language-store";
import { syncLanguagePreference } from "./language-sync";
import { useToast } from "@/hooks/use-toast";

export function LanguagePage() {
  const navigate = useNavigate();
  const location = useLocation();
  const shouldReduceMotion = useReducedMotion();
  const { locale, messages } = useI18n();
  const { warning } = useToast();
  const persistedLocale = useLanguageStore((state) => state.locale);
  const [isSyncing, setIsSyncing] = useState(false);

  const [selectedLocale, setSelectedLocale] = useState<AppLocale>(persistedLocale ?? locale);

  const nextPath = useMemo(() => routeForPostLanguageEntry(selectedLocale), [selectedLocale]);
  const fromPath =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? null;

  const handleContinue = async () => {
    if (isSyncing) return;
    setIsSyncing(true);
    try {
      const result = await syncLanguagePreference({
        desiredLocale: selectedLocale,
        strategy: "prefer-local"
      });
      if (result.source !== "local") {
        warning(messages.language.syncFailed);
      }
      const destination = fromPath && fromPath !== appRoutes.language ? fromPath : nextPath || appRoutes.agent;
      navigate(destination, { replace: true });
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <ScreenShell>
      <PageContainer className="py-8 sm:py-10">
        <SectionContainer className="mx-auto flex min-h-[calc(100dvh-5rem)] w-full max-w-3xl items-center justify-center">
          <motion.div
            className="w-full"
            variants={shouldReduceMotion ? undefined : dsMotionVariants.fadeIn}
            initial={shouldReduceMotion ? false : "hidden"}
            animate="visible"
          >
            <CardShell className="p-5 sm:p-8">
              <header className="mb-6 space-y-2 text-center">
                <h1 className={dsTypography.displayTitle}>{messages.language.pageTitle}</h1>
                <p className="mx-auto max-w-xl text-sm text-muted-foreground sm:text-base">{messages.language.pageSubtitle}</p>
              </header>

              <LanguageSwitcher value={selectedLocale} onChange={setSelectedLocale} />

              <div className="mt-6 flex justify-center">
                <Button variant="primary" size="lg" onClick={() => void handleContinue()} className="min-w-44" disabled={isSyncing}>
                  {isSyncing ? messages.language.syncInProgress : messages.language.continueCta}
                </Button>
              </div>
            </CardShell>
          </motion.div>
        </SectionContainer>
      </PageContainer>
    </ScreenShell>
  );
}
