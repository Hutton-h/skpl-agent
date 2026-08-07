import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import { contextApi } from '@/api';
import { useTranslation } from '@/i18n/useI18n';

interface TokenUsageEntry {
  category: string;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  isWaste: boolean;
  wasteReason?: string;
}

interface TokenUsageProps {
  sessionId: string;
  maxTokens?: number;
}

export function TokenUsage({ sessionId, maxTokens = 32000 }: TokenUsageProps) {
  const { t } = useTranslation();
  const [entries, setEntries] = useState<TokenUsageEntry[]>([]);
  const [totalTokens, setTotalTokens] = useState(0);
  const [wasteTokens, setWasteTokens] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const fetchTokenUsage = async () => {
      try {
        setLoading(true);
        const summary = await contextApi.getTokenSummary(sessionId) as unknown as Record<string, unknown>;
        if (mounted) {
          setTotalTokens((summary.total_tokens as number) || 0);
          setWasteTokens((summary.total_waste_tokens as number) || 0);
          // Build entries from model_breakdown: Record<string, number> (model → total tokens)
          const breakdown = (summary.model_breakdown as Record<string, number>) || {};
          const built: TokenUsageEntry[] = [];
          for (const [model, total] of Object.entries(breakdown)) {
            built.push({
              category: model,
              inputTokens: 0, // model_breakdown is aggregated total only
              outputTokens: 0,
              totalTokens: total,
              isWaste: false,
            });
          }
          setEntries(built);
        }
      } catch {
        // Silently ignore — context may not be initialized yet
        if (mounted) {
          setEntries([]);
          setTotalTokens(0);
          setWasteTokens(0);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchTokenUsage();
    const interval = setInterval(fetchTokenUsage, 5000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  const usagePercent = maxTokens > 0 ? Math.min(100, (totalTokens / maxTokens) * 100) : 0;
  const wastePercent = totalTokens > 0 ? (wasteTokens / totalTokens) * 100 : 0;

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      system_prompt: 'bg-blue-500',
      user_message: 'bg-green-500',
      assistant_message: 'bg-purple-500',
      tool_call: 'bg-yellow-500',
      tool_result: 'bg-orange-500',
      context_injection: 'bg-cyan-500',
      memory: 'bg-pink-500',
      rag_result: 'bg-indigo-500',
    };
    return colors[category] || 'bg-gray-500';
  };

  const formatTokens = (tokens: number) => {
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
    return tokens.toString();
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{t('context.tokenUsage')}</CardTitle>
          <Badge variant={usagePercent > 80 ? 'destructive' : 'secondary'}>
            {formatTokens(totalTokens)} / {formatTokens(maxTokens)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>{t('context.used')}: {usagePercent.toFixed(1)}%</span>
            <span>{t('context.waste')}: {wastePercent.toFixed(1)}%</span>
          </div>
          <Progress value={usagePercent} className="h-2" />
          {wasteTokens > 0 && (
            <div className="flex items-center gap-2 text-xs text-amber-500">
              <span className="inline-block w-2 h-2 rounded-full bg-amber-500" />
              {formatTokens(wasteTokens)} {t('context.tokensWasted')}
            </div>
          )}
        </div>

        {loading ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            {t('context.loadingTokenData')}
          </div>
        ) : (
          <>
            <Separator className="my-3" />
            {/* Category breakdown */}
            <ScrollArea className="h-32">
              <div className="space-y-1.5">
                {entries.map((entry, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span
                        className={`inline-block w-2 h-2 rounded-full ${getCategoryColor(entry.category)}`}
                      />
                      <span className="capitalize">
                        {entry.category.replace(/_/g, ' ')}
                      </span>
                      {entry.isWaste && (
                        <Badge variant="outline" className="text-[10px] h-4 px-1 text-amber-500 border-amber-500/30">
                          {t('context.waste')}
                        </Badge>
                      )}
                    </div>
                    <span className="text-muted-foreground tabular-nums">
                      {formatTokens(entry.totalTokens)}
                    </span>
                  </div>
                ))}
                {entries.length === 0 && (
                  <div className="text-xs text-muted-foreground text-center py-2">
                    {t('context.noTokenUsageData')}
                  </div>
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default TokenUsage;