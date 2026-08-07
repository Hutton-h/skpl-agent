/**
 * CerebrumPanel — 记忆管理面板
 *
 * 提供完整的 Cerebrum 记忆管理功能：
 * - 记忆统计卡片（总数、分类分布）
 * - 按 key 搜索/召回记忆
 * - 添加新记忆表单
 * - 记忆列表展示（含删除、置信度进度条等）
 * - 每 10 秒自动刷新统计数据
 */
import {
  BarChart3,
  Brain,
  Clock,
  Hash,
  Loader2,
  Plus,
  RefreshCw,
  Search,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { contextApi } from '@/api';
import type { MemoryEntry, MemoryStats } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Separator } from '@/components/ui/separator';
import { toast } from 'sonner';

// ── Constants ────────────────────────────────────────────────────────────────

const CATEGORIES = [
  'general',
  'code',
  'decision',
  'fact',
  'preference',
  'todo',
  'bug',
  'note',
] as const;

const CATEGORY_COLORS: Record<string, string> = {
  general: 'bg-gray-100 text-gray-800',
  code: 'bg-blue-100 text-blue-800',
  decision: 'bg-purple-100 text-purple-800',
  fact: 'bg-green-100 text-green-800',
  preference: 'bg-orange-100 text-orange-800',
  todo: 'bg-yellow-100 text-yellow-800',
  bug: 'bg-red-100 text-red-800',
  note: 'bg-cyan-100 text-cyan-800',
};

const AUTO_REFRESH_INTERVAL = 10_000; // 10 seconds

// ── Props ────────────────────────────────────────────────────────────────────

interface CerebrumPanelProps {
  sessionId: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function truncateValue(value: string, maxLen = 80): string {
  if (value.length <= maxLen) return value;
  return value.slice(0, maxLen) + '...';
}

function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return 'N/A';
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function getCategoryBadgeClass(category: string): string {
  return CATEGORY_COLORS[category] ?? 'bg-gray-100 text-gray-800';
}

// ── Component ────────────────────────────────────────────────────────────────

export function CerebrumPanel({ sessionId }: CerebrumPanelProps) {
  const { t } = useTranslation();
  // Stats
  const [stats, setStats] = useState<MemoryStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);

  // Search
  const [searchKey, setSearchKey] = useState('');
  const [searching, setSearching] = useState(false);

  // Add form
  const [formKey, setFormKey] = useState('');
  const [formValue, setFormValue] = useState('');
  const [formCategory, setFormCategory] = useState('general');
  const [formConfidence, setFormConfidence] = useState(0.8);
  const [adding, setAdding] = useState(false);

  // Memory list (local state — keyed by memory key to avoid duplicates)
  const [memories, setMemories] = useState<Map<string, MemoryEntry>>(new Map());
  const [deletingKeys, setDeletingKeys] = useState<Set<string>>(new Set());

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load Stats ──────────────────────────────────────────────────────────

  const loadStats = useCallback(async () => {
    try {
      const s = await contextApi.getMemoryStats(sessionId);
      setStats(s);
    } catch {
      // Stats load failure is non-critical; silently ignore
    } finally {
      setStatsLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  // ── Load all memories on mount ──────────────────────────────────────────

  const [memoriesLoading, setMemoriesLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const loadAll = async () => {
      setMemoriesLoading(true);
      try {
        const all = await contextApi.listMemories(sessionId);
        if (cancelled) return;
        const map = new Map<string, MemoryEntry>();
        for (const m of all) {
          map.set(m.key, m);
        }
        setMemories(map);
      } catch {
        // Non-critical: user can still search/add manually
      } finally {
        if (!cancelled) setMemoriesLoading(false);
      }
    };
    loadAll();
    return () => { cancelled = true; };
  }, [sessionId]);

  // ── Auto-refresh ────────────────────────────────────────────────────────

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      loadStats();
    }, AUTO_REFRESH_INTERVAL);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [loadStats]);

  // ── Search / Recall ─────────────────────────────────────────────────────

  const handleSearch = async () => {
    const key = searchKey.trim();
    if (!key) return;
    setSearching(true);
    try {
      const entry = await contextApi.recall(sessionId, key);
      setMemories((prev) => {
        const next = new Map(prev);
        next.set(entry.key, entry);
        return next;
      });
      toast.success(`Memory "${key}" recalled`);
    } catch {
      toast.error(`Memory "${key}" not found`);
    } finally {
      setSearching(false);
    }
  };

  // ── Add ─────────────────────────────────────────────────────────────────

  const handleAdd = async () => {
    const key = formKey.trim();
    const value = formValue.trim();
    if (!key || !value) return;
    setAdding(true);
    try {
      const entry = await contextApi.remember(sessionId, {
        key,
        value,
        category: formCategory,
        confidence: formConfidence,
      });
      setMemories((prev) => {
        const next = new Map(prev);
        next.set(entry.key, entry);
        return next;
      });
      setFormKey('');
      setFormValue('');
      setFormCategory('general');
      setFormConfidence(0.8);
      toast.success(`Memory "${key}" saved`);
      loadStats();
    } catch {
      toast.error(t('context.saveMemoryFailed'));
    } finally {
      setAdding(false);
    }
  };

  // ── Delete ──────────────────────────────────────────────────────────────

  const handleDelete = async (key: string) => {
    setDeletingKeys((prev) => {
      const next = new Set(prev);
      next.add(key);
      return next;
    });
    try {
      await contextApi.forget(sessionId, key);
      setMemories((prev) => {
        const next = new Map(prev);
        next.delete(key);
        return next;
      });
      toast.success(`Memory "${key}" deleted`);
      loadStats();
    } catch {
      toast.error(`Failed to delete memory "${key}"`);
    } finally {
      setDeletingKeys((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    }
  };

  // ── Derived ─────────────────────────────────────────────────────────────

  const memoryList = Array.from(memories.values());

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="space-y-4">
      {/* ── Stats Cards ──────────────────────────────────────────────────── */}
      <div className="grid gap-4 md:grid-cols-3">
        {/* Total Memories */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <Brain className="h-4 w-4" /> {t('context.totalMemories')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">{t('common.loading')}</span>
              </div>
            ) : (
              <div className="text-2xl font-bold">{stats?.total_memories ?? 0}</div>
            )}
          </CardContent>
        </Card>

        {/* Categories */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <BarChart3 className="h-4 w-4" /> {t('context.categories')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {statsLoading ? (
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">{t('common.loading')}</span>
              </div>
            ) : (
              <>
                <div className="text-2xl font-bold">
                  {Object.keys(stats?.by_category ?? {}).length}
                </div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {Object.entries(stats?.by_category ?? {})
                    .slice(0, 5)
                    .map(([cat, count]) => (
                      <Badge
                        key={cat}
                        variant="secondary"
                        className={`text-xs ${getCategoryBadgeClass(cat)}`}
                      >
                        {cat} ({count})
                      </Badge>
                    ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Refresh */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2">
              <RefreshCw className="h-4 w-4" /> {t('context.autoRefresh')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {t('context.statsRefresh')}
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-2"
              onClick={loadStats}
              disabled={statsLoading}
            >
              <RefreshCw
                className={`mr-1 h-3.5 w-3.5 ${statsLoading ? 'animate-spin' : ''}`}
              />
              {t('context.refreshNow')}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* ── Search & Add ─────────────────────────────────────────────────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Recall */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Search className="h-4 w-4" /> {t('context.recallMemory')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              <Input
                placeholder={t('context.memoryKeyPlaceholder')}
                value={searchKey}
                onChange={(e) => setSearchKey(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSearch();
                }}
              />
              <Button onClick={handleSearch} disabled={searching}>
                {searching ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Search className="h-4 w-4" />
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Add Memory */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Plus className="h-4 w-4" /> {t('context.addMemory')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs">{t('context.memoryKey')}</Label>
                  <Input
                    placeholder={t('context.memoryKeyPlaceholder')}
                    value={formKey}
                    onChange={(e) => setFormKey(e.target.value)}
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">{t('context.memoryCategory')}</Label>
                  <Select value={formCategory} onValueChange={setFormCategory}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CATEGORIES.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">{t('context.memoryValue')}</Label>
                <Input
                  placeholder={t('context.memoryValuePlaceholder')}
                  value={formValue}
                  onChange={(e) => setFormValue(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">
                  {t('context.confidence')}: {(formConfidence * 100).toFixed(0)}%
                </Label>
                <Input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={formConfidence}
                  onChange={(e) => setFormConfidence(parseFloat(e.target.value))}
                />
              </div>
              <Button
                onClick={handleAdd}
                disabled={adding || !formKey.trim() || !formValue.trim()}
                className="w-full"
              >
                {adding ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="mr-2 h-4 w-4" />
                )}
                {adding ? t('common.saving') : t('context.saveMemory')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Memory List ──────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Brain className="h-4 w-4" /> {t('context.memoryList')}
            <Badge variant="secondary" className="ml-1 text-xs">
              {memoryList.length}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {memoriesLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : memoryList.length === 0 ? (
            <p className="text-sm text-muted-foreground py-8 text-center">
              {t('context.noMemoriesHint')}
            </p>
          ) : (
            <ScrollArea className="h-[400px] pr-1">
              <div className="space-y-1">
                {memoryList.map((mem, idx) => (
                  <div key={mem.key}>
                    {idx > 0 && <Separator className="my-2" />}
                    <div className="space-y-2">
                      {/* Header: key + category + delete */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-mono text-sm font-medium truncate">
                            {mem.key}
                          </span>
                          <Badge
                            variant="secondary"
                            className={`text-xs shrink-0 ${getCategoryBadgeClass(mem.category)}`}
                          >
                            {mem.category}
                          </Badge>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive shrink-0"
                          onClick={() => handleDelete(mem.key)}
                          disabled={deletingKeys.has(mem.key)}
                        >
                          {deletingKeys.has(mem.key) ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Trash2 className="h-3.5 w-3.5" />
                          )}
                        </Button>
                      </div>

                      {/* Value (truncated) */}
                      <p className="text-sm text-muted-foreground break-all">
                        {truncateValue(mem.value)}
                      </p>

                      {/* Confidence progress bar */}
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground w-16 shrink-0">
                          {t('context.confidence')}
                        </span>
                        <Progress
                          value={mem.confidence * 100}
                          className="h-2 flex-1"
                        />
                        <span className="text-xs text-muted-foreground w-10 text-right shrink-0">
                          {(mem.confidence * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Meta: access count + created time */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          {t('context.access')}: {mem.access_count}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(mem.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default CerebrumPanel;