// ── SKPL: MobileGuard — blocks or degrades features on mobile ────────────────
import { AlertTriangle } from 'lucide-react';
import { useFeatureDegrade } from '@/hooks/useMobileDegrade';
import { useTranslation } from '@/i18n/useI18n';

interface MobileGuardProps {
  /** Feature identifier matching MOBILE_DEGRADE_RULES */
  feature: string;
  /** Children to render when feature is available */
  children: React.ReactNode;
  /** Optional: custom fallback for blocked features */
  fallback?: React.ReactNode;
}

/**
 * Wraps page content and enforces mobile degradation rules.
 *
 * - 'full' blocked features show an alert with an explanation
 * - 'readonly' / 'simplified' features pass through (pages handle it internally)
 * - 'none' / desktop: renders children normally
 */
export function MobileGuard({ feature, children, fallback }: MobileGuardProps) {
  const { t } = useTranslation();
  const { isBlocked, isMobile, reasonKey, labelKey } = useFeatureDegrade(feature);

  if (!isMobile) {
    return <>{children}</>;
  }

  if (isBlocked) {
    if (fallback) {
      return <>{fallback}</>;
    }

    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center gap-4">
        <div className="rounded-full bg-amber-500/10 p-4">
          <AlertTriangle className="h-8 w-8 text-amber-500" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-foreground">
            {t('mobile.blocked.title', { feature: t(labelKey) })}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-md">
            {t(reasonKey)}
          </p>
        </div>
        <p className="text-xs text-muted-foreground">
          {t('mobile.blocked.hint')}
        </p>
      </div>
    );
  }

  return <>{children}</>;
}