/**
 * AnatomyStatsPanel — 项目解剖统计面板
 *
 * 显示项目解剖的核心统计信息和语言分布。
 */
import { Code2, Database, FileCode, Hash, Layers } from 'lucide-react';

import type { AnatomyStats } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';

interface AnatomyStatsPanelProps {
  stats: AnatomyStats | null;
  loading?: boolean;
}

export function AnatomyStatsPanel({ stats, loading }: AnatomyStatsPanelProps) {
  const { t } = useTranslation();
  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
      </div>
    );
  }

  if (!stats) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-8">
          <Code2 className="h-6 w-6 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">{t('context.noAnatomyData')}</p>
        </CardContent>
      </Card>
    );
  }

  const total = stats.total_symbols || 1;
  const maxLang = Math.max(...Object.values(stats.languages ?? {}), 1);

  return (
    <div className="space-y-4">
      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Symbols
            </CardTitle>
            <Hash className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_symbols.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Files
            </CardTitle>
            <FileCode className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.total_files.toLocaleString()}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Languages
            </CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Object.keys(stats.languages ?? {}).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Language Breakdown */}
      {Object.keys(stats.languages ?? {}).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Database className="h-4 w-4" />
              Language Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(stats.languages ?? {})
                .sort(([, a], [, b]) => b - a)
                .slice(0, 10)
                .map(([lang, count]) => (
                  <div key={lang} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{lang}</span>
                      <span className="text-muted-foreground">
                        {count.toLocaleString()} ({((count / total) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <Progress value={(count / maxLang) * 100} className="h-1.5" />
                  </div>
                ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default AnatomyStatsPanel;