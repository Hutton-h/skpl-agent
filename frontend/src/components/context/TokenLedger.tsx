/**
 * TokenLedger — 完整 Token 账本面板
 *
 * 功能:
 * - 顶部统计卡片：总 Token、输入、输出、浪费、成本
 * - 模型分布：横向条形图展示 model_breakdown
 * - Provider 分布
 * - 自动刷新（每 5 秒）
 */
import { useCallback, useEffect, useState } from 'react';
import {
  BarChart3,
  Database,
  DollarSign,
  RefreshCw,
  Zap,
} from 'lucide-react';

import { contextApi } from '@/api';
import type { TokenLedgerSummary } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';

interface TokenLedgerProps {
  sessionId: string;
}

/** Format large numbers with locale string */
function formatNum(n: number | undefined): string {
  if (n === undefined || n === null) return '0';
  return n.toLocaleString();
}

/** Format a token count to K/M suffix */
function formatTokens(tokens: number | undefined): string {
  if (tokens === undefined || tokens === null) return '0';
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

/** Format USD cost */
function formatCost(cost: number): string {
  if (cost >= 0.01) return `$${cost.toFixed(4)}`;
  if (cost >= 0.0001) return `$${cost.toFixed(6)}`;
  return `$${cost.toExponential(2)}`;
}

/** Model color palette */
const MODEL_COLORS = [
  'bg-blue-500',
  'bg-green-500',
  'bg-purple-500',
  'bg-orange-500',
  'bg-cyan-500',
  'bg-pink-500',
  'bg-yellow-500',
  'bg-indigo-500',
  'bg-teal-500',
  'bg-red-500',
];

function getModelColor(index: number): string {
  return MODEL_COLORS[index % MODEL_COLORS.length];
}

export function TokenLedger({ sessionId }: TokenLedgerProps) {
  const { t } = useTranslation();
  const [summary, setSummary] = useState<TokenLedgerSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSummary = useCallback(async () => {
    try {
      const data = await contextApi.getTokenSummary(sessionId);
      setSummary(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('context.loadTokenFailed'));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSummary();
    const interval = setInterval(fetchSummary, 5000);
    return () => clearInterval(interval);
  }, [fetchSummary]);

  // ── Loading State ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="grid gap-4 md:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-36 rounded-xl" />
      </div>
    );
  }

  // ── Error State ─────────────────────────────────────────────────────────

  if (error || !summary) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="py-6 text-center">
          <p className="text-sm text-destructive">
            {error || t('context.noTokenData')}
          </p>
        </CardContent>
      </Card>
    );
  }

  // ── Compute derived values ──────────────────────────────────────────────

  const wastePercent = ((summary.waste_rate ?? 0) * 100).toFixed(1);
  const modelEntries = Object.entries(summary.model_breakdown ?? {}).sort(
    (a, b) => b[1] - a[1],
  );
  const providerEntries = Object.entries(summary.provider_breakdown ?? {}).sort(
    (a, b) => b[1] - a[1],
  );
  const maxModelTokens = modelEntries.length > 0 ? modelEntries[0][1] : 1;

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* Auto-refresh indicator */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <RefreshCw className="h-3 w-3" />
        <span>{t('context.autoRefreshing')}</span>
        <span className="ml-auto">{summary.entry_count} {t('context.entries')}</span>
      </div>

      {/* Top Stats Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Database className="h-3.5 w-3.5" />
              {t('context.totalTokens')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatTokens(summary.total_tokens)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatNum(summary.total_tokens)} {t('context.tokensUnit')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Zap className="h-3.5 w-3.5 text-blue-500" />
              {t('context.input')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatTokens(summary.total_input_tokens)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatNum(summary.total_input_tokens)} {t('context.tokensUnit')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Zap className="h-3.5 w-3.5 text-green-500" />
              {t('context.output')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatTokens(summary.total_output_tokens)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {formatNum(summary.total_output_tokens)} {t('context.tokensUnit')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <RefreshCw className="h-3.5 w-3.5 text-amber-500" />
              {t('context.waste')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums text-amber-500">
              {formatTokens(summary.total_waste_tokens)}
            </div>
            <p className="text-xs text-amber-600/80 mt-1">
              {wastePercent}% {t('context.wasteRate')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <DollarSign className="h-3.5 w-3.5 text-emerald-500" />
              {t('dashboard.cost')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold tabular-nums">
              {formatCost(summary.total_cost_usd)}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {t('context.estimatedCost')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Model Breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <BarChart3 className="h-4 w-4" />
            {t('context.modelDistribution')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {modelEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t('context.noModelData')}
            </p>
          ) : (
            <ScrollArea className="max-h-64">
              <div className="space-y-3">
                {modelEntries.map(([model, tokens], idx) => {
                  const pct = summary.total_tokens > 0
                    ? ((tokens / summary.total_tokens) * 100).toFixed(1)
                    : '0.0';
                  const barWidth = maxModelTokens > 0
                    ? (tokens / maxModelTokens) * 100
                    : 0;
                  return (
                    <div key={model} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium truncate max-w-[60%]">
                          {model}
                        </span>
                        <span className="text-muted-foreground tabular-nums">
                          {formatTokens(tokens)} ({pct}%)
                        </span>
                      </div>
                      <Progress
                        value={barWidth}
                        className="h-2.5 [&>div]:bg-blue-500"
                        /* Override the progress fill color via inline style */
                        style={
                          {
                            '--progress-bg': getModelColor(idx).replace('bg-', ''),
                          } as React.CSSProperties
                        }
                      />
                    </div>
                  );
                })}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Provider Breakdown */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Database className="h-4 w-4" />
            {t('context.providerDistribution')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {providerEntries.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t('context.noProviderData')}
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {providerEntries.map(([provider, tokens]) => {
                const pct = summary.total_tokens > 0
                  ? ((tokens / summary.total_tokens) * 100).toFixed(1)
                  : '0.0';
                return (
                  <Badge
                    key={provider}
                    variant="secondary"
                    className="text-sm px-3 py-1.5 gap-1.5"
                  >
                    <span className="font-medium">{provider}</span>
                    <Separator orientation="vertical" className="h-3" />
                    <span className="tabular-nums">
                      {formatTokens(tokens)} ({pct}%)
                    </span>
                  </Badge>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default TokenLedger;