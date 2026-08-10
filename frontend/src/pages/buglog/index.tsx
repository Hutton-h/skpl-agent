/**
 * Bug Log Page — 错误日志管理页面
 *
 * 功能:
 * - 查看近期 Bug 列表
 * - 按状态筛选 (open/resolved/duplicate)
 * - 更新 Bug 状态
 * - 查看 Bug 统计
 */
import {
  AlertTriangle,
  Bug,
  CheckCircle2,
  Copy,
  Filter,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { useTranslation } from '@/i18n/useI18n';
import { contextApi } from '@/api';
import type { BugEntry, BugStats } from '@/api/context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

// ── Status Badge ────────────────────────────────────────────────────────────

function BugStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
    open: 'destructive',
    in_progress: 'default',
    resolved: 'outline',
    duplicate: 'secondary',
    wont_fix: 'secondary',
  };
  const statusLabels: Record<string, string> = {
    open: t('buglog.open'),
    in_progress: t('buglog.inProgress'),
    resolved: t('buglog.resolved'),
    duplicate: t('buglog.duplicate'),
    wont_fix: t('buglog.wontFix'),
  };
  return (
    <Badge variant={variants[status] ?? 'secondary'}>
      {statusLabels[status] ?? status.replace('_', ' ')}
    </Badge>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export function BugLogPage() {
  const { t } = useTranslation();
  const [sessionId] = useState(() => localStorage.getItem('active_session_id') || '');
  const [loading, setLoading] = useState(true);
  const [bugs, setBugs] = useState<BugEntry[]>([]);
  const [stats, setStats] = useState<BugStats | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [updating, setUpdating] = useState<string | null>(null);

  const loadBugs = useCallback(async () => {
    setLoading(true);
    try {
      const [bugList, bugStats] = await Promise.all([
        contextApi.listBugs(
          sessionId,
          50,
          statusFilter === 'all' ? undefined : statusFilter,
        ),
        contextApi.getBugStats(sessionId),
      ]);
      setBugs(bugList);
      setStats(bugStats);
    } catch {
      setBugs([]);
    } finally {
      setLoading(false);
    }
  }, [sessionId, statusFilter]);

  useEffect(() => {
    if (!sessionId) {
      setLoading(false);
      return;
    }
    loadBugs();
  }, [loadBugs]);

  const handleUpdateStatus = async (bugId: string, newStatus: string) => {
    setUpdating(bugId);
    try {
      await contextApi.updateBugStatus(sessionId, bugId, {
        status: newStatus,
      });
      await loadBugs();
    } catch {
      // Silent
    } finally {
      setUpdating(null);
    }
  };

  const formatDate = (iso: string) => {
    const d = new Date(iso);
    return d.toLocaleString();
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {!sessionId && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="flex flex-col items-center gap-2 py-8">
            <Bug className="h-8 w-8 text-amber-500" />
            <p className="text-sm text-muted-foreground text-center">
              {t('buglog.noSessionSelected') || 'No active session selected. Please open a chat session first to view bug logs.'}
            </p>
          </CardContent>
        </Card>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{t('buglog.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {t('buglog.subtitle')}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadBugs} disabled={loading}>
          <RefreshCw className={`mr-1 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          {t('buglog.refresh')}
        </Button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{t('buglog.total')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-destructive">{t('buglog.open')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-destructive">
                {stats.open}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{t('buglog.resolved')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.resolved}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">{t('buglog.duplicates')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.duplicate}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder={t('buglog.filterByStatus')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('buglog.allStatuses')}</SelectItem>
            <SelectItem value="open">{t('buglog.open')}</SelectItem>
            <SelectItem value="in_progress">{t('buglog.inProgress')}</SelectItem>
            <SelectItem value="resolved">{t('buglog.resolved')}</SelectItem>
            <SelectItem value="duplicate">{t('buglog.duplicate')}</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Bug List */}
      {loading ? (
        <div className="space-y-2">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      ) : bugs.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12">
            <Bug className="h-8 w-8 text-muted-foreground" />
            <p className="text-muted-foreground">{t('buglog.noBugs')}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="rounded-lg border">
          {bugs.map((bug) => (
            <div
              key={bug.id}
              className="flex items-start gap-4 p-4 border-b last:border-0 hover:bg-muted/30"
            >
              <div className="mt-0.5">
                {bug.status === 'resolved' ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertTriangle className="h-5 w-5 text-destructive" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <BugStatusBadge status={bug.status} />
                  <span className="font-mono text-sm font-medium">
                    {bug.error_type}
                  </span>
                  {bug.duplicate_of && (
                    <Badge variant="outline" className="text-xs">
                      <Copy className="mr-1 h-3 w-3" />
                      {t('buglog.duplicateOf')} {bug.duplicate_of.slice(0, 8)}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {bug.error_message}
                </p>
                {bug.file_path && (
                  <p className="text-xs text-muted-foreground mt-1 font-mono">
                    {bug.file_path}
                    {bug.line_number ? `:${bug.line_number}` : ''}
                  </p>
                )}
                <p className="text-xs text-muted-foreground mt-1">
                  {formatDate(bug.created_at)}
                </p>
              </div>
              <div className="flex items-center gap-1">
                {bug.status === 'open' && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUpdateStatus(bug.id, 'resolved')}
                      disabled={updating === bug.id}
                    >
                      {updating === bug.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        t('buglog.resolve')
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleUpdateStatus(bug.id, 'duplicate')}
                      disabled={updating === bug.id}
                    >
                      {t('buglog.duplicate')}
                    </Button>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default BugLogPage;