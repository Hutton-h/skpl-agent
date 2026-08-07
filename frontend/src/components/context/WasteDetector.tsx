/**
 * WasteDetector — 浪费检测面板
 *
 * 功能:
 * - 调用 contextApi.getWastePatterns(sessionId) 获取浪费模式
 * - 展示浪费模式列表（pattern_type、severity badge、description、tokens_wasted）
 * - 按 severity 用不同颜色标识
 * - 统计总浪费 Token 数
 */
import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Trash2 } from 'lucide-react';

import { contextApi } from '@/api';
import type { WastePattern } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Skeleton } from '@/components/ui/skeleton';

interface WasteDetectorProps {
  sessionId: string;
}

/** Severity → Badge variant mapping */
const SEVERITY_CONFIG: Record<
  string,
  { variant: 'default' | 'destructive' | 'secondary' | 'outline'; color: string }
> = {
  high: { variant: 'destructive', color: 'text-red-600' },
  medium: { variant: 'default', color: 'text-amber-600' },
  low: { variant: 'secondary', color: 'text-blue-600' },
  info: { variant: 'outline', color: 'text-muted-foreground' },
};

function getSeverityConfig(severity: string) {
  return (
    SEVERITY_CONFIG[severity.toLowerCase()] ?? {
      variant: 'outline' as const,
      color: 'text-muted-foreground',
    }
  );
}

/** Format token count */
function formatTokens(tokens: number | undefined): string {
  if (tokens === undefined || tokens === null) return '0';
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return tokens.toString();
}

export function WasteDetector({ sessionId }: WasteDetectorProps) {
  const { t } = useTranslation();
  const [patterns, setPatterns] = useState<WastePattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatterns = useCallback(async () => {
    try {
      const data = await contextApi.getWastePatterns(sessionId);
      setPatterns(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('context.loadWasteFailed'));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchPatterns();
  }, [fetchPatterns]);

  const totalWasted = patterns.reduce(
    (sum, p) => sum + p.tokens_wasted,
    0,
  );

  // ── Loading State ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Trash2 className="h-4 w-4" />
            {t('context.wasteDetection')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Error State ─────────────────────────────────────────────────────────

  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Trash2 className="h-4 w-4" />
            {t('context.wasteDetection')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-destructive">{error}</p>
        </CardContent>
      </Card>
    );
  }

  // ── Empty State ─────────────────────────────────────────────────────────

  if (patterns.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Trash2 className="h-4 w-4" />
            {t('context.wasteDetection')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <AlertTriangle className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {t('context.noWastePatterns')}
            </p>
            <p className="text-xs text-muted-foreground">
              {t('context.tokenUsageEfficient')}
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Trash2 className="h-4 w-4" />
            {t('context.wasteDetection')}
          </CardTitle>
          <Badge variant="outline" className="gap-1">
            <AlertTriangle className="h-3 w-3" />
            {formatTokens(totalWasted)} {t('context.wastedTokens')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {patterns.map((pattern, idx) => {
              const sev = getSeverityConfig(pattern.severity);
              return (
                <div
                  key={idx}
                  className="rounded-lg border p-3 hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={sev.variant} className="text-xs">
                          {pattern.severity.toUpperCase()}
                        </Badge>
                        <span className="text-sm font-medium truncate">
                          {pattern.pattern_type.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {pattern.description}
                      </p>
                      {pattern.file_path && (
                        <p className="text-xs text-muted-foreground/70 mt-1 font-mono truncate">
                          {pattern.file_path}
                        </p>
                      )}
                    </div>
                    <Badge
                      variant="outline"
                      className={`shrink-0 tabular-nums ${sev.color}`}
                    >
                      {formatTokens(pattern.tokens_wasted)}
                    </Badge>
                  </div>
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default WasteDetector;