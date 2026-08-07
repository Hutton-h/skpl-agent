/**
 * SymbolIndex — 符号索引面板
 *
 * 按 kind 分组显示符号，支持折叠展开，显示数量统计。
 * 增强现有符号搜索功能，嵌入 Context 页面的 Symbols Tab 中。
 */
import {
  ChevronDown,
  ChevronRight,
  Code2,
  Box,
  FunctionSquare,
  Variable,
  Layers,
  Hash,
} from 'lucide-react';
import { useMemo, useState, useCallback } from 'react';

import type { SymbolEntry } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface SymbolIndexProps {
  sessionId: string;
  symbols: SymbolEntry[];
  onSelect?: (symbol: SymbolEntry) => void;
}

/** 按 kind 分组后的结构 */
interface KindGroup {
  kind: string;
  symbols: SymbolEntry[];
  count: number;
}

/** 根据 kind 返回对应的图标 */
function kindIcon(kind: string) {
  switch (kind) {
    case 'function':
      return <FunctionSquare className="h-3.5 w-3.5 text-blue-500" />;
    case 'method':
      return <FunctionSquare className="h-3.5 w-3.5 text-purple-500" />;
    case 'class':
      return <Box className="h-3.5 w-3.5 text-amber-500" />;
    case 'variable':
      return <Variable className="h-3.5 w-3.5 text-green-500" />;
    case 'interface':
      return <Layers className="h-3.5 w-3.5 text-cyan-500" />;
    case 'module':
      return <Code2 className="h-3.5 w-3.5 text-orange-500" />;
    default:
      return <Hash className="h-3.5 w-3.5 text-muted-foreground" />;
  }
}

export function SymbolIndex({ sessionId: _sessionId, symbols, onSelect }: SymbolIndexProps) {
  const { t } = useTranslation();
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());
  const [selectedSymbolId, setSelectedSymbolId] = useState<string | null>(null);

  /** 按 kind 分组，各组内按 name 排序 */
  const groups = useMemo<KindGroup[]>(() => {
    const map = new Map<string, SymbolEntry[]>();
    for (const sym of symbols) {
      const list = map.get(sym.kind) || [];
      list.push(sym);
      map.set(sym.kind, list);
    }
    const result: KindGroup[] = [];
    for (const [kind, list] of map) {
      list.sort((a, b) => a.name.localeCompare(b.name));
      result.push({ kind, symbols: list, count: list.length });
    }
    // 按数量降序排列
    result.sort((a, b) => b.count - a.count);
    return result;
  }, [symbols]);

  const toggleGroup = useCallback((kind: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) {
        next.delete(kind);
      } else {
        next.add(kind);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (symbol: SymbolEntry) => {
      setSelectedSymbolId(symbol.id);
      onSelect?.(symbol);
    },
    [onSelect],
  );

  const totalSymbols = symbols.length;
  const totalKinds = groups.length;

  if (symbols.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Code2 className="h-4 w-4" />
            Symbol Index
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
            <Code2 className="h-6 w-6" />
            <p className="text-sm">{t('context.noSymbolsIndexed')}</p>
            <p className="text-xs">{t('context.noSymbolsIndexedHint')}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Code2 className="h-4 w-4" />
            Symbol Index
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {totalSymbols} symbols
            </Badge>
            <Badge variant="outline" className="text-xs">
              {totalKinds} kinds
            </Badge>
          </div>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-0">
            {groups.map((group) => {
              const isCollapsed = collapsedGroups.has(group.kind);
              return (
                <div key={group.kind} className="border-b last:border-b-0">
                  {/* Group Header */}
                  <button
                    type="button"
                    className="flex items-center gap-2 w-full px-3 py-2 text-left hover:bg-muted/50 transition-colors"
                    onClick={() => toggleGroup(group.kind)}
                  >
                    {isCollapsed ? (
                      <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                    ) : (
                      <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                    )}
                    {kindIcon(group.kind)}
                    <span className="text-sm font-medium capitalize">
                      {group.kind}
                    </span>
                    <Badge variant="secondary" className="ml-auto text-[10px] h-4 px-1.5">
                      {group.count}
                    </Badge>
                  </button>

                  {/* Symbol List */}
                  {!isCollapsed && (
                    <div>
                      {group.symbols.map((sym) => (
                        <button
                          key={sym.id}
                          type="button"
                          className={`flex items-center gap-2 w-full pl-10 pr-3 py-1.5 text-left text-xs hover:bg-muted/50 transition-colors ${
                            selectedSymbolId === sym.id ? 'bg-accent' : ''
                          }`}
                          onClick={() => handleSelect(sym)}
                          title={sym.signature ?? sym.name}
                        >
                          <span className="font-mono font-medium truncate flex-1">
                            {sym.name}
                          </span>
                          {sym.parent && (
                            <span className="text-muted-foreground truncate max-w-[120px]">
                              {sym.parent}
                            </span>
                          )}
                          <span className="text-muted-foreground tabular-nums shrink-0">
                            L{sym.line_start}
                          </span>
                          {sym.is_exported && (
                            <Badge
                              variant="outline"
                              className="text-[10px] h-4 px-1 shrink-0 border-green-500/30 text-green-600"
                            >
                              export
                            </Badge>
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default SymbolIndex;