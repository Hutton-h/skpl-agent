/**
 * Code Generation Page — 代码生成与执行页面
 *
 * 功能:
 * - 迭代式代码生成任务执行
 * - Python/Bash 直接运行
 * - 查看执行历史和结果
 * - 步骤执行记录查看
 */
import {
  Code,
  Terminal,
  Play,
  FileCode,
  ScrollText,
  Loader2,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  RotateCw,
  AlertTriangle,
} from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ApiError } from '@/api/client';
import { useTranslation } from '@/i18n/useI18n';
import {
  codeGenerationApi,
  type ExecuteCodeRequest,
  type ExecuteCodeResponse,
  type CodeResultListItem,
  type RunCodeRequest,
  type RunCodeResponse,
} from '@/api/codeGeneration';

export function CodeGenerationPage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('codeGeneration.title')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('codeGeneration.subtitle')}
        </p>
      </div>

      <Tabs defaultValue="execute">
        <TabsList>
          <TabsTrigger value="execute">
            <Code className="mr-1 h-4 w-4" /> {t('codeGeneration.tabTask')}
          </TabsTrigger>
          <TabsTrigger value="direct-run">
            <Terminal className="mr-1 h-4 w-4" /> {t('codeGeneration.tabDirectRun')}
          </TabsTrigger>
          <TabsTrigger value="history">
            <ScrollText className="mr-1 h-4 w-4" /> {t('codeGeneration.tabHistory')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="execute" className="mt-4">
          <ExecutePanel />
        </TabsContent>

        <TabsContent value="direct-run" className="mt-4">
          <DirectRunPanel />
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <HistoryPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Status Badge                                                        */
/* ------------------------------------------------------------------ */
function StatusBadge({ completionReason }: { completionReason: string }) {
  const { t } = useTranslation();
  const isSuccess = completionReason === 'DONE';
  const isFail = completionReason === 'FAIL';

  const statusLabel = isSuccess
    ? t('codeGeneration.statusSuccess')
    : isFail
      ? t('codeGeneration.statusFail')
      : completionReason;

  return (
    <Badge
      variant={isSuccess ? 'outline' : isFail ? 'destructive' : 'secondary'}
      className="gap-1"
    >
      {isSuccess ? (
        <CheckCircle2 className="h-3 w-3" />
      ) : isFail ? (
        <XCircle className="h-3 w-3" />
      ) : (
        <Clock className="h-3 w-3" />
      )}
      {statusLabel}
    </Badge>
  );
}

/* ------------------------------------------------------------------ */
/*  Execute Panel                                                       */
/* ------------------------------------------------------------------ */
function ExecutePanel() {
  const { t } = useTranslation();
  const [task, setTask] = useState('');
  const [context, setContext] = useState('');
  const [budget, setBudget] = useState(10);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ExecuteCodeResponse | null>(null);
  const [error, setError] = useState('');

  const handleExecute = useCallback(async () => {
    if (!task.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const req: ExecuteCodeRequest = {
        task: task.trim(),
        context: context.trim() || undefined,
        budget: budget > 0 ? budget : undefined,
      };
      const res = await codeGenerationApi.execute(req);
      setResult(res);
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('codeGeneration.error'));
    } finally {
      setLoading(false);
    }
  }, [task, context, budget, t]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Code className="h-4 w-4" /> {t('codeGeneration.executeCodeTask')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>{t('codeGeneration.taskInstruction')}</Label>
            <Textarea
              placeholder={t('codeGeneration.promptPlaceholder')}
              value={task}
              onChange={(e) => setTask(e.target.value)}
              rows={4}
            />
          </div>
          <div className="space-y-2">
            <Label>{t('codeGeneration.contextOptional')}</Label>
            <Textarea
              placeholder={t('codeGeneration.contextPlaceholder')}
              value={context}
              onChange={(e) => setContext(e.target.value)}
              rows={3}
            />
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Label className="whitespace-nowrap">{t('codeGeneration.budgetSteps')}</Label>
              <Input
                type="number"
                min={1}
                max={50}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-16"
              />
            </div>
            <div className="flex-1" />
            <Button onClick={handleExecute} disabled={loading}>
              {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Play className="mr-1 h-4 w-4" />}
              {t('codeGeneration.execute')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {result && (
        <ResultDetail result={result} />
      )}

      {!loading && !result && !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <FileCode className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('codeGeneration.describeTask')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Result Detail                                                       */
/* ------------------------------------------------------------------ */
function ResultDetail({ result }: { result: ExecuteCodeResponse }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>{t('codeGeneration.executionResult')}</span>
          <StatusBadge completionReason={result.completion_reason} />
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Summary */}
        {result.summary && (
          <div>
            <Label className="text-sm text-muted-foreground">{t('codeGeneration.summary')}</Label>
            <p className="text-sm mt-1 whitespace-pre-wrap">{result.summary}</p>
          </div>
        )}

        {/* Metadata */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-muted-foreground">{t('codeGeneration.steps')}</span>
            <p className="font-medium">{result.steps_executed} / {result.budget}</p>
          </div>
          <div>
            <span className="text-muted-foreground">{t('codeGeneration.duration')}</span>
            <p className="font-medium">{result.duration_seconds.toFixed(2)}s</p>
          </div>
          <div>
            <span className="text-muted-foreground">{t('codeGeneration.taskId')}</span>
            <p className="font-medium font-mono text-xs">{result.task_id}</p>
          </div>
        </div>

        {/* Execution History */}
        {result.execution_history.length > 0 && (
          <div>
            <Label className="text-sm text-muted-foreground">
              {t('codeGeneration.executionHistory')} ({result.execution_history.length} {t('codeGeneration.steps')})
            </Label>
            <div className="mt-2 space-y-2">
              {result.execution_history.map((step, idx) => {
                const isOpen = expanded === idx;
                return (
                  <Card key={idx} className="bg-muted/50">
                    <div
                      className="flex items-center gap-2 p-3 cursor-pointer"
                      onClick={() => setExpanded(isOpen ? null : idx)}
                    >
                      {isOpen ? <ChevronRight className="h-4 w-4 rotate-90 transition-transform" /> : <ChevronRight className="h-4 w-4 transition-transform" />}
                      <span className="text-xs font-medium">{t('codeGeneration.step', { n: idx + 1 })}</span>
                      {'status' in (step.result as any) && (
                        <div className="ml-auto">
                          <Badge variant={(step.result as any).status === 'success' ? 'outline' : 'destructive'} className="text-xs">
                            {(step.result as any).status === 'success'
                              ? t('codeGeneration.statusSuccess')
                              : (step.result as any).status === 'failed'
                                ? t('codeGeneration.statusFail')
                                : (step.result as any).status}
                          </Badge>
                        </div>
                      )}
                    </div>
                    {isOpen && (
                      <CardContent className="pt-0 border-t mt-0">
                        {'thoughts' in step && !!step.thoughts && (
                          <div className="mb-2">
                            <span className="text-xs text-muted-foreground">{t('codeGeneration.thoughts')}</span>
                            <p className="text-sm whitespace-pre-wrap mt-1">{String(step.thoughts)}</p>
                          </div>
                        )}
                        {'action' in step && !!step.action && (
                          <div className="mb-2">
                            <span className="text-xs text-muted-foreground">{t('codeGeneration.action')}</span>
                            <pre className="text-xs bg-background p-2 rounded mt-1 overflow-x-auto">
                              {String(step.action)}
                            </pre>
                          </div>
                        )}
                        {'result' in step && !!step.result && (
                          <div>
                            <span className="text-xs text-muted-foreground">{t('codeGeneration.result')}</span>
                            {(step.result as any).output && (
                              <pre className="text-xs bg-background p-2 rounded mt-1 overflow-x-auto">
                                {String((step.result as any).output)}
                              </pre>
                            )}
                            {(step.result as any).error && (
                              <pre className="text-xs bg-destructive/10 p-2 rounded mt-1 overflow-x-auto text-destructive">
                                {String((step.result as any).error)}
                              </pre>
                            )}
                          </div>
                        )}
                      </CardContent>
                    )}
                  </Card>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Direct Run Panel                                                   */
/* ------------------------------------------------------------------ */
function DirectRunPanel() {
  const { t } = useTranslation();
  const [code, setCode] = useState('');
  const [language, setLanguage] = useState<'python' | 'bash'>('python');
  const [timeout, setTimeout] = useState(30);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RunCodeResponse | null>(null);
  const [error, setError] = useState('');

  const handleRun = useCallback(async () => {
    if (!code.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const req: RunCodeRequest = { code: code.trim(), timeout };
      const res = language === 'python'
        ? await codeGenerationApi.runPython(req)
        : await codeGenerationApi.runBash(req);
      setResult(res);
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('codeGeneration.error'));
    } finally {
      setLoading(false);
    }
  }, [code, language, timeout, t]);

  const examples: Record<string, string> = {
    python: `import sys

print("Hello from Python!")
print(f"Python version: {sys.version}")`,
    bash: `echo "Hello from Bash!" && whoami`,
  };

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Terminal className="h-4 w-4" /> {t('codeGeneration.directCodeExecution')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-2">
            <Button
              variant={language === 'python' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setLanguage('python');
                setCode(examples.python);
              }}
            >
              {t('codeGeneration.python')}
            </Button>
            <Button
              variant={language === 'bash' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setLanguage('bash');
                setCode(examples.bash);
              }}
            >
              {t('codeGeneration.bash')}
            </Button>
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <Label className="text-sm whitespace-nowrap">{t('codeGeneration.timeoutSeconds')}</Label>
              <Input
                type="number"
                min={1}
                max={120}
                value={timeout}
                onChange={(e) => setTimeout(Number(e.target.value))}
                className="w-16"
              />
            </div>
          </div>

          <Textarea
            placeholder={t('codeGeneration.enterCode', { language })}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            rows={8}
            className="font-mono text-sm"
          />

          <div className="flex justify-end">
            <Button onClick={handleRun} disabled={loading}>
              {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Play className="mr-1 h-4 w-4" />}
              {t('codeGeneration.runCode')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>{t('codeGeneration.output')}</span>
              <Badge variant={result.status === 'success' ? 'outline' : 'destructive'}>
                {result.status}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {result.output && (
              <div>
                <Label className="text-xs text-muted-foreground">{t('codeGeneration.stdout')}</Label>
                <ScrollArea className="max-h-64">
                  <pre className="text-xs bg-muted p-3 rounded overflow-x-auto mt-1">
                    {result.output}
                  </pre>
                </ScrollArea>
              </div>
            )}
            {result.error && (
              <div>
                <Label className="text-xs text-muted-foreground">{t('codeGeneration.stderr')}</Label>
                <ScrollArea className="max-h-64">
                  <pre className="text-xs bg-destructive/10 text-destructive p-3 rounded overflow-x-auto mt-1">
                    {result.error}
                  </pre>
                </ScrollArea>
              </div>
            )}
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">{t('codeGeneration.exitCode')}</span>
                <p className="font-medium">{result.return_code}</p>
              </div>
              <div>
                <span className="text-muted-foreground">{t('codeGeneration.duration')}</span>
                <p className="font-medium">{result.duration_seconds.toFixed(2)}s</p>
              </div>
              <div>
                <span className="text-muted-foreground">{t('codeGeneration.executionId')}</span>
                <p className="font-medium font-mono text-xs">{result.execution_id}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {!loading && !result && !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <Terminal className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('codeGeneration.enterCodeToRun')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  History Panel                                                       */
/* ------------------------------------------------------------------ */
function HistoryPanel() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [results, setResults] = useState<CodeResultListItem[]>([]);
  const [selectedResult, setSelectedResult] = useState<ExecuteCodeResponse | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);

  const loadResults = useCallback(async () => {
    setLoading(true);
    try {
      const res = await codeGenerationApi.listResults();
      setResults(res);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  const handleSelectResult = useCallback(async (taskId: string) => {
    setSelectedLoading(true);
    try {
      const res = await codeGenerationApi.getResult(taskId);
      setSelectedResult(res as unknown as ExecuteCodeResponse);
    } catch {
      setSelectedResult(null);
    } finally {
      setSelectedLoading(false);
    }
  }, []);

  const handleRefresh = useCallback(() => {
    loadResults();
    setSelectedResult(null);
  }, [loadResults]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-[300px_1fr] gap-4">
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">{t('codeGeneration.tasks')}</CardTitle>
            <Button variant="ghost" size="sm" onClick={handleRefresh}>
              <RotateCw className="h-3 w-3" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="pb-0">
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-8">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-muted-foreground">{t('codeGeneration.loading')}</span>
            </div>
          ) : results.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8">
              <ScrollText className="h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground text-sm">{t('codeGeneration.noResults')}</p>
            </div>
          ) : (
            <div className="space-y-2 -mr-3 pr-3">
              {results.map((item) => (
                <Card
                  key={item.task_id}
                  className={`cursor-pointer hover:border-primary/50 transition-colors ${
                    selectedResult?.task_id === item.task_id ? 'border-primary' : ''
                  }`}
                  onClick={() => handleSelectResult(item.task_id)}
                >
                  <CardContent className="py-3 px-3">
                    <p className="text-sm font-medium truncate">{item.task_instruction}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <StatusBadge completionReason={item.completion_reason} />
                      <span className="text-xs text-muted-foreground">
                        {item.steps_executed} {t('codeGeneration.steps')}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <div>
        {selectedLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center gap-2 py-8">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm text-muted-foreground">{t('codeGeneration.loadingResult')}</span>
            </CardContent>
          </Card>
        ) : selectedResult ? (
          <ResultDetail result={selectedResult} />
        ) : results.length > 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12">
              <AlertTriangle className="h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground">{t('codeGeneration.selectTask')}</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12">
              <FileCode className="h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground">{t('codeGeneration.noExecutionHistory')}</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

export default CodeGenerationPage;