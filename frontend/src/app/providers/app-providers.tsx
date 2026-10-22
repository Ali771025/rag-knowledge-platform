import type { PropsWithChildren } from "react";
import { useEffect } from "react";
import { QueryProvider } from "./query-provider";
import { ThemeProvider } from "./theme-provider";
import { AppMotionProvider } from "./motion-provider";
import { I18nProvider } from "@/i18n";
import { ToastProvider } from "@/components/ui";
import { bootstrapServerLanguageSync } from "@/features/language/language-sync-bootstrap";

function LanguageSyncBootstrap() {
  useEffect(() => {
    void bootstrapServerLanguageSync();
  }, []);

  return null;
}

export function AppProviders({ children }: PropsWithChildren) {
  return (
    <ThemeProvider>
      <I18nProvider>
        <AppMotionProvider>
          <QueryProvider>
            <ToastProvider>
              <LanguageSyncBootstrap />
              {children}
            </ToastProvider>
          </QueryProvider>
        </AppMotionProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
