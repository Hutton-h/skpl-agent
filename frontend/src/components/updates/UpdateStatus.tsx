import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { RefreshCw, ExternalLink, GitBranch, Clock, AlertCircle, CheckCircle } from 'lucide-react';
import { useTranslation } from '@/i18n/useI18n';

interface UpstreamRepo {
  name: string;
  url: string;
  branch: string;
  hasUpdates: boolean;
  latestCommit?: string;
  latestTag?: string;
  commitsBehind: number;
  checkedAt: string;
  error?: string;
}

interface UpdateStatusProps {
  repos: UpstreamRepo[];
  onCheckNow?: () => void;
  isChecking?: boolean;
}

export function UpdateStatus({ repos, onCheckNow, isChecking = false }: UpdateStatusProps) {
  const { t } = useTranslation();
  const formatTime = (iso: string) => {
    if (!iso) return t('updates.never');
    const date = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000) return t('updates.justNow');
    if (diff < 3600000) return t('updates.minutesAgo', { n: Math.floor(diff / 60000) });
    if (diff < 86400000) return t('updates.hoursAgo', { n: Math.floor(diff / 3600000) });
    return date.toLocaleDateString();
  };

  const formatCommit = (hash?: string) => {
    if (!hash) return 'N/A';
    return hash.slice(0, 8);
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{t('updates.upstreamUpdates')}</CardTitle>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs gap-1"
            onClick={onCheckNow}
            disabled={isChecking}
          >
            <RefreshCw className={`h-3 w-3 ${isChecking ? 'animate-spin' : ''}`} />
            {isChecking ? t('updates.checking') : t('updates.checkNow')}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {repos.map((repo) => (
            <div
              key={repo.name}
              className="rounded-md border p-2.5 space-y-1.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-1.5">
                    {repo.error ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : repo.hasUpdates ? (
                      <AlertCircle className="h-4 w-4 text-amber-500" />
                    ) : (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    )}
                    <span className="text-sm font-medium capitalize">
                      {repo.name}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {repo.hasUpdates && (
                    <Badge variant="destructive" className="text-[10px] h-4 px-1">
                      {repo.commitsBehind > 0
                        ? `${repo.commitsBehind} ${t('updates.behind')}`
                        : t('updates.update')}
                    </Badge>
                  )}
                  <a
                    href={repo.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>

              <div className="flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <GitBranch className="h-3 w-3" />
                  {repo.branch}
                </span>
                {repo.latestCommit && (
                  <span className="font-mono">
                    {formatCommit(repo.latestCommit)}
                  </span>
                )}
                {repo.latestTag && (
                  <Badge variant="outline" className="text-[10px] h-4 px-1">
                    {repo.latestTag}
                  </Badge>
                )}
              </div>

              <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                <Clock className="h-3 w-3" />
                <span>{t('updates.checked')}: {formatTime(repo.checkedAt)}</span>
              </div>

              {repo.error && (
                <div className="text-[10px] text-red-500 truncate">
                  {t('updates.error')}: {repo.error}
                </div>
              )}
            </div>
          ))}

          {repos.length === 0 && (
            <div className="text-center py-4 text-muted-foreground">
              <p className="text-sm">{t('updates.noUpstreamRepos')}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default UpdateStatus;