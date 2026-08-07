import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Bug, CheckCircle, AlertTriangle, XCircle, Info } from 'lucide-react';
import { contextApi } from '@/api';
import { useTranslation } from '@/i18n/useI18n';

interface BugEntry {
  id: string;
  errorType: string;
  errorMessage: string;
  severity: string;
  status: string;
  occurrenceCount: number;
  firstSeen: string;
  lastSeen: string;
  fingerprint?: string;
}

interface BugTrackerProps {
  sessionId: string;
}

const severityConfig = {
  critical: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-500/10' },
  high: { icon: AlertTriangle, color: 'text-orange-500', bg: 'bg-orange-500/10' },
  medium: { icon: Bug, color: 'text-yellow-500', bg: 'bg-yellow-500/10' },
  low: { icon: Info, color: 'text-blue-500', bg: 'bg-blue-500/10' },
  info: { icon: Info, color: 'text-gray-500', bg: 'bg-gray-500/10' },
};

const statusVariantMap: Record<string, 'destructive' | 'secondary' | 'default' | 'outline'> = {
  new: 'destructive',
  acknowledged: 'secondary',
  fixed: 'default',
  wont_fix: 'outline',
  duplicate: 'outline',
};

export function BugTracker({ sessionId }: BugTrackerProps) {
  const { t } = useTranslation();
  const [bugs, setBugs] = useState<BugEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>('all');

  const getStatusLabel = (status: string) => {
    const labels: Record<string, string> = {
      new: t('buglog.open'),
      acknowledged: t('buglog.inProgress'),
      fixed: t('buglog.resolved'),
      wont_fix: t('buglog.wontFix'),
      duplicate: t('buglog.duplicate'),
    };
    return labels[status] || status;
  };

  useEffect(() => {
    let mounted = true;

    const fetchBugs = async () => {
      try {
        setLoading(true);
        const data = await contextApi.listBugs(sessionId, 50);
        if (mounted) {
          setBugs(
            (data as unknown as Array<Record<string, unknown>>).map((b: Record<string, unknown>) => ({
              id: b.id as string,
              errorType: b.error_type as string,
              errorMessage: b.error_message as string,
              severity: (b.severity as string) || 'medium',
              status: b.status as string,
              occurrenceCount: (b.occurrence_count as number) || 1,
              firstSeen: b.created_at as string,
              lastSeen: b.updated_at as string,
              fingerprint: b.fingerprint as string,
            })) || [],
          );
        }
      } catch {
        // Silently ignore — context may not be initialized yet
        if (mounted) setBugs([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchBugs();
    const interval = setInterval(fetchBugs, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [sessionId]);

  const filteredBugs = filter === 'all'
    ? bugs
    : bugs.filter((b) => b.status === filter);

  const severityCounts = bugs.reduce(
    (acc, bug) => {
      acc[bug.severity] = (acc[bug.severity] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{t('buglog.title')}</CardTitle>
          <div className="flex items-center gap-1">
            <Badge variant="outline" className="text-xs">
              {bugs.length} total
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Severity summary */}
        <div className="flex gap-2 mb-3">
          {Object.entries(severityConfig).map(([key, config]) => {
            const count = severityCounts[key] || 0;
            if (count === 0) return null;
            const Icon = config.icon;
            return (
              <Badge
                key={key}
                variant="outline"
                className={`text-xs gap-1 ${config.color}`}
              >
                <Icon className="h-3 w-3" />
                {count}
              </Badge>
            );
          })}
        </div>

        {/* Filter buttons */}
        <div className="flex gap-1 mb-2">
          {['all', 'new', 'acknowledged', 'fixed'].map((f) => (
            <Button
              key={f}
              variant={filter === f ? 'secondary' : 'ghost'}
              size="sm"
              className="h-6 text-xs px-2"
              onClick={() => setFilter(f)}
            >
              {f === 'all' ? t('buglog.all') : getStatusLabel(f)}
            </Button>
          ))}
        </div>

        <Separator className="mb-2" />

        {loading ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            Loading bugs...
          </div>
        ) : (
          <ScrollArea className="h-48">
            <div className="space-y-2">
              {filteredBugs.map((bug) => {
                const SevIcon = severityConfig[bug.severity as keyof typeof severityConfig]?.icon || Bug;
                const statusLabel = getStatusLabel(bug.status);
                const statusVariant = statusVariantMap[bug.status] || 'destructive';
                return (
                  <div
                    key={bug.id}
                    className="rounded-md border p-2 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <SevIcon
                          className={`h-3.5 w-3.5 ${severityConfig[bug.severity as keyof typeof severityConfig]?.color || ''}`}
                        />
                        <span className="font-medium truncate max-w-[200px]">
                          {bug.errorType}
                        </span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Badge variant={statusVariant} className="text-[10px] h-4 px-1">
                          {statusLabel}
                        </Badge>
                        {bug.occurrenceCount > 1 && (
                          <Badge variant="outline" className="text-[10px] h-4 px-1">
                            x{bug.occurrenceCount}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="text-muted-foreground truncate">
                      {bug.errorMessage}
                    </p>
                    <div className="flex justify-between text-[10px] text-muted-foreground">
                      <span>{t('buglog.firstSeen')}: {new Date(bug.firstSeen).toLocaleString()}</span>
                      <span>{t('buglog.lastSeen')}: {new Date(bug.lastSeen).toLocaleString()}</span>
                    </div>
                  </div>
                );
              })}
              {filteredBugs.length === 0 && (
                <div className="text-center py-4 text-muted-foreground">
                  <CheckCircle className="h-8 w-8 mx-auto mb-1 text-green-500" />
                  <p className="text-sm">{t('buglog.noBugs')}</p>
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

export default BugTracker;