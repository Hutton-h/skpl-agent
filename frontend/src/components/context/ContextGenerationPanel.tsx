/**
 * ContextGenerationPanel — 上下文生成面板
 *
 * 允许用户选择上下文类型并生成上下文字符串。
 */
import {
  Brain,
  Bug,
  Code2,
  Copy,
  Eye,
  Loader2,
} from 'lucide-react';
import { useState } from 'react';

import { contextApi } from '@/api';
import type { ContextGenerationResponse } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';

interface ContextGenerationPanelProps {
  sessionId: string;
}

export function ContextGenerationPanel({ sessionId }: ContextGenerationPanelProps) {
  const { t } = useTranslation();
  const [options, setOptions] = useState({
    include_anatomy: true,
    include_bugs: true,
    include_memory: true,
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ContextGenerationResponse | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await contextApi.generateContext(sessionId, options);
      setResult(res);
    } catch {
      // Error toast is already handled by client.ts request()
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = () => {
    if (result?.context) {
      navigator.clipboard.writeText(result.context);
      toast.success(t('context.contextCopied'));
    }
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" />
            {t('context.generateContext')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Options */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">{t('context.includeSections')}</Label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox
                    checked={options.include_anatomy}
                    onCheckedChange={(v) =>
                      setOptions((o) => ({ ...o, include_anatomy: !!v }))
                    }
                  />
                  <Code2 className="h-3.5 w-3.5" /> {t('context.anatomy')}
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox
                    checked={options.include_bugs}
                    onCheckedChange={(v) =>
                      setOptions((o) => ({ ...o, include_bugs: !!v }))
                    }
                  />
                  <Bug className="h-3.5 w-3.5" /> {t('dashboard.bugs')}
                </label>
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <Checkbox
                    checked={options.include_memory}
                    onCheckedChange={(v) =>
                      setOptions((o) => ({ ...o, include_memory: !!v }))
                    }
                  />
                  <Brain className="h-3.5 w-3.5" /> {t('context.memory')}
                </label>
              </div>
            </div>

            <Button onClick={handleGenerate} disabled={loading} className="w-full">
              {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              {loading ? t('context.generating') : t('context.generateContext')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Result */}
      {result && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Eye className="h-4 w-4" />
              {t('context.generatedContext')}
              <span className="text-xs text-muted-foreground font-normal">
                ~{result.estimated_tokens.toLocaleString()} {t('context.tokens')}
              </span>
            </CardTitle>
            <Button variant="ghost" size="sm" onClick={handleCopy}>
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </CardHeader>
          <CardContent>
            <Textarea
              value={result.context}
              readOnly
              className="font-mono text-xs min-h-[200px] max-h-[400px] resize-y"
              placeholder={t('context.noContextGenerated')}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default ContextGenerationPanel;