/**
 * SessionSummary — 会话摘要面板
 *
 * 功能:
 * - 调用 contextApi.getSessionSummary(sessionId) 获取会话摘要
 * - 展示会话基本信息（session_id、agent_id、created_at）
 * - 展示各子系统摘要卡片（anatomy、bugs、memory、tokens、waste）
 */
import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  BarChart3,
  Brain,
  Bug,
  Code2,
  Database,
  Trash2,
} from 'lucide-react';

import { contextApi } from '@/api';
import type { SessionContextSummary } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

interface SessionSummaryProps {
  sessionId: string;
}

/** Format a date string to a readable format */
function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A';
  try {
    const d = new Date(dateStr);
    return d.toLocaleString();
  } catch {
    return dateStr;
  }
}

/** Format large numbers */
function formatNum(n: number | undefined): string {
  if (n === undefined || n === null) return '0';
  return n.toLocaleString();
}

/** Format token count */
function formatTokens(tokens: number | undefined): string {
  if (tokens === undefined || tokens === null) return '0';
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

export function SessionSummary({ sessionId }: SessionSummaryProps) {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<SessionContextSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await contextApi.getSessionSummary(sessionId);
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : t('context.loadSessionSummaryFailed'),
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  // ── Loading State ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-16 rounded-xl" />
        <div className="grid gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  // ── Error State ─────────────────────────────────────────────────────────

  if (error || !summary) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-4 text-center">
          <p className="text-sm text-destructive">
            {error || t('context.noSessionSummary')}
          </p>
        </CardContent>
      </Card>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Session Info Banner */}
      <Card>
        <CardContent className="py-3">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <div className="flex items-center gap-1.5">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">{t('common.sessions')}:</span>
              <span className="font-mono font-medium">{summary.session_id}</span>
            </div>
            {summary.agent_id && (
              <>
                <Separator orientation="vertical" className="h-4" />
                <div className="flex items-center gap-1.5">
                  <span className="text-muted-foreground">{t('common.agent')}:</span>
                  <span className="font-mono">{summary.agent_id}</span>
                </div>
              </>
            )}
            <Separator orientation="vertical" className="h-4" />
            <div className="flex items-center gap-1.5">
              <span className="text-muted-foreground">{t('common.date')}:</span>
              <span>{formatDate(summary.created_at)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Subsystem Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        {/* Anatomy */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Code2 className="h-3.5 w-3.5" />
              {t('context.anatomy')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.anatomy ? (
              <div className="space-y-1.5">
                <div className="text-2xl font-bold tabular-nums">
                  {formatNum(summary.anatomy.total_symbols)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {t('context.symbolsInFiles', { files: formatNum(summary.anatomy.total_files) })}
                </p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(summary.anatomy.languages ?? {})
                    .slice(0, 3)
                    .map(([lang]) => (
                      <Badge key={lang} variant="secondary" className="text-[10px]">
                        {lang}
                      </Badge>
                    ))}
                  {Object.keys(summary.anatomy.languages ?? {}).length > 3 && (
                    <Badge variant="outline" className="text-[10px]">
                      +{Object.keys(summary.anatomy.languages!).length - 3}
                    </Badge>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('common.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Bugs */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Bug className="h-3.5 w-3.5" />
              {t('dashboard.bugs')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.bugs ? (
              <div className="space-y-1.5">
                <div className="text-2xl font-bold tabular-nums">
                  {formatNum(summary.bugs.total)}
                </div>
                <div className="flex items-center gap-2 text-xs">
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-red-50 text-red-700 border-red-200"
                  >
                    {summary.bugs.open} {t('buglog.open')}
                  </Badge>
                  <Badge
                    variant="outline"
                    className="text-[10px] bg-green-50 text-green-700 border-green-200"
                  >
                    {summary.bugs.resolved} {t('buglog.resolved')}
                  </Badge>
                </div>
                {summary.bugs.duplicate > 0 && (
                  <p className="text-xs text-muted-foreground">
                    {summary.bugs.duplicate} {t('buglog.duplicates')}
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('common.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Memory */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Brain className="h-3.5 w-3.5" />
              {t('context.memory')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.memory ? (
              <div className="space-y-1.5">
                <div className="text-2xl font-bold tabular-nums">
                  {formatNum(summary.memory.total_memories)}
                </div>
                <p className="text-xs text-muted-foreground">{t('context.entries')}</p>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(summary.memory.by_category ?? {})
                    .slice(0, 3)
                    .map(([cat, count]) => (
                      <Badge key={cat} variant="secondary" className="text-[10px]">
                        {cat} ({count})
                      </Badge>
                    ))}
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('common.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Tokens */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Database className="h-3.5 w-3.5" />
              {t('context.tokens')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.tokens ? (
              <div className="space-y-1.5">
                <div className="text-2xl font-bold tabular-nums">
                  {formatTokens(summary.tokens.total_tokens)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {formatNum(summary.tokens.entry_count)} {t('context.entries')}
                </p>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-blue-600 tabular-nums">
                    {t('context.input')}: {formatTokens(summary.tokens.total_input_tokens)}
                  </span>
                  <span className="text-green-600 tabular-nums">
                    {t('context.output')}: {formatTokens(summary.tokens.total_output_tokens)}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('common.noData')}</p>
            )}
          </CardContent>
        </Card>

        {/* Waste */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Trash2 className="h-3.5 w-3.5" />
              {t('context.waste')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {summary.waste ? (
              <div className="space-y-1.5">
                <div className="text-2xl font-bold tabular-nums text-amber-500">
                  {formatTokens(summary.waste.total_waste_tokens)}
                </div>
                <p className="text-xs text-muted-foreground">
                  {((summary.waste.waste_rate ?? 0) * 100).toFixed(1)}% {t('context.wasteRate')}
                </p>
                <Badge variant="outline" className="text-[10px]">
                  {summary.waste.pattern_count} {t('context.patterns')}
                </Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">{t('common.noData')}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Last Scan */}
      {summary.last_scan && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm">
              <BarChart3 className="h-4 w-4" />
              {t('context.lastScan')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              <Badge variant="secondary" className="text-xs">
                {summary.last_scan.mode}
              </Badge>
              <span className="text-muted-foreground">
                {formatNum(summary.last_scan.files_scanned)} files
              </span>
              <span className="text-muted-foreground">
                {formatNum(summary.last_scan.symbols_extracted)} symbols
              </span>
              <span className="text-muted-foreground">
                {(summary.last_scan.duration_seconds ?? 0).toFixed(1)}s
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default SessionSummary;