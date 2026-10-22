import type { PropsWithChildren } from "react";
import { MotionPage, PageContainer, ScreenShell, SectionContainer } from "@/components/ui";

interface ReferralDashboardPageProps extends PropsWithChildren {
  className?: string;
}

export function ReferralDashboardPage({ className = "", children }: ReferralDashboardPageProps) {
  return (
    <ScreenShell className="agent-premium-surface">
      <PageContainer className="py-8 sm:py-10">
        <MotionPage>
          <SectionContainer className={`mx-auto w-full max-w-5xl space-y-4 ${className}`.trim()}>{children}</SectionContainer>
        </MotionPage>
      </PageContainer>
    </ScreenShell>
  );
}
