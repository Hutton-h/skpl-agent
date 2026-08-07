/**
 * Web Intelligence Page — 网络智能搜索与研究页面
 *
 * 功能:
 * - 多引擎网页搜索
 * - 知识检索 (Knowledge Retrieval)
 * - 深度研究任务 (Research Agent)
 * - 搜索引擎列表查看
 */
import {
  Search,
  Globe,
  Brain,
  FlaskConical,
  Loader2,
  ExternalLink,
  Layers,
  ChevronRight,
  RotateCw,
  Bot,
} from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';

import { useTranslation } from '@/i18n/useI18n';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { ApiError } from '@/api/client';
import {
  webIntelligenceApi,
  type SearchResult,
  type ResearchStatus,
  type ResearchListItem,
} from '@/api/webIntelligence';

export function WebIntelligencePage() {
  const { t } = useTranslation();

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{t('common.webIntelligence')}</h1>
        <p className="text-muted-foreground mt-1">
          {t('webIntelligence.subtitle')}
        </p>
      </div>

      <Tabs defaultValue="search">
        <TabsList>
          <TabsTrigger value="search">
            <Search className="mr-1 h-4 w-4" /> {t('webIntelligence.tabs.search')}
          </TabsTrigger>
          <TabsTrigger value="knowledge">
            <Brain className="mr-1 h-4 w-4" /> {t('webIntelligence.tabs.knowledge')}
          </TabsTrigger>
          <TabsTrigger value="research">
            <FlaskConical className="mr-1 h-4 w-4" /> {t('webIntelligence.tabs.research')}
          </TabsTrigger>
          <TabsTrigger value="engines">
            <Layers className="mr-1 h-4 w-4" /> {t('webIntelligence.tabs.engines')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search" className="mt-4">
          <SearchPanel />
        </TabsContent>

        <TabsContent value="knowledge" className="mt-4">
          <KnowledgePanel />
        </TabsContent>

        <TabsContent value="research" className="mt-4">
          <ResearchPanel />
        </TabsContent>

        <TabsContent value="engines" className="mt-4">
          <EnginesPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Search Panel                                                       */
/* ------------------------------------------------------------------ */
function SearchPanel() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [engine, setEngine] = useState('');
  const [numResults, setNumResults] = useState(10);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await webIntelligenceApi.search({
        query: query.trim(),
        engine: engine || undefined,
        num_results: numResults,
      });
      setResults(res.results);
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('webIntelligence.search.failed'));
    } finally {
      setLoading(false);
    }
  }, [query, engine, numResults, t]);

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Input
          placeholder={t('webIntelligence.searchPlaceholder')}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="flex-1"
        />
        <Input
          placeholder={t('webIntelligence.enginePlaceholder')}
          value={engine}
          onChange={(e) => setEngine(e.target.value)}
          className="w-40"
        />
        <Input
          type="number"
          min={1}
          max={50}
          value={numResults}
          onChange={(e) => setNumResults(Number(e.target.value))}
          className="w-20"
        />
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Search className="mr-1 h-4 w-4" />}
          {t('webIntelligence.search.button')}
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            {t('webIntelligence.search.foundResults', { count: results.length })}
          </p>
          {results.map((r, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  <a
                    href={r.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline flex items-center gap-1"
                  >
                    {r.title}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">{r.snippet}</p>
                <div className="flex items-center gap-2 mt-2">
                  <Badge variant="secondary" className="text-xs">{r.source}</Badge>
                  <span className="text-xs text-muted-foreground truncate max-w-md">{r.url}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <Globe className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('webIntelligence.emptyHint')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Knowledge Panel                                                    */
/* ------------------------------------------------------------------ */
function KnowledgePanel() {
  const { t } = useTranslation();
  const [instruction, setInstruction] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [engine, setEngine] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');

  const handleRetrieve = useCallback(async () => {
    if (!instruction.trim()) return;
    setLoading(true);
    setError('');
    try {
      const res = await webIntelligenceApi.retrieveKnowledge({
        instruction: instruction.trim(),
        search_query: searchQuery.trim() || undefined,
        engine: engine || undefined,
      });
      setResults(res.results);
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('webIntelligence.knowledge.failed'));
    } finally {
      setLoading(false);
    }
  }, [instruction, searchQuery, engine, t]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-4 w-4" /> {t('webIntelligence.knowledge.title')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea
            placeholder={t('webIntelligence.knowledge.placeholder')}
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            rows={3}
          />
          <div className="flex gap-2">
            <Input
              placeholder={t('webIntelligence.knowledge.queryOverride')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
            <Input
              placeholder={t('webIntelligence.knowledge.engine')}
              value={engine}
              onChange={(e) => setEngine(e.target.value)}
              className="w-40"
            />
            <Button onClick={handleRetrieve} disabled={loading}>
              {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Brain className="mr-1 h-4 w-4" />}
              {t('webIntelligence.knowledge.retrieve')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">
                  <a href={r.url} target="_blank" rel="noopener noreferrer" className="hover:underline flex items-center gap-1">
                    {r.title}
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-3">{r.snippet}</p>
                <Badge variant="secondary" className="text-xs mt-2">{r.source}</Badge>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && results.length === 0 && !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <Brain className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('webIntelligence.knowledge.emptyHint')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Research Panel                                                     */
/* ------------------------------------------------------------------ */
function ResearchPanel() {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [context, setContext] = useState('');
  const [maxSources, setMaxSources] = useState(10);
  const [loading, setLoading] = useState(false);
  const [tasks, setTasks] = useState<ResearchListItem[]>([]);
  const [selectedTask, setSelectedTask] = useState<ResearchStatus | null>(null);
  const [selectedLoading, setSelectedLoading] = useState(false);
  const [error, setError] = useState('');

  const loadTasks = useCallback(async () => {
    try {
      const res = await webIntelligenceApi.listResearchTasks();
      setTasks(res);
    } catch {
      // Ignore list errors silently
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  const handleStartResearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError('');
    try {
      await webIntelligenceApi.startResearch({
        query: query.trim(),
        context: context.trim() || undefined,
        max_sources: maxSources,
      });
      setQuery('');
      setContext('');
      await loadTasks();
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('webIntelligence.research.failed'));
    } finally {
      setLoading(false);
    }
  }, [query, context, maxSources, loadTasks, t]);

  const handleViewTask = useCallback(async (taskId: string) => {
    setSelectedLoading(true);
    try {
      const res = await webIntelligenceApi.getResearchStatus(taskId);
      setSelectedTask(res);
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? t('webIntelligence.research.loadFailed'));
    } finally {
      setSelectedLoading(false);
    }
  }, [t]);

  const handleRefreshTasks = useCallback(() => {
    loadTasks();
  }, [loadTasks]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <FlaskConical className="h-4 w-4" /> {t('webIntelligence.research.startResearch')}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Input
            placeholder={t('webIntelligence.research.queryPlaceholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleStartResearch()}
          />
          <Textarea
            placeholder={t('webIntelligence.research.contextPlaceholder')}
            value={context}
            onChange={(e) => setContext(e.target.value)}
            rows={2}
          />
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={50}
              value={maxSources}
              onChange={(e) => setMaxSources(Number(e.target.value))}
              className="w-20"
            />
            <span className="text-sm text-muted-foreground">{t('webIntelligence.research.maxSources')}</span>
            <div className="flex-1" />
            <Button onClick={handleStartResearch} disabled={loading}>
              {loading ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <FlaskConical className="mr-1 h-4 w-4" />}
              {t('webIntelligence.research.startButton')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="py-3 text-sm text-destructive">{error}</CardContent>
        </Card>
      )}

      {/* Research Tasks List */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">{t('webIntelligence.research.tasksHeading')}</h3>
        <Button variant="ghost" size="sm" onClick={handleRefreshTasks}>
          <RotateCw className="mr-1 h-3 w-3" /> {t('webIntelligence.research.refresh')}
        </Button>
      </div>

      {tasks.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-8">
            <Bot className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground text-sm">{t('webIntelligence.research.noTasks')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {tasks.map((task) => (
            <Card
              key={task.task_id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => handleViewTask(task.task_id)}
            >
              <CardContent className="flex items-center justify-between py-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{task.query}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={task.status === 'completed' ? 'outline' : 'secondary'} className="text-xs">
                      {task.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      {t('webIntelligence.research.sources', { count: task.sources_count })}
                    </span>
                  </div>
                </div>
                <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Selected Task Detail */}
      {selectedLoading && (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-8">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">{t('webIntelligence.research.loadingDetails')}</span>
          </CardContent>
        </Card>
      )}

      {selectedTask && !selectedLoading && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-base">{t('webIntelligence.research.taskLabel', { query: selectedTask.query })}</CardTitle>
            <Badge variant={selectedTask.status === 'completed' ? 'outline' : 'secondary'}>
              {selectedTask.status}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4 text-sm mb-4">
              <div>
                <span className="text-muted-foreground">{t('webIntelligence.research.taskId')}</span>
                <p className="font-mono text-xs">{selectedTask.task_id}</p>
              </div>
              <div>
                <span className="text-muted-foreground">{t('webIntelligence.research.sourcesLabel')}</span>
                <p className="font-medium">{selectedTask.sources_count}</p>
              </div>
            </div>
            {selectedTask.sub_queries.length > 0 && (
              <div className="mb-4">
                <span className="text-sm text-muted-foreground">{t('webIntelligence.research.subQueries')}</span>
                <div className="flex flex-wrap gap-1 mt-1">
                  {selectedTask.sub_queries.map((sq, i) => (
                    <Badge key={i} variant="secondary" className="text-xs">{sq}</Badge>
                  ))}
                </div>
              </div>
            )}
            {selectedTask.synthesis && (
              <div>
                <span className="text-sm text-muted-foreground">{t('webIntelligence.research.synthesis')}</span>
                <p className="text-sm mt-1 whitespace-pre-wrap">{selectedTask.synthesis}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Engines Panel                                                      */
/* ------------------------------------------------------------------ */
function EnginesPanel() {
  const { t } = useTranslation();
  const [engines, setEngines] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    webIntelligenceApi.listEngines()
      .then((res: any) => setEngines(res.engines))
      .catch(() => setEngines([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-2 py-8">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">{t('webIntelligence.engines.loading')}</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3">
        {engines.map((engine) => (
          <Card key={engine}>
            <CardContent className="flex items-center gap-3 py-3">
              <Layers className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium text-sm">{engine}</p>
                <p className="text-xs text-muted-foreground">{t('webIntelligence.engines.available')}</p>
              </div>
              <div className="flex-1" />
              <Badge variant="outline">{t('webIntelligence.engines.active')}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
      {engines.length === 0 && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <Layers className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('webIntelligence.engines.noEngines')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default WebIntelligencePage;