/**
 * MemoryHealthPanel — 记忆系统健康状态面板
 *
 * 显示 L1(Cerebrum) / L2(Mem0) / L3(KnowledgeBase) 三层记忆子系统的连接状态，
 * 以及 MemoryManager 的整体健康概要。
 */
import {
  Activity,
  AlertCircle,
  Brain,
  CheckCircle2,
  Database,
  Layers,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { contextApi } from '@/api';
import type { MemoryHealth } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

// ── Layer config ────────────────────────────────────────────────────────────

interface LayerInfo {
  key: keyof MemoryHealth;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const LAYERS: LayerInfo[] = [
  {
    key: 'l1_cerebrum',
    label: 'L1 Cerebrum',
    description: '工作记忆 — 当前会话的即时知识存储',
    icon: <Brain className="h-4 w-4" />,
  },
  {
    key: 'l2_mem0',
    label: 'L2 Mem0',
    description: '语义记忆 — 向量搜索的长期用户偏好与事实',
    icon: <Activity className="h-4 w-4" />,
  },
  {
    key: 'l3_knowledge',
    label: 'L3 KnowledgeBase',
    description: '情景记忆 — 文档索引与知识库内容',
    icon: <Database className="h-4 w-4" />,
  },
];

// ── Component ────────────────────────────────────────────────────────────────

export function MemoryHealthPanel() {
  const { t } = useTranslation();
  const [health, setHealth] = useState<MemoryHealth | null>(null);
  const [loading, setLoading] = useState(true);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    try {
      const h = await contextApi.getMemoryHealth();
      setHealth(h);
    } catch {
      // Silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadHealth();
  }, [loadHealth]);

  // ── Derived ─────────────────────────────────────────────────────────────

  const activeCount = health
    ? (health.l1_cerebrum ? 1 : 0) + (health.l2_mem0 ? 1 : 0) + (health.l3_knowledge ? 1 : 0)
    : 0;

  const totalLayers = 3;
  const healthPercent = Math.round((activeCount / totalLayers) * 100);

  const overallStatus = activeCount === totalLayers
    ? 'healthy'
    : activeCount === 0
      ? 'offline'
      : 'degraded';

  const statusConfig = {
    healthy: {
      icon: <CheckCircle2 className="h-5 w-5 text-green-500" />,
      label: '全部在线',
      variant: 'default' as const,
    },
    degraded: {
      icon: <AlertCircle className="h-5 w-5 text-yellow-500" />,
      label: '部分降级',
      variant: 'secondary' as const,
    },
    offline: {
      icon: <XCircle className="h-5 w-5 text-red-500" />,
      label: '全部离线',
      variant: 'destructive' as const,
    },
  };

  const status = statusConfig[overallStatus];

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Layers className="h-4 w-4" />
            {t('context.memoryHealth') || '记忆系统健康'}
          </CardTitle>
          <Button variant="ghost" size="icon-sm" onClick={loadHealth} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-6">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : health ? (
          <div className="space-y-4">
            {/* Overall Status */}
            <div className="flex items-center gap-3">
              {status.icon}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-medium">{status.label}</span>
                  <Badge variant={status.variant} className="text-xs">
                    {activeCount}/{totalLayers}
                  </Badge>
                </div>
                <Progress value={healthPercent} className="h-2" />
              </div>
            </div>

            {/* Per-layer Status */}
            <div className="space-y-2">
              {LAYERS.map((layer) => (
                <div
                  key={layer.key}
                  className="flex items-center gap-3 rounded-lg border p-2.5"
                >
                  <div className="flex-shrink-0 text-muted-foreground">
                    {layer.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{layer.label}</span>
                      {health[layer.key] ? (
                        <Badge variant="outline" className="text-xs text-green-600 border-green-300 bg-green-50">
                          <CheckCircle2 className="mr-0.5 h-3 w-3" />
                          在线
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs text-red-600 border-red-300 bg-red-50">
                          <XCircle className="mr-0.5 h-3 w-3" />
                          离线
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {layer.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground text-center py-4">
            无法获取记忆系统状态
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default MemoryHealthPanel;