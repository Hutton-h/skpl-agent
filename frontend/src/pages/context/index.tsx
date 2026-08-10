/**
 * Context Management Page — 上下文管理页面
 *
 * 功能:
 * - 项目解剖扫描 (Anatomy Scan)
 * - 符号搜索 (Symbol Search)
 * - 符号浏览 (TreeView + SymbolIndex + FileDetail)
 * - Token 使用追踪 + Token 估算
 * - 记忆管理 (Cerebrum)
 */
import {
  Brain,
  CheckCircle2,
  Clock,
  Code2,
  FolderTree,
  Layers,
  Loader2,
  Play,
  RefreshCw,
  Search,
  XCircle,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from '@/i18n/useI18n';

import { contextApi } from '@/api';
import type {
  AnatomyStats,
  ScanStatus,
  SymbolEntry,
} from '@/api/context';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { CerebrumPanel } from '@/components/context/CerebrumPanel';
import { MemoryHealthPanel } from '@/components/context/MemoryHealthPanel';
import { SessionSummary } from '@/components/context/SessionSummary';
import { TokenLedger } from '@/components/context/TokenLedger';
import { WasteDetector } from '@/components/context/WasteDetector';
import { TokenEstimate } from '@/components/context/TokenEstimate';
import { SymbolIndex } from '@/components/context/SymbolIndex';
import { TreeView } from '@/components/context/TreeView';
import { FileDetail } from '@/components/context/FileDetail';
// ── Scan Status Badge ───────────────────────────────────────────────────────

function ScanStatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  const variants: Record<string, { icon: React.ReactNode; label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
    queued: { icon: <Clock className="h-3 w-3" />, label: t('context.queued'), variant: 'secondary' },
    running: { icon: <Loader2 className="h-3 w-3 animate-spin" />, label: t('common.running'), variant: 'default' },
    completed: { icon: <CheckCircle2 className="h-3 w-3" />, label: t('common.completed'), variant: 'outline' },
    failed: { icon: <XCircle className="h-3 w-3" />, label: t('common.failed'), variant: 'destructive' },
  };
  const v = variants[status] ?? variants.queued;
  return (
    <Badge variant={v.variant} className="gap-1">
      {v.icon} {v.label}
    </Badge>
  );
}

// ── Symbol Kind Badge ───────────────────────────────────────────────────────

