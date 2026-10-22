import { Copy, Share2 } from "lucide-react";
import { Button } from "@/components/ui";
import type { ReferralLinkSummary } from "@/services/referral";

interface ReferralLinkActionsProps {
  link: ReferralLinkSummary;
  labels: { copy: string; share: string };
  onCopySuccess: () => void;
  onCopyError: () => void;
  onShareSuccess: () => void;
  onShareUnavailable: () => void;
  onShareError: () => void;
}

function buildSharePayload(link: ReferralLinkSummary): ShareData {
  return {
    title: link.label,
    text: link.shortUrl,
    url: link.shortUrl,
  };
}

function copyToClipboard(value: string): Promise<void> {
  if (!navigator.clipboard || typeof navigator.clipboard.writeText !== "function") {
    return Promise.reject(new Error("Clipboard API unavailable"));
  }
  return navigator.clipboard.writeText(value);
}

export function ReferralLinkActions({
  link,
  labels,
  onCopySuccess,
  onCopyError,
  onShareSuccess,
  onShareUnavailable,
  onShareError,
}: ReferralLinkActionsProps) {
  const handleCopy = async () => {
    try {
      await copyToClipboard(link.shortUrl);
      onCopySuccess();
    } catch {
      onCopyError();
    }
  };

  const handleShare = async () => {
    if (!navigator.share || typeof navigator.share !== "function") {
      onShareUnavailable();
      return;
    }
    try {
      await navigator.share(buildSharePayload(link));
      onShareSuccess();
    } catch {
      onShareError();
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button variant="secondary" size="sm" onClick={() => void handleShare()}>
        <Share2 className="h-4 w-4" aria-hidden="true" />
        {labels.share}
      </Button>
      <Button variant="secondary" size="sm" onClick={() => void handleCopy()}>
        <Copy className="h-4 w-4" aria-hidden="true" />
        {labels.copy}
      </Button>
    </div>
  );
}
