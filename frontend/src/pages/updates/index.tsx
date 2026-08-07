/**
 * Upstream Update Status Page
 *
 * Displays the update status of the four upstream repositories
 * (AgentScope, OpenWolf, Agent-S, Firecrawl). Shows:
 * - Last check time
 * - Commits behind count
 * - Latest tag
 * - Manual trigger for update checks
 */
import {
  RefreshCw,
  GitBranch,
  GitCommit,
  Tag,
  Clock,
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Loader2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { client } from '@/api/client';
import { useTranslation } from '@/i18n/useI18n';
interface UpstreamRepoStatus {
  repo: string;
  url?: string;
  has_updates: boolean;
  commits_behind: number;
  latest_tag: string;
  current_commit?: string;
  latest_commit?: string;
  breaking_changes: string[];
  error: string | null;
  checked_at?: string;
}

interface UpdateStatus {
  running: boolean;
  check_interval_hours: number;
  auto_merge?: boolean;
  last_check: string | null;
  next_scheduled_run?: string | null;
  repos: UpstreamRepoStatus[];
  total_repos: number;
  repos_with_updates: number;
}

const REPO_DISPLAY: Record<string, { name: string; color: string }> = {
  agentscope: { name: 'AgentScope', color: 'bg-blue-500/10 text-blue-600' },
  openwolf: { name: 'OpenWolf', color: 'bg-purple-500/10 text-purple-600' },
  'agent-s': { name: 'Agent-S', color: 'bg-green-500/10 text-green-600' },
  firecrawl: { name: 'Firecrawl', color: 'bg-orange-500/10 text-orange-600' },
};

function formatTimeAgo(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.floor(diffHr / 24);
  return `${diffDay}d ago`;
}

export function UpdatesPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<UpdateStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const data = await client.get<any>('/api/updates/status');
      // Map API response to UpdateStatus interface
      const lastReport = data.last_report;
      const repos: UpstreamRepoStatus[] = lastReport?.results?.map((r: any) => ({
        repo: r.repo,
        has_updates: r.has_updates ?? false,
        commits_behind: r.commits_behind ?? 0,
        latest_tag: r.latest_tag ?? 'N/A',
        breaking_changes: r.breaking_changes ?? [],
        error: r.error ?? null,
      })) ?? [];
      setStatus({
        running: data.running ?? false,
        check_interval_hours: data.check_interval_hours ?? 6,
        last_check: data.last_check ?? null,
        repos,
        total_repos: data.checker?.tracked_repos ?? repos.length,
        repos_with_updates: lastReport?.repos_with_updates ?? repos.filter(r => r.has_updates).length,
      });
    } catch {
      setError(t('updates.loadFailed'));
    } finally {
      setLoading(false);
    }
  }, []);

  const triggerCheck = useCallback(async () => {
    setChecking(true);
    try {
      await client.post('/api/updates/check');
      await fetchStatus();
    } catch {
      setError(t('updates.triggerFailed'));
    } finally {
      setChecking(false);
    }
  }, [fetchStatus]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Upstream Updates
          </h1>
          <p className="text-muted-foreground mt-1">
            Monitor the four upstream projects for new commits and releases
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={triggerCheck}
          disabled={checking}
        >
          {checking ? (
            <Loader2 className="mr-1 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-1 h-4 w-4" />
          )}
          {checking ? 'Checking...' : 'Check Now'}
        </Button>
      </div>

      {/* Error Banner */}
      {error && (
        <Card className="border-destructive/50 bg-destructive/5">
          <CardContent className="flex items-center gap-2 py-3">
            <AlertTriangle className="h-4 w-4 text-destructive" />
            <p className="text-sm text-destructive">{error}</p>
          </CardContent>
        </Card>
      )}

      {/* Status Summary */}
      {status && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Last Check
              </CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {status.last_check
                  ? formatTimeAgo(status.last_check)
                  : 'Never'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Next: {status.next_scheduled_run
                  ? formatTimeAgo(status.next_scheduled_run)
                  : t('updates.notScheduled')}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Repos Tracked
              </CardTitle>
              <GitBranch className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{status.total_repos}</div>
              <p className="text-xs text-muted-foreground mt-1">
                Check every {status.check_interval_hours}h
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Updates Available
              </CardTitle>
              {status.repos_with_updates > 0 ? (
                <AlertTriangle className="h-4 w-4 text-amber-500" />
              ) : (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {status.repos_with_updates}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {status.repos_with_updates > 0
                  ? 'Repos have pending updates'
                  : t('updates.allUpToDate')}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <Card>
          <CardContent className="flex items-center justify-center gap-2 py-12">
            <Loader2 className="h-4 w-4 animate-spin" />
            <span className="text-sm text-muted-foreground">
              Loading update status...
            </span>
          </CardContent>
        </Card>
      )}

      {/* Repo Cards */}
      {status && !loading && (
        <div className="grid gap-4">
          {status.repos.map((repo) => {
            const display = REPO_DISPLAY[repo.repo] ?? {
              name: repo.repo,
              color: 'bg-gray-500/10 text-gray-600',
            };
            return (
              <Card key={repo.repo} className={repo.has_updates ? 'border-amber-500/30' : ''}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <div className="flex items-center gap-3">
                    <Badge
                      variant="outline"
                      className={`font-mono text-xs ${display.color}`}
                    >
                      {display.name}
                    </Badge>
                    <CardTitle className="text-base font-mono text-sm">
                      {repo.repo}
                    </CardTitle>
                    {repo.url && (
                      <a
                        href={repo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                  {repo.has_updates ? (
                    <Badge variant="default" className="bg-amber-500/15 text-amber-600 gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      Updates Available
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-green-600 gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Up to Date
                    </Badge>
                  )}
                </CardHeader>
                <CardContent>
                  {/* Error State */}
                  {repo.error && (
                    <div className="flex items-center gap-2 mb-3 p-2 rounded bg-destructive/5 text-destructive text-sm">
                      <AlertTriangle className="h-3 w-3" />
                      {repo.error}
                    </div>
                  )}

                  {/* Metrics */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="flex items-center gap-2">
                      <GitCommit className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Behind</p>
                        <p className={`font-mono font-bold ${repo.commits_behind > 0 ? 'text-amber-600' : ''}`}>
                          {repo.commits_behind} commits
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Tag className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Latest Tag</p>
                        <p className="font-mono text-sm">{repo.latest_tag}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <GitBranch className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Current</p>
                        <p className="font-mono text-xs">{repo.current_commit?.slice(0, 7) ?? 'N/A'}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Checked</p>
                        <p className="text-sm">{repo.checked_at ? formatTimeAgo(repo.checked_at) : 'N/A'}</p>
                      </div>
                    </div>
                  </div>

                  {/* Breaking Changes */}
                  {repo.breaking_changes.length > 0 && (
                    <>
                      <Separator className="my-3" />
                      <div>
                        <p className="text-xs font-medium text-destructive mb-1">
                          Breaking Changes
                        </p>
                        <ul className="list-disc list-inside space-y-1">
                          {repo.breaking_changes.map((change, i) => (
                            <li key={i} className="text-xs text-muted-foreground">
                              {change}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default UpdatesPage;