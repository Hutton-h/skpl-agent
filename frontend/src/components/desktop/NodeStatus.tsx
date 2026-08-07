import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Monitor, CheckCircle, XCircle, AlertCircle, RefreshCw, Clock } from 'lucide-react';
import { client } from '@/api/client';
import { useTranslation } from '@/i18n/useI18n';

interface DesktopNode {
  id: string;
  status: 'connected' | 'disconnected' | 'busy' | 'error';
  hostname: string;
  platform: string;
  lastActive: string;
  currentTask?: string;
  screenshotCount: number;
  actionCount: number;
}

interface NodeStatusProps {
  onNodeSelect?: (nodeId: string) => void;
}

export function NodeStatus({ onNodeSelect }: NodeStatusProps) {
  const { t } = useTranslation();
  const [nodes, setNodes] = useState<DesktopNode[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNodes = async () => {
      try {
        setLoading(true);
        const data = await client.get<any>('/api/desktop-automation/sessions');
        // Map sessions to node display format
        const sessions = Array.isArray(data) ? data : (data.sessions || []);
        setNodes(sessions.map((s: Record<string, unknown>) => ({
          id: s.id as string,
          status: (s.status as string) || 'disconnected',
          hostname: (s.hostname as string) || (s.id as string),
          platform: (s.platform as string) || 'unknown',
          lastActive: (s.updated_at as string) || (s.created_at as string) || new Date().toISOString(),
          currentTask: s.current_task as string | undefined,
          screenshotCount: (s.screenshot_count as number) || 0,
          actionCount: (s.action_count as number) || 0,
        })));
      } catch (err) {
        console.error('Failed to fetch desktop nodes:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchNodes();
    const interval = setInterval(fetchNodes, 3000);
    return () => clearInterval(interval);
  }, []);

  const statusIcons = {
    connected: { icon: CheckCircle, color: 'text-green-500' },
    disconnected: { icon: XCircle, color: 'text-gray-400' },
    busy: { icon: RefreshCw, color: 'text-blue-500 animate-spin' },
    error: { icon: AlertCircle, color: 'text-red-500' },
  };

  const statusLabels = {
    connected: t('desktop.statusConnected'),
    disconnected: t('desktop.statusDisconnected'),
    busy: t('desktop.statusProcessing'),
    error: t('desktop.statusError'),
  };

  const formatTime = (iso: string) => {
    const date = new Date(iso);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    if (diff < 60000) return t('desktop.justNow');
    if (diff < 3600000) return t('desktop.minutesAgo', { n: Math.floor(diff / 60000) });
    if (diff < 86400000) return t('desktop.hoursAgo', { n: Math.floor(diff / 3600000) });
    return date.toLocaleDateString();
  };

  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{t('desktop.nodeTitle')}</CardTitle>
          <Badge variant="outline" className="text-xs">
            {t('desktop.nodesOnline', { connected: nodes.filter((n) => n.status === 'connected').length, total: nodes.length })}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {loading && nodes.length === 0 ? (
          <div className="py-4 text-center text-sm text-muted-foreground">
            {t('desktop.scanningNodes')}
          </div>
        ) : (
          <div className="space-y-2">
            {nodes.map((node) => {
              const StatusIcon = statusIcons[node.status]?.icon || CheckCircle;
              const statusColor = statusIcons[node.status]?.color || 'text-gray-500';
              const statusLabel = statusLabels[node.status] || node.status;

              return (
                <div
                  key={node.id}
                  className="rounded-md border p-2.5 cursor-pointer hover:bg-accent/50 transition-colors"
                  onClick={() => onNodeSelect?.(node.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Monitor className="h-4 w-4 text-muted-foreground" />
                      <div className="text-sm font-medium">{node.hostname}</div>
                    </div>
                    <Badge
                      variant="outline"
                      className={`text-xs gap-1 ${statusColor}`}
                    >
                      <StatusIcon className={`h-3 w-3 ${node.status === 'busy' ? 'animate-spin' : ''}`} />
                      {statusLabel}
                    </Badge>
                  </div>

                  <div className="mt-1.5 flex items-center justify-between text-xs text-muted-foreground">
                    <div className="flex items-center gap-3">
                      <span>{node.platform}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTime(node.lastActive)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span>{node.screenshotCount} {t('desktop.shots')}</span>
                      <span>{node.actionCount} {t('desktop.actions')}</span>
                    </div>
                  </div>

                  {node.currentTask && (
                    <div className="mt-1 text-xs text-blue-500 truncate">
                      {t('desktop.task')}: {node.currentTask}
                    </div>
                  )}
                </div>
              );
            })}
            {nodes.length === 0 && (
              <div className="text-center py-6 text-muted-foreground">
                <Monitor className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">{t('desktop.noNodesConnected')}</p>
                <Button variant="link" size="sm" className="text-xs mt-1">
                  {t('desktop.connectNode')}
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default NodeStatus;