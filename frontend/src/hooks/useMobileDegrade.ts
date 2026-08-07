// ── SKPL: Mobile feature degradation rules ─────────────────────────────────
// 13 rules that define which features are restricted on mobile devices.
// These rules are used by the MobileGuard component and individual pages
// to conditionally disable or adapt features for mobile.

import { useIsMobile } from '@/hooks/use-mobile';

/** Degradation level for a feature on mobile */
export type DegradeLevel = 'full' | 'readonly' | 'simplified' | 'none';

export interface FeatureDegradeRule {
  /** Feature identifier */
  feature: string;
  /** Display name (i18n key) */
  labelKey: string;
  /** Degradation level on mobile */
  level: DegradeLevel;
  /** Explanation shown to user (i18n key) */
  reasonKey: string;
}

/** All 13 mobile feature degradation rules */
export const MOBILE_DEGRADE_RULES: FeatureDegradeRule[] = [
  // 1. Desktop automation — GUI automation needs local desktop node
  {
    feature: 'desktop',
    labelKey: 'nav.desktop',
    level: 'full',
    reasonKey: 'mobile.degrade.desktop',
  },
  // 2. Code generation — full IDE features need desktop
  {
    feature: 'code-generation',
    labelKey: 'nav.codeGeneration',
    level: 'full',
    reasonKey: 'mobile.degrade.codeGeneration',
  },
  // 3. Credential management — sensitive operations need desktop
  {
    feature: 'credential',
    labelKey: 'nav.credential',
    level: 'full',
    reasonKey: 'mobile.degrade.credential',
  },
  // 4. Context — read-only on mobile (no file tree editing)
  {
    feature: 'context',
    labelKey: 'nav.context',
    level: 'readonly',
    reasonKey: 'mobile.degrade.context',
  },
  // 5. Setup — simplified onboarding
  {
    feature: 'setup',
    labelKey: 'nav.setup',
    level: 'simplified',
    reasonKey: 'mobile.degrade.setup',
  },
  // 6. Knowledge base — read-only + search on mobile
  {
    feature: 'knowledge',
    labelKey: 'nav.knowledge',
    level: 'readonly',
    reasonKey: 'mobile.degrade.knowledge',
  },
  // 7. Schedule — read-only view
  {
    feature: 'schedule',
    labelKey: 'nav.schedule',
    level: 'readonly',
    reasonKey: 'mobile.degrade.schedule',
  },
  // 8. Updates — notification view only
  {
    feature: 'updates',
    labelKey: 'nav.updates',
    level: 'readonly',
    reasonKey: 'mobile.degrade.updates',
  },
  // 9. Buglog — read-only
  {
    feature: 'buglog',
    labelKey: 'nav.buglog',
    level: 'readonly',
    reasonKey: 'mobile.degrade.buglog',
  },
  // 10. Firecrawl — simplified
  {
    feature: 'firecrawl',
    labelKey: 'nav.firecrawl',
    level: 'simplified',
    reasonKey: 'mobile.degrade.firecrawl',
  },
  // 11. Web Intelligence — simplified
  {
    feature: 'web-intelligence',
    labelKey: 'nav.webIntelligence',
    level: 'simplified',
    reasonKey: 'mobile.degrade.webIntelligence',
  },
  // 12. Dashboard — simplified
  {
    feature: 'dashboard',
    labelKey: 'nav.dashboard',
    level: 'simplified',
    reasonKey: 'mobile.degrade.dashboard',
  },
  // 13. Team — member view only
  {
    feature: 'team',
    labelKey: 'nav.team',
    level: 'readonly',
    reasonKey: 'mobile.degrade.team',
  },
];

/** Get degradation level for a specific feature */
export function getDegradeLevel(feature: string): DegradeLevel {
  const rule = MOBILE_DEGRADE_RULES.find((r) => r.feature === feature);
  return rule?.level ?? 'none';
}

/** Check if a feature is fully unavailable on mobile */
export function isFeatureBlocked(feature: string): boolean {
  return getDegradeLevel(feature) === 'full';
}

/** Check if a feature is degraded (not full) on mobile */
export function isFeatureDegraded(feature: string): boolean {
  return getDegradeLevel(feature) !== 'none';
}

/** Hook: get degradation info for a feature, considering device type */
export function useFeatureDegrade(feature: string) {
  const isMobile = useIsMobile();
  const level = isMobile ? getDegradeLevel(feature) : 'none';
  const rule = MOBILE_DEGRADE_RULES.find((r) => r.feature === feature);

  return {
    isMobile,
    level,
    isBlocked: level === 'full',
    isDegraded: level !== 'none',
    isReadonly: level === 'readonly',
    isSimplified: level === 'simplified',
    labelKey: rule?.labelKey ?? '',
    reasonKey: rule?.reasonKey ?? '',
  };
}