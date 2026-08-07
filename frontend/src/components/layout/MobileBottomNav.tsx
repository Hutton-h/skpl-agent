// ── SKPL: MobileBottomNav — bottom tab bar for mobile devices ────────────────
import { useLocation, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  Calendar,
  Settings,
  Monitor,
  Code,
  Globe,
  Bug,
  Flame,
  Bell,
  Key,
  Users,
  FolderTree,
  Menu,
  Shield,
} from 'lucide-react';
import { useIsMobile } from '@/hooks/use-mobile';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

interface NavItem {
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  labelKey: string;
  feature: string;
}

const MOBILE_TABS: NavItem[] = [
  { path: '/dashboard', icon: LayoutDashboard, labelKey: 'nav.dashboard', feature: 'dashboard' },
  { path: '/chat', icon: MessageSquare, labelKey: 'nav.chat', feature: 'chat' },
  { path: '/knowledge', icon: BookOpen, labelKey: 'nav.knowledge', feature: 'knowledge' },
  { path: '/schedule', icon: Calendar, labelKey: 'nav.schedule', feature: 'schedule' },
  { path: '/more', icon: Menu, labelKey: 'nav.more', feature: 'more' },
];

const MORE_ITEMS: NavItem[] = [
  { path: '/desktop', icon: Monitor, labelKey: 'nav.desktop', feature: 'desktop' },
  { path: '/code-generation', icon: Code, labelKey: 'nav.codeGeneration', feature: 'code-generation' },
  { path: '/web-intelligence', icon: Globe, labelKey: 'nav.webIntelligence', feature: 'web-intelligence' },
  { path: '/firecrawl', icon: Flame, labelKey: 'nav.firecrawl', feature: 'firecrawl' },
  { path: '/context', icon: FolderTree, labelKey: 'nav.context', feature: 'context' },
  { path: '/buglog', icon: Bug, labelKey: 'nav.buglog', feature: 'buglog' },
  { path: '/updates', icon: Bell, labelKey: 'nav.updates', feature: 'updates' },
  { path: '/credential', icon: Key, labelKey: 'nav.credential', feature: 'credential' },
  { path: '/team', icon: Users, labelKey: 'nav.team', feature: 'team' },
  { path: '/setup', icon: Settings, labelKey: 'nav.setup', feature: 'setup' },
  { path: '/admin', icon: Shield, labelKey: 'nav.admin', feature: 'admin' },
];

export function MobileBottomNav() {
  const isMobile = useIsMobile();
  const location = useLocation();
  const navigate = useNavigate();
  const { t } = useTranslation();

  if (!isMobile) return null;

  const currentPath = location.pathname;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="flex h-14 items-center justify-around px-1 safe-area-bottom">
        {MOBILE_TABS.map((tab) => {
          const isActive =
            tab.path === '/more'
              ? MORE_ITEMS.some((item) => currentPath.startsWith(item.path))
              : currentPath === tab.path || (tab.path !== '/dashboard' && currentPath.startsWith(tab.path));

          const isBlocked = tab.feature !== 'more' && tab.feature !== 'chat'
            ? false // handled by MobileGuard on page level
            : false;

          return (
            <button
              key={tab.path}
              onClick={() => navigate(tab.path)}
              className={cn(
                'flex flex-col items-center justify-center gap-0.5 px-2 py-1 min-w-0',
                'text-muted-foreground transition-colors',
                isActive && 'text-primary',
                isBlocked && 'opacity-30'
              )}
            >
              <tab.icon className={cn('h-5 w-5', isActive && 'text-primary')} />
              <span className="text-[10px] leading-tight truncate max-w-[56px]">
                {t(tab.labelKey)}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}

/** Returns true if the current route is a "more" page */
export function isMorePage(pathname: string): boolean {
  return MORE_ITEMS.some((item) => pathname.startsWith(item.path));
}