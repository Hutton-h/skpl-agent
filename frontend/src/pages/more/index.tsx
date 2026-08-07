// ── SKPL: MorePage — grid of additional navigation items ──────────────────
import { useNavigate } from "react-router-dom";
import {
  Monitor,
  Code,
  Globe,
  Flame,
  Bug,
  Bell,
  Key,
  FolderTree,
  Settings,
  Shield,
} from "lucide-react";
import { useTranslation } from "@/i18n/useI18n";
import { cn } from "@/lib/utils";

interface MoreItem {
  path: string;
  icon: React.ComponentType<{ className?: string }>;
  labelKey: string;
  adminOnly?: boolean;
}

const MORE_ITEMS: MoreItem[] = [
  { path: "/desktop", icon: Monitor, labelKey: "nav.desktop" },
  { path: "/code-generation", icon: Code, labelKey: "nav.codeGeneration" },
  { path: "/web-intelligence", icon: Globe, labelKey: "nav.webIntelligence" },
  { path: "/firecrawl", icon: Flame, labelKey: "nav.firecrawl" },
  { path: "/context", icon: FolderTree, labelKey: "nav.context" },
  { path: "/buglog", icon: Bug, labelKey: "nav.buglog" },
  { path: "/updates", icon: Bell, labelKey: "nav.updates" },
  { path: "/credential", icon: Key, labelKey: "nav.credential" },
  { path: "/setup", icon: Settings, labelKey: "nav.setup" },
  { path: "/admin", icon: Shield, labelKey: "nav.admin", adminOnly: true },
];

export function MorePage() {
  const navigate = useNavigate();
  const { t } = useTranslation();

  const isAdmin = localStorage.getItem('user_role') === 'admin';

  const visibleItems = MORE_ITEMS.filter(
    (item) => !item.adminOnly || isAdmin
  );

  return (
    <div className="flex flex-col h-full overflow-auto">
      <div className="p-4 md:p-6">
        <h1 className="text-2xl font-bold mb-1">{t("nav.more")}</h1>
        <p className="text-sm text-muted-foreground mb-6">
          更多高级功能与工具
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {visibleItems.map((item) => (
            <button
              key={item.path}
              onClick={() => navigate(item.path)}
              className={cn(
                "flex flex-col items-center justify-center gap-2 p-4 rounded-lg",
                "border border-border bg-card hover:bg-accent hover:text-accent-foreground",
                "transition-colors cursor-pointer text-center"
              )}
            >
              <item.icon className="h-8 w-8 text-primary" />
              <span className="text-sm font-medium">{t(item.labelKey)}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}