function KindBadge({ kind, language }: { kind: string; language: string }) {
  const colors: Record<string, string> = {
    function: 'bg-blue-100 text-blue-800',
    class: 'bg-purple-100 text-purple-800',
    method: 'bg-cyan-100 text-cyan-800',
    variable: 'bg-green-100 text-green-800',
    interface: 'bg-orange-100 text-orange-800',
    type: 'bg-pink-100 text-pink-800',
    module: 'bg-yellow-100 text-yellow-800',
  };
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium ${colors[kind] ?? 'bg-gray-100 text-gray-800'}`}>
      {language} {kind}
    </span>
  );
}

// ── Main Page ───────────────────────────────────────────────────────────────

export function ContextPage() {
  const { t } = useTranslation();
  const [sessionId] = useState(() => localStorage.getItem('active_session_id') || '');

  // Scan state
  const [scanStatus, setScanStatus] = useState<ScanStatus | null>(null);
  const [scanning, setScanning] = useState(false);

  // Symbol search
  const [searchQuery, setSearchQuery] = useState('');
  const [symbols, setSymbols] = useState<SymbolEntry[]>([]);
  const [searching, setSearching] = useState(false);

  // Browse mode
  const [symbolsMode, setSymbolsMode] = useState<'search' | 'browse'>('search');
  const [browseSymbols, setBrowseSymbols] = useState<SymbolEntry[]>([]);
  const [browseLoading, setBrowseLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [_selectedSymbol, setSelectedSymbol] = useState<SymbolEntry | null>(null);

  // Anatomy stats
  const [anatomyStats, setAnatomyStats] = useState<AnatomyStats | null>(null);
  const [anatomyLoading, setAnatomyLoading] = useState(true);

  // ── Scan ──────────────────────────────────────────────────────────────────

  const handleStartScan = async () => {
    setScanning(true);
    try {
      const result = await contextApi.startScan(sessionId, {
        root_path: '.',
        mode: 'full',
      });
      setScanStatus(result);

      // Poll for completion
      const poll = setInterval(async () => {
        try {
          const status = await contextApi.getScanStatus(sessionId, result.task_id);
          setScanStatus(status);
          if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(poll);
            setScanning(false);
            // Reload stats
            const stats = await contextApi.getAnatomyStats(sessionId);
            setAnatomyStats(stats);
          }
        } catch {
          clearInterval(poll);
          setScanning(false);
        }
      }, 2000);
    } catch {
      setScanning(false);
    }
  };

  // ── Symbol Search ─────────────────────────────────────────────────────────

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const results = await contextApi.searchSymbols(sessionId, {
        query: searchQuery,
        limit: 50,
      });
      setSymbols(results);
    } catch {
      setSymbols([]);
    } finally {
      setSearching(false);
    }
  };

  // ── Load Anatomy Stats ────────────────────────────────────────────────────

  const loadAnatomyStats = async () => {
    try {
      const stats = await contextApi.getAnatomyStats(sessionId);
      setAnatomyStats(stats);
    } catch {
      // Silent
    } finally {
      setAnatomyLoading(false);
    }
  };

  useEffect(() => {
    if (!sessionId) {
      setAnatomyLoading(false);
      return;
    }
    loadAnatomyStats();
  }, [sessionId]);

  // ── Browse Symbols ─────────────────────────────────────────────────────────

  const loadBrowseSymbols = useCallback(async () => {
    setBrowseLoading(true);
    try {
      // Use search with empty query to fetch all indexed symbols
      const results = await contextApi.searchSymbols(sessionId, {
        query: '',
        limit: 500,
      });
      setBrowseSymbols(results);
    } catch {
      setBrowseSymbols([]);
    } finally {
      setBrowseLoading(false);
    }
  }, [sessionId]);

  const handleSelectFile = useCallback((filePath: string) => {
    setSelectedFile(filePath);
    setSelectedSymbol(null);
  }, []);

  const handleSelectSymbol = useCallback((symbol: SymbolEntry) => {
    setSelectedSymbol(symbol);
  }, []);

  // Filter symbols for the selected file in FileDetail
  const fileDetailSymbols = useMemo(() => {
    if (!selectedFile) return [];
    return browseSymbols.filter((s) => s.file_path === selectedFile);
  }, [browseSymbols, selectedFile]);

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col gap-6 p-6">
      {!sessionId && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardContent className="flex flex-col items-center gap-2 py-8">
            <FolderTree className="h-8 w-8 text-amber-500" />
            <p className="text-sm text-muted-foreground text-center">
              {t('context.noSessionSelected') || 'No active session selected. Please open a chat session first to view context.'}
            </p>
          </CardContent>
        </Card>
      )}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            {t('context.title')}
          </h1>
          <p className="text-muted-foreground mt-1">
            {t('context.subtitle')}
          </p>
        </div>
        <Button onClick={handleStartScan} disabled={scanning}>
          {scanning ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Play className="mr-2 h-4 w-4" />
          )}
          {scanning ? t('context.scanning') : t('context.scanProject')}
        </Button>
      </div>

      {/* Scan Status */}
      {scanStatus && (
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center gap-3">
              <ScanStatusBadge status={scanStatus.status} />
              <span className="text-sm text-muted-foreground">
                {t('context.task')}: {scanStatus.task_id}
              </span>
              {scanStatus.result && (
                <>
                  <Separator orientation="vertical" className="h-4" />
                  <span className="text-sm">
                    {scanStatus.result.files_scanned} {t('context.files')},{' '}
                    {scanStatus.result.symbols_extracted} {t('context.symbols')} {t('context.in')}{' '}
                    {scanStatus.result.duration_seconds.toFixed(1)}s
                  </span>
                </>
              )}
              {scanStatus.error && (
                <span className="text-sm text-destructive">{scanStatus.error}</span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Session Summary */}
      <SessionSummary sessionId={sessionId} />

      <Tabs defaultValue="anatomy">
        <TabsList>
          <TabsTrigger value="anatomy">
            <Code2 className="mr-1 h-4 w-4" /> {t('context.anatomy')}
          </TabsTrigger>
          <TabsTrigger value="symbols">
            <Search className="mr-1 h-4 w-4" /> {t('context.symbols')}
          </TabsTrigger>
          <TabsTrigger value="tokens">
            <RefreshCw className="mr-1 h-4 w-4" /> {t('context.tokens')}
          </TabsTrigger>
          <TabsTrigger value="memory">
            <Brain className="mr-1 h-4 w-4" /> {t('context.memory')}
          </TabsTrigger>
        </TabsList>

        {/* Anatomy Tab */}
        <TabsContent value="anatomy" className="mt-4">
          {anatomyLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-1/2" />
              <Skeleton className="h-4 w-1/3" />
            </div>
          ) : anatomyStats ? (
            <div className="grid gap-4 md:grid-cols-3">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('context.totalSymbols')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {anatomyStats.total_symbols.toLocaleString()}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('context.files')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {anatomyStats.total_files.toLocaleString()}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('context.languages')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {Object.keys(anatomyStats.languages ?? {}).length}
                  </div>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {Object.entries(anatomyStats.languages ?? {})
                      .slice(0, 5)
                      .map(([lang, count]) => (
                        <Badge key={lang} variant="secondary" className="text-xs">
                          {lang} ({count})
                        </Badge>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              {t('context.noAnatomyData')}
            </p>
          )}
        </TabsContent>

        {/* Symbols Tab */}
        <TabsContent value="symbols" className="mt-4">
          {/* Mode toggle */}
          <div className="flex items-center gap-2 mb-4">
            <Button
              variant={symbolsMode === 'search' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setSymbolsMode('search')}
            >
              <Search className="mr-1 h-4 w-4" /> {t('context.search')}
            </Button>
            <Button
              variant={symbolsMode === 'browse' ? 'default' : 'outline'}
              size="sm"
              onClick={() => {
                setSymbolsMode('browse');
                if (browseSymbols.length === 0) loadBrowseSymbols();
              }}
            >
              <FolderTree className="mr-1 h-4 w-4" /> {t('context.browse')}
            </Button>
          </div>

          {/* Search Mode */}
          {symbolsMode === 'search' && (
            <>
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder={t('context.searchSymbols')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                />
                <Button onClick={handleSearch} disabled={searching}>
                  {searching ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                </Button>
              </div>

              {symbols.length > 0 && (
                <div className="rounded-lg border">
                  <div className="grid grid-cols-[auto_1fr_auto] gap-3 p-3 text-xs font-medium text-muted-foreground border-b">
                    <span>{t('context.kind')}</span>
                    <span>{t('context.nameSignature')}</span>
                    <span>{t('context.file')}</span>
                  </div>
                  {symbols.map((sym) => (
                    <div
                      key={sym.id}
                      className="grid grid-cols-[auto_1fr_auto] gap-3 p-3 text-sm border-b last:border-0 hover:bg-muted/50"
                    >
                      <KindBadge kind={sym.kind} language={sym.language} />
                      <div>
                        <span className="font-medium font-mono">{sym.name}</span>
                        {sym.signature && (
                          <span className="text-muted-foreground ml-1 font-mono text-xs">
                            {sym.signature}
                          </span>
                        )}
                        {sym.is_exported && (
                          <Badge variant="outline" className="ml-1 text-[10px]">
                            {t('context.export')}
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground font-mono truncate max-w-[200px]">
                        {sym.file_path}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {symbols.length === 0 && !searching && (
                <p className="text-sm text-muted-foreground">
                  {t('context.searchToExplore')}
                </p>
              )}
            </>
          )}

          {/* Browse Mode */}
          {symbolsMode === 'browse' && (
            <>
              {browseLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : browseSymbols.length === 0 ? (
                <div className="flex flex-col items-center gap-3 py-12 text-muted-foreground">
                  <FolderTree className="h-8 w-8" />
                  <p className="text-sm">{t('context.noSymbolsLoaded')}</p>
                  <Button variant="outline" size="sm" onClick={loadBrowseSymbols}>
                    <Play className="mr-1 h-4 w-4" /> {t('context.loadSymbols')}
                  </Button>
                </div>
              ) : (
                <div className="grid gap-4 lg:grid-cols-[280px_minmax(0,1fr)_minmax(0,1fr)]">
                  {/* Left: TreeView */}
                  <div className="h-[calc(100vh-380px)] min-h-[400px]">
                    <TreeView
                      sessionId={sessionId}
                      symbols={browseSymbols}
                      onSelectFile={handleSelectFile}
                    />
                  </div>

                  {/* Middle: SymbolIndex */}
                  <div className="h-[calc(100vh-380px)] min-h-[400px]">
                    <SymbolIndex
                      sessionId={sessionId}
                      symbols={selectedFile ? fileDetailSymbols : browseSymbols}
                      onSelect={handleSelectSymbol}
                    />
                  </div>

                  {/* Right: FileDetail (when a file is selected) */}
                  <div className="h-[calc(100vh-380px)] min-h-[400px]">
                    {selectedFile ? (
                      <FileDetail
                        filePath={selectedFile}
                        sessionId={sessionId}
                        symbols={browseSymbols}
                      />
                    ) : (
                      <Card className="h-full flex items-center justify-center">
                        <CardContent className="text-center py-8">
                          <Layers className="h-8 w-8 text-muted-foreground/50 mx-auto mb-2" />
                          <p className="text-sm text-muted-foreground">
                            {t('context.selectFileHint')}
                          </p>
                        </CardContent>
                      </Card>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* Tokens Tab */}
        <TabsContent value="tokens" className="mt-4">
          <div className="space-y-4">
            <TokenLedger sessionId={sessionId} />
            <WasteDetector sessionId={sessionId} />
            <TokenEstimate />
          </div>
        </TabsContent>

        {/* Memory Tab */}
        <TabsContent value="memory" className="mt-4">
          <div className="space-y-4">
            <MemoryHealthPanel />
            <CerebrumPanel sessionId={sessionId} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default ContextPage;