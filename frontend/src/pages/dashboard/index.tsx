/**
 * SKPL Dashboard — 系统概览页面
 *
 * 展示:
 * - 活跃会话概览
 * - Token 使用统计
 * - Bug 趋势
 * - 项目解剖状态
 */
import {
  Activity,
  AlertTriangle,
  Brain,
  Bug,
  Code2,
  Coins,
  ScanEye,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { contextApi } from '@/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { useTranslation } from '@/i18n/useI18n';

interface DashboardData {
  totalSessions: number;
  totalTokens: number;
  totalCost: number;
  totalBugs: number;
  openBugs: number;
  totalSymbols: number;
  totalFiles: number;
  wasteRate: number;
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  loading,
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ComponentType<{ className?: string }>;
  loading?: boolean;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-8 w-20" />
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
}

export function DashboardPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<DashboardData>({
    totalSessions: 0,
    totalTokens: 0,
    totalCost: 0,
    totalBugs: 0,
    openBugs: 0,
    totalSymbols: 0,
    totalFiles: 0,
    wasteRate: 0,
  });

  useEffect(() => {
    async function load() {
      try {
        const activeSessionId = localStorage.getItem('active_session_id');
        if (!activeSessionId) {
          setLoading(false);
          return;
        }
        // Dashboard aggregates data from multiple sources
        const results = await Promise.allSettled([
          contextApi.getSessionSummary(activeSessionId).catch(() => null),
        ]);

        const summary = results[0].status === 'fulfilled' ? results[0].value : null;

        if (summary) {
          setData({
            totalSessions: 1,
            totalTokens: summary.tokens?.total_tokens ?? 0,
            totalCost: summary.tokens?.total_cost_usd ?? 0,
            totalBugs: summary.bugs?.total ?? 0,
            openBugs: summary.bugs?.open ?? 0,
            totalSymbols: summary.anatomy?.total_symbols ?? 0,
            totalFiles: summary.anatomy?.total_files ?? 0,
            wasteRate: summary.tokens?.waste_rate ?? 0,
          });
        }
      } catch {
        // Dashboard stays empty when no data available
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const formatTokens = (n: number) => {
    if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
    return String(n);
  };

  const formatCost = (n: number) => `$${n.toFixed(4)}`;

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('dashboard.title')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('dashboard.subtitle')}
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title={t('common.sessions') ?? 'Sessions'}
          value={data.totalSessions}
          icon={Activity}
          loading={loading}
        />
        <StatCard
          title={t('dashboard.totalTokens') ?? 'Total Tokens'}
          value={formatTokens(data.totalTokens)}
          subtitle={`${t('dashboard.cost')}: ${formatCost(data.totalCost)}`}
          icon={Coins}
          loading={loading}
        />
        <StatCard
          title={t('dashboard.bugs') ?? 'Bugs'}
          value={data.totalBugs}
          subtitle={`${data.openBugs}${t('dashboard.openBugs')}`}
          icon={Bug}
          loading={loading}
        />
        <StatCard
          title={t('dashboard.wasteRate') ?? 'Waste Rate'}
          value={`${(data.wasteRate * 100).toFixed(1)}%`}
          icon={AlertTriangle}
          loading={loading}
        />
      </div>

      {/* Project Anatomy */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Code2 className="h-4 w-4" />
              {t('dashboard.projectAnatomy')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      {t('dashboard.totalSymbols') ?? 'Total Symbols'}
                    </span>
                    <span className="text-sm font-medium">
                      {data.totalSymbols.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      {t('dashboard.filesScanned') ?? 'Files Scanned'}
                    </span>
                    <span className="text-sm font-medium">
                      {data.totalFiles.toLocaleString()}
                    </span>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Zap className="h-4 w-4" />
                {t('dashboard.quickActions') ?? 'Quick Actions'}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-2">
                <a
                  href="/context"
                  className="flex items-center gap-2 rounded-lg border p-3 text-sm hover:bg-accent transition-colors"
                >
                  <ScanEye className="h-4 w-4" />
                  {t('dashboard.scanProject') ?? 'Scan Project'}
                </a>
                <a
                  href="/buglog"
                  className="flex items-center gap-2 rounded-lg border p-3 text-sm hover:bg-accent transition-colors"
                >
                  <Bug className="h-4 w-4" />
                  {t('dashboard.viewBugs') ?? 'View Bugs'}
                </a>
                <a
                  href="/context"
                  className="flex items-center gap-2 rounded-lg border p-3 text-sm hover:bg-accent transition-colors"
                >
                  <Brain className="h-4 w-4" />
                  {t('dashboard.memory') ?? 'Memory'}
                </a>
                <a
                  href="/firecrawl"
                  className="flex items-center gap-2 rounded-lg border p-3 text-sm hover:bg-accent transition-colors"
                >
                  <Activity className="h-4 w-4" />
                  {t('dashboard.firecrawl') ?? 'Firecrawl'}
                </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default DashboardPage;