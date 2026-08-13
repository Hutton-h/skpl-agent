/**
 * Desktop Agent Page — 桌面 Agent 管理页面
 *
 * 功能:
 * - 查看已连接的桌面 Agent 节点
 * - 管理桌面 Agent 配置
 * - 监控桌面操作状态
 */
import {
  Monitor,
  Wifi,
  WifiOff,
  Loader2,
  Settings,
  Terminal,
  Cpu,
  HardDrive,
  Activity,
  Download,
  Laptop,
  CheckCircle2,
  ArrowRight,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { useTranslation } from '@/i18n/useI18n';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { desktopNodeApi } from '@/api';
import type { DesktopNode as ApiDesktopNode } from '@/api/desktopNode';
import { Progress } from '@/components/ui/progress';

interface DesktopNodeUI {
  id: string;
  name: string;
  hostname: string;
  status: 'online' | 'idle' | 'busy' | 'offline' | 'connecting';
  os: string;
  version: string;
  last_seen: string;
  active_sessions: number;
  cpu_percent: number;
  memory_percent: number;
  screen_width: number;
  screen_height: number;
  capabilities: string[];
}

function NodeStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const variants: Record<string, { icon: React.ReactNode; label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
    online: { icon: <Wifi className="h-3 w-3" />, label: t('desktop.online'), variant: 'outline' },
    idle: { icon: <Wifi className="h-3 w-3" />, label: t('desktop.idle'), variant: 'outline' },
    busy: { icon: <Activity className="h-3 w-3" />, label: t('desktop.busy'), variant: 'default' },
    offline: { icon: <WifiOff className="h-3 w-3" />, label: t('desktop.offline'), variant: 'secondary' },
    connecting: { icon: <Loader2 className="h-3 w-3 animate-spin" />, label: t('desktop.connecting'), variant: 'default' },
  };
  const v = variants[status] ?? variants.offline;
  return (
    <Badge variant={v.variant} className="gap-1">
      {v.icon} {v.label}
    </Badge>
  );
}

function mapNodeStatus(status: string): DesktopNodeUI['status'] {
  switch (status) {
    case 'online': return 'online';
    case 'idle': return 'idle';
    case 'busy': return 'busy';
    case 'connecting': return 'connecting';
    default: return 'offline';
  }
}

export function DesktopPage() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [nodes, setNodes] = useState<DesktopNodeUI[]>([]);
  const [onlineCount, setOnlineCount] = useState(0);

  const loadNodes = useCallback(() => {
    desktopNodeApi.listNodes()
      .then((res) => {
        setNodes(res.nodes.map((n: ApiDesktopNode) => ({
          id: n.node_id,
          name: n.node_name || n.node_id,
          hostname: n.node_id,
          status: mapNodeStatus(n.status),
          os: n.os_name || 'N/A',
          version: n.os_version || 'N/A',
          last_seen: n.last_seen,
          active_sessions: n.active_actions,
          cpu_percent: n.cpu_percent,
          memory_percent: n.memory_percent,
          screen_width: n.screen_width,
          screen_height: n.screen_height,
          capabilities: n.capabilities,
        })));
        setOnlineCount(res.online_count);
      })
      .catch(() => {
        setNodes([]);
        setOnlineCount(0);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadNodes();
    // Auto-refresh every 15 seconds
    const interval = setInterval(loadNodes, 15000);
    return () => clearInterval(interval);
  }, [loadNodes]);

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t('desktop.title')}
          </h1>
          <p className="text-muted-foreground mt-1">
            {t('desktop.subtitle')}
            {nodes.length > 0 && (
              <span className="ml-2 text-xs">
                ({onlineCount}/{nodes.length} {t('desktop.online')})
              </span>
            )}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadNodes}>
          <Loader2 className="mr-1 h-4 w-4" />
          {t('common.refresh')}
        </Button>
      </div>

      {/* Download Guide - shown when no nodes */}
      {!loading && nodes.length === 0 && (
        <Card className="border-2 border-dashed border-blue-200 bg-gradient-to-br from-blue-50/50 to-indigo-50/50 overflow-hidden">
          <CardContent className="p-6 md:p-8">
            <div className="flex flex-col md:flex-row items-center gap-6">
              <div className="md:w-3/5 space-y-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                    <Laptop className="w-4 h-4 text-white" />
                  </div>
                  <h2 className="text-xl font-bold text-gray-800">还没有桌面节点？一键安装</h2>
                </div>
                <p className="text-gray-600 text-sm">
                  安装桌面节点后，AI 可以自动操作你的电脑：打开网页、填写表单、处理文件、截图等。
                  整个过程只需 30 秒，无需任何技术知识。
                </p>
                <div className="grid grid-cols-3 gap-3">
                  <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100 text-center">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mx-auto mb-2 text-sm font-bold">1</div>
                    <p className="text-xs font-medium text-gray-700">下载安装包</p>
                    <p className="text-xs text-gray-400 mt-0.5">自动适配系统</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100 text-center">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mx-auto mb-2 text-sm font-bold">2</div>
                    <p className="text-xs font-medium text-gray-700">双击运行</p>
                    <p className="text-xs text-gray-400 mt-0.5">无需配置</p>
                  </div>
                  <div className="bg-white rounded-xl p-3 shadow-sm border border-gray-100 text-center">
                    <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 mx-auto mb-2 text-sm font-bold">3</div>
                    <p className="text-xs font-medium text-gray-700">自动连接</p>
                    <p className="text-xs text-gray-400 mt-0.5">即开即用</p>
                  </div>
                </div>
                <div className="flex gap-3">
                  <Button
                    size="lg"
                    className="bg-blue-600 hover:bg-blue-700 text-white gap-2"
                    onClick={async () => {
                      try {
                        const baseUrl = localStorage.getItem('server_url') || 'http://localhost:8000';
                        let url = baseUrl.trim();
                        if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');

                        // Step 1: Get install token
                        const tokenRes = await fetch(`${url}/api/desktop/install-token`);
                        if (!tokenRes.ok) {
                          throw new Error('获取安装令牌失败');
                        }
                        const tokenData = await tokenRes.json();

                        // Step 2: Download using the token-authenticated URL
                        window.open(tokenData.download_url, '_blank');
                      } catch (err) {
                        console.error('Download failed:', err);
                        // Fallback: try direct download (may work if server allows)
                        const baseUrl = localStorage.getItem('server_url') || 'http://localhost:8000';
                        let url = baseUrl.trim();
                        if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');
                        window.open(url + '/api/desktop/download-installer', '_blank');
                      }
                    }}
                  >
                    <Download className="w-4 h-4" />
                    下载 Windows 安装包
                  </Button>
                  <Button
                    size="lg"
                    variant="outline"
                    className="gap-2"
                    onClick={async () => {
                      try {
                        const baseUrl = localStorage.getItem('server_url') || 'http://localhost:8000';
                        let url = baseUrl.trim();
                        if (!/^https?:\/\//i.test(url)) url = 'http://' + url;
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
                        url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');

                        const res = await fetch(`${url}/api/desktop/install-token`);
                        const data = await res.json();
                        // Copy token to clipboard
                        await navigator.clipboard.writeText(data.token);
                        toast.success('安装令牌已复制到剪贴板');
                      } catch {
                        toast.error('获取安装令牌失败');
                      }
                    }}
                  >
                    <ArrowRight className="w-4 h-4" />
                    获取安装令牌
                  </Button>
                </div>
                <p className="text-xs text-gray-400">
                  支持 Windows 10/11，macOS 版本即将推出
                </p>
              </div>
              <div className="md:w-2/5 flex justify-center">
                <div className="relative w-48 h-48">
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-400 to-indigo-600 rounded-2xl shadow-lg flex items-center justify-center">
                    <Laptop className="w-16 h-16 text-white/80" />
                  </div>
                  <div className="absolute -bottom-2 -right-2 w-12 h-12 bg-green-500 rounded-full flex items-center justify-center shadow-lg">
                    <CheckCircle2 className="w-6 h-6 text-white" />
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Node List */}
      <div className="grid gap-4">
        {loading ? (
          <Card>
            <CardContent className="py-8">
              <div className="flex items-center justify-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">
                  {t('desktop.loadingNodes')}
                </span>
              </div>
            </CardContent>
          </Card>
        ) : nodes.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center gap-2 py-12">
              <Monitor className="h-8 w-8 text-muted-foreground" />
              <p className="text-muted-foreground">{t('desktop.noNodes')}</p>
              <p className="text-xs text-muted-foreground">
                {t('desktop.noNodesHint')}
              </p>
            </CardContent>
          </Card>
        ) : (
          nodes.map((node) => (
            <Card key={node.id}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <div className="flex items-center gap-3">
                  <Monitor className="h-5 w-5 text-muted-foreground" />
                  <div>
                    <CardTitle className="text-base">{node.name}</CardTitle>
                    <p className="text-xs text-muted-foreground font-mono">
                      {node.hostname}
                    </p>
                  </div>
                </div>
                <NodeStatusBadge status={node.status} />
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm mb-3">
                  <div>
                    <span className="text-muted-foreground">{t('desktop.os')}</span>
                    <p className="font-medium">{node.os}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('desktop.version')}</span>
                    <p className="font-medium">{node.version}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('desktop.activeSessions')}</span>
                    <p className="font-medium">{node.active_sessions}</p>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('desktop.lastSeen')}</span>
                    <p className="font-medium">
                      {new Date(node.last_seen).toLocaleTimeString()}
                    </p>
                  </div>
                </div>
                {/* Resource usage bars */}
                {(node.cpu_percent > 0 || node.memory_percent > 0) && (
                  <div className="grid grid-cols-2 gap-3 pt-2 border-t">
                    <div className="flex items-center gap-2">
                      <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground w-16">CPU</span>
                      <Progress value={node.cpu_percent} className="h-2 flex-1" />
                      <span className="text-xs font-mono w-10 text-right">{node.cpu_percent.toFixed(0)}%</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <HardDrive className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs text-muted-foreground w-16">MEM</span>
                      <Progress value={node.memory_percent} className="h-2 flex-1" />
                      <span className="text-xs font-mono w-10 text-right">{node.memory_percent.toFixed(0)}%</span>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Connection Info */}
      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">
            <Terminal className="mr-1 h-4 w-4" /> {t('desktop.connection')}
          </TabsTrigger>
          <TabsTrigger value="settings">
            <Settings className="mr-1 h-4 w-4" /> {t('common.settings')}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('desktop.connectionDetails')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('desktop.protocol')}</span>
                  <span className="font-mono">WebSocket</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('desktop.authentication')}</span>
                  <span className="font-mono">JWT Token</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('desktop.heartbeat')}</span>
                  <span>Every 10s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">{t('desktop.timeout')}</span>
                  <span>60s</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t('desktop.desktopSettings')}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                {t('desktop.desktopSettingsDesc')}
              </p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default DesktopPage;