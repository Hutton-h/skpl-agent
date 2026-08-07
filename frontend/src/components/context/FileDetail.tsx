/**
 * FileDetail — 文件详情面板
 *
 * 显示选中文件的完整符号列表，头部显示文件路径、语言、符号数量。
 * 符号列表按行号排序，点击可高亮选中。
 */
import {
  FileCode,
  Code2,
  FunctionSquare,
  Box,
  Variable,
  Layers,
  Hash,
  ArrowUpDown,
} from 'lucide-react';
import { useMemo, useState, useCallback } from 'react';

import type { SymbolEntry } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';

interface FileDetailProps {
  filePath: string;
  sessionId: string;
  /** 从父组件传入的符号列表（可选），用于按需展示而不调用 API */
  symbols?: SymbolEntry[];
}

/** 根据 kind 返回对应的图标 */
function kindIcon(kind: string) {
  switch (kind) {
    case 'function':
      return <FunctionSquare className="h-3.5 w-3.5 text-blue-500 shrink-0" />;
    case 'method':
      return <FunctionSquare className="h-3.5 w-3.5 text-purple-500 shrink-0" />;
    case 'class':
      return <Box className="h-3.5 w-3.5 text-amber-500 shrink-0" />;
    case 'variable':
      return <Variable className="h-3.5 w-3.5 text-green-500 shrink-0" />;
    case 'interface':
      return <Layers className="h-3.5 w-3.5 text-cyan-500 shrink-0" />;
    case 'module':
      return <Code2 className="h-3.5 w-3.5 text-orange-500 shrink-0" />;
    default:
      return <Hash className="h-3.5 w-3.5 text-muted-foreground shrink-0" />;
  }
}

/** 语言对应的颜色映射 */
function languageColor(language: string): string {
  const colors: Record<string, string> = {
    typescript: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
    javascript: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
    python: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
    rust: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    go: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
    java: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    cpp: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
    c: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
  };
  return colors[language.toLowerCase()] || 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400';
}

/** 提取文件名 */
function fileName(fullPath: string): string {
  const parts = fullPath.replace(/\\/g, '/').split('/');
  return parts[parts.length - 1] || fullPath;
}

export function FileDetail({ filePath, sessionId: _sessionId, symbols = [] }: FileDetailProps) {
  const { t } = useTranslation();
  const [highlightedSymbolId, setHighlightedSymbolId] = useState<string | null>(null);
  const [sortAsc, setSortAsc] = useState(true);

  /** 过滤属于当前文件的符号 */
  const fileSymbols = useMemo(() => {
    return symbols.filter((s) => s.file_path === filePath);
  }, [symbols, filePath]);

  /** 按行号排序 */
  const sortedSymbols = useMemo(() => {
    return [...fileSymbols].sort((a, b) =>
      sortAsc ? a.line_start - b.line_start : b.line_start - a.line_start,
    );
  }, [fileSymbols, sortAsc]);

  /** 推断语言（取第一个符号的 language，或从扩展名推断） */
  const language = useMemo(() => {
    if (fileSymbols.length > 0) {
      return fileSymbols[0].language;
    }
    const ext = filePath.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      ts: 'typescript',
      tsx: 'typescript',
      js: 'javascript',
      jsx: 'javascript',
      py: 'python',
      rs: 'rust',
      go: 'go',
      java: 'java',
      cpp: 'cpp',
      c: 'c',
      h: 'c',
    };
    return langMap[ext || ''] || 'unknown';
  }, [fileSymbols, filePath]);

  const handleSymbolClick = useCallback((symbol: SymbolEntry) => {
    setHighlightedSymbolId((prev) => (prev === symbol.id ? null : symbol.id));
  }, []);

  const toggleSort = useCallback(() => {
    setSortAsc((prev) => !prev);
  }, []);

  const fname = fileName(filePath);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2 min-w-0">
            <FileCode className="h-4 w-4 text-blue-500 shrink-0" />
            <span className="truncate">{fname}</span>
          </CardTitle>
          <Badge variant="secondary" className="text-xs shrink-0">
            {fileSymbols.length} symbols
          </Badge>
        </div>

        {/* File path & language */}
        <div className="flex items-center gap-2 mt-1.5">
          <span className="text-xs text-muted-foreground truncate flex-1">
            {filePath}
          </span>
          <Badge
            variant="outline"
            className={`text-[10px] h-5 px-1.5 shrink-0 ${languageColor(language)}`}
          >
            {language}
          </Badge>
        </div>
      </CardHeader>
      <Separator />

      {/* Sort toggle */}
      <div className="px-3 py-1.5 flex items-center gap-2 border-b">
        <button
          type="button"
          className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
          onClick={toggleSort}
        >
          <ArrowUpDown className="h-3 w-3" />
          <span>Line {sortAsc ? 'ascending' : 'descending'}</span>
        </button>
      </div>

      <CardContent className="flex-1 p-0 overflow-hidden">
        {sortedSymbols.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
            <FileCode className="h-8 w-8" />
            <p className="text-sm">{t('context.noSymbolsInFile')}</p>
            {symbols.length === 0 && (
              <p className="text-xs">{t('context.noSymbolsInFileHint')}</p>
            )}
          </div>
        ) : (
          <ScrollArea className="h-full">
            <div>
              {sortedSymbols.map((sym) => (
                <button
                  key={sym.id}
                  type="button"
                  className={`w-full text-left px-3 py-2 border-b last:border-b-0 hover:bg-muted/50 transition-colors ${
                    highlightedSymbolId === sym.id ? 'bg-accent ring-1 ring-primary/20' : ''
                  }`}
                  onClick={() => handleSymbolClick(sym)}
                >
                  {/* Row 1: icon + name + kind + line */}
                  <div className="flex items-center gap-2">
                    {kindIcon(sym.kind)}
                    <span className="font-mono font-medium text-sm truncate flex-1">
                      {sym.name}
                    </span>
                    <Badge variant="secondary" className="text-[10px] h-4 px-1 shrink-0 capitalize">
                      {sym.kind}
                    </Badge>
                    <span className="text-xs text-muted-foreground tabular-nums shrink-0">
                      L{sym.line_start}{sym.line_end > sym.line_start ? `-${sym.line_end}` : ''}
                    </span>
                  </div>

                  {/* Row 2: signature */}
                  {sym.signature && (
                    <div className="mt-1 pl-5.5">
                      <code className="text-xs font-mono text-muted-foreground break-all line-clamp-2">
                        {sym.signature}
                      </code>
                    </div>
                  )}

                  {/* Row 3: description */}
                  {sym.description && (
                    <div className="mt-0.5 pl-5.5">
                      <p className="text-xs text-muted-foreground/70 line-clamp-2">
                        {sym.description}
                      </p>
                    </div>
                  )}

                  {/* Extra info: parent + exported */}
                  <div className="flex items-center gap-2 mt-1 pl-5.5">
                    {sym.parent && (
                      <span className="text-[10px] text-muted-foreground/60">
                        in {sym.parent}
                      </span>
                    )}
                    {sym.is_exported && (
                      <Badge
                        variant="outline"
                        className="text-[10px] h-4 px-1 border-green-500/30 text-green-600"
                      >
                        exported
                      </Badge>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}

export default FileDetail;