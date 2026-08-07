/**
 * Firecrawl Page — 网页抓取技能管理页面
 *
 * 功能:
 * - 发起网页抓取请求
 * - 查看抓取历史
 * - 配置抓取参数
 * - 查看抓取统计
 */
import {
  Globe,
  Loader2,
  Play,
  ExternalLink,
  Clock,
  CheckCircle2,
  XCircle,
  Settings,
  BarChart3,
  RotateCw,
  X,
} from 'lucide-react';
import { useEffect, useState, useCallback } from 'react';

import { useTranslation } from '@/i18n/useI18n';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ApiError } from '@/api/client';
import {
  firecrawlApi,
  type CrawlResult,
  type FirecrawlStats,
} from '@/api/firecrawl';

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const variants: Record<string, { icon: React.ReactNode; label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
    pending: { icon: <Clock className="h-3 w-3" />, label: t('firecrawl.pending'), variant: 'secondary' },
    running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, label: t('firecrawl.running'), variant: 'default' },
    completed: { icon: <CheckCircle2 className="h-3 w-3" />, label: t('firecrawl.done'), variant: 'outline' },
    failed: { icon: <XCircle className="h-3 w-3" />, label: t('firecrawl.failed'), variant: 'destructive' },
  };
  const v = variants[status] ?? variants.pending;
  return (
    <Badge variant={v.variant} className="gap-1">
      {v.icon} {v.label}
    </Badge>
  );
}

export function FirecrawlPage() {
  const { t } = useTranslation();
  const [url, setUrl] = useState('');
  const [crawling, setCrawling] = useState(false);
  const [results, setResults] = useState<CrawlResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadResults = useCallback(async () => {
    try {
      const res = await firecrawlApi.listCrawls(50);
      setResults(Array.isArray(res) ? res : []);
    } catch {
      // Silently ignore list errors on initial load
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadResults();
  }, [loadResults]);

  const handleCrawl = async () => {
    if (!url.trim()) return;
    setCrawling(true);
    setError('');
    try {
      const res = await firecrawlApi.startCrawl({
        url: url.trim(),
        mode: 'crawl',
      });
      setResults((prev) => [res, ...prev]);
      setUrl('');
    } catch (e: any) {
      setError((e as ApiError)?.detail ?? e.message ?? 'Crawl failed');
    } finally {
      setCrawling(false);
    }
  };

  const handleCancel = async (crawlId: string) => {
    try {
      await firecrawlApi.cancelCrawl(crawlId);
      await loadResults();
    } catch {
      // silently ignore
    }
  };

  const handleRefresh = () => {
    loadResults();
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t('firecrawl.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {t('firecrawl.subtitle')}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh}>
          <RotateCw className="mr-1 h-3 w-3" /> {t('firecrawl.refresh')}
        </Button>
      </div>

      {/* Crawl Input */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Globe className="h-4 w-4" />
            {t('firecrawl.newCrawl')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              placeholder={t('firecrawl.urlPlaceholder')}
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCrawl()}
              className="flex-1"
            />
            <Button onClick={handleCrawl} disabled={crawling || !url.trim()}>
              {crawling ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              {crawling ? t('firecrawl.crawling') : t('firecrawl.crawl')}
            </Button>
          </div>
          {error && (
            <p className="text-sm text-destructive mt-2">{error}</p>
          )}
        </CardContent>
      </Card>

      {/* Results */}
      <Tabs defaultValue="history">
        <TabsList>
          <TabsTrigger value="history">
            <Clock className="mr-1 h-4 w-4" /> {t('firecrawl.history')}
          </TabsTrigger>
          <TabsTrigger value="stats">
            <BarChart3 className="mr-1 h-4 w-4" /> {t('firecrawl.stats')}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="mr-1 h-4 w-4" /> {t('firecrawl.settings')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="history" className="mt-4">
          {loading ? (
            <Card>
              <CardContent className="flex items-center justify-center gap-2 py-8">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">{t('common.loading')}</span>
              </CardContent>
            </Card>
          ) : results.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center gap-2 py-12">
                <Globe className="h-8 w-8 text-muted-foreground" />
                <p className="text-muted-foreground">{t('firecrawl.noHistory')}</p>
                <p className="text-xs text-muted-foreground">
                  {t('firecrawl.noHistoryHint')}
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="rounded-lg border">
              {results.map((result) => (
                <div
                  key={result.id}
                  className="flex items-center gap-4 p-4 border-b last:border-0 hover:bg-muted/30"
                >
                  <StatusBadge status={result.status} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm truncate">
                        {result.url}
                      </span>
                      <a
                        href={result.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground shrink-0"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      {result.pages_crawled} {t('firecrawl.pagesCrawled')}
                      {result.pages_failed > 0 ? ` (${result.pages_failed} ${t('firecrawl.pagesFailed')})` : ''}
                      {' · '}
                      {new Date(result.created_at).toLocaleString()}
                    </p>
                    {result.error && (
                      <p className="text-xs text-destructive mt-1 truncate">
                        {result.error}
                      </p>
                    )}
                  </div>
                  {(result.status === 'pending' || result.status === 'running') && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCancel(result.id)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="stats" className="mt-4">
          <StatsPanel />
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('firecrawl.crawlConfig')}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {t('firecrawl.crawlConfigDesc')}
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function StatsPanel() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<FirecrawlStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await firecrawlApi.getStats();
      setStats(res);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center gap-2 py-8">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm text-muted-foreground">{t('firecrawl.loadingStats')}</span>
        </CardContent>
      </Card>
    );
  }

  if (!stats) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-12">
          <BarChart3 className="h-8 w-8 text-muted-foreground" />
          <p className="text-muted-foreground">{t('firecrawl.noStats')}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
      <Card>
        <CardContent className="py-4 text-center">
          <p className="text-2xl font-bold">{stats.total_crawls}</p>
          <p className="text-xs text-muted-foreground">{t('firecrawl.totalCrawls')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 text-center">
          <p className="text-2xl font-bold text-green-600">{stats.completed_crawls}</p>
          <p className="text-xs text-muted-foreground">{t('firecrawl.completed')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 text-center">
          <p className="text-2xl font-bold text-red-600">{stats.failed_crawls}</p>
          <p className="text-xs text-muted-foreground">{t('firecrawl.failed')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 text-center">
          <p className="text-2xl font-bold text-blue-600">{stats.active_crawls}</p>
          <p className="text-xs text-muted-foreground">{t('firecrawl.active')}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="py-4 text-center">
          <p className="text-2xl font-bold">{stats.total_pages_crawled}</p>
          <p className="text-xs text-muted-foreground">{t('firecrawl.totalPagesCrawled')}</p>
        </CardContent>
      </Card>
    </div>
  );
}

export default FirecrawlPage;