/**
 * TokenEstimate — Token 估算器
 *
 * 输入文本后实时估算 token 数量，支持多模型对比。
 * 无外部依赖，独立组件。
 */
import { Calculator, Hash, BarChart3, Text } from 'lucide-react';
import { useState, useMemo, useCallback } from 'react';

import { useTranslation } from '@/i18n/useI18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Textarea } from '@/components/ui/textarea';

/** 模型估算配置 */
interface ModelEstimate {
  name: string;
  charsPerToken: number;
  description: string;
}

const MODELS: ModelEstimate[] = [
  {
    name: 'Simple (chars/4)',
    charsPerToken: 4,
    description: '通用简算法：1 token = 4 字符',
  },
  {
    name: 'GPT-4o',
    charsPerToken: 3.75,
    description: 'OpenAI GPT-4o: 1 token ~ 3.75 字符',
  },
  {
    name: 'Claude',
    charsPerToken: 3.5,
    description: 'Anthropic Claude: 1 token ~ 3.5 字符',
  },
];

/** 估算 token 数量 */
function estimateTokens(text: string, charsPerToken: number): number {
  if (!text.trim()) return 0;
  return Math.max(1, Math.round(text.length / charsPerToken));
}

/** 格式化数字 */
function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function TokenEstimate() {
  const { t } = useTranslation();
  const [text, setText] = useState('');

  const charCount = text.length;

  const estimates = useMemo(() => {
    return MODELS.map((model) => ({
      ...model,
      tokens: estimateTokens(text, model.charsPerToken),
    }));
  }, [text]);

  const handleTextChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setText(e.target.value);
    },
    [],
  );

  const maxTokens = estimates.length > 0 ? Math.max(...estimates.map((e) => e.tokens)) : 0;
  const minTokens = estimates.length > 0 ? Math.min(...estimates.map((e) => e.tokens)) : 0;

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Calculator className="h-4 w-4" />
          Token Estimator
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Input */}
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <Text className="h-3 w-3" />
            Paste or type text to estimate tokens
          </label>
          <Textarea
            placeholder={t('context.estimatePlaceholder')}
            value={text}
            onChange={handleTextChange}
            className="min-h-[120px] font-mono text-sm resize-y"
          />
        </div>

        <Separator />

        {/* Character count */}
        <div className="flex items-center justify-between">
          <span className="text-xs text-muted-foreground flex items-center gap-1.5">
            <Hash className="h-3.5 w-3.5" />
            Character count
          </span>
          <Badge variant="secondary" className="text-xs tabular-nums">
            {formatNumber(charCount)} chars
          </Badge>
        </div>

        <Separator />

        {/* Model comparison */}
        <div className="space-y-1.5">
          <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" />
            Model comparison
          </span>
          <div className="space-y-2">
            {estimates.map((model) => {
              const isMax = model.tokens === maxTokens && maxTokens > 0;
              const isMin = model.tokens === minTokens && minTokens > 0 && maxTokens !== minTokens;

              const barWidth =
                maxTokens > 0
                  ? Math.max(4, (model.tokens / maxTokens) * 100)
                  : 0;

              return (
                <div key={model.name} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium">{model.name}</span>
                      {isMax && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-4 px-1 border-amber-500/30 text-amber-600"
                        >
                          max
                        </Badge>
                      )}
                      {isMin && (
                        <Badge
                          variant="outline"
                          className="text-[10px] h-4 px-1 border-blue-500/30 text-blue-600"
                        >
                          min
                        </Badge>
                      )}
                    </div>
                    <Badge variant="secondary" className="text-xs tabular-nums">
                      {formatNumber(model.tokens)} tokens
                    </Badge>
                  </div>
                  {/* Progress bar */}
                  <div className="w-full h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary transition-all duration-200"
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                  <p className="text-[10px] text-muted-foreground/60 pl-0.5">
                    {model.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Empty state */}
        {!text.trim() && (
          <div className="flex flex-col items-center gap-2 py-4 text-muted-foreground">
            <Calculator className="h-6 w-6" />
            <p className="text-xs">{t('context.estimateHint')}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default TokenEstimate;