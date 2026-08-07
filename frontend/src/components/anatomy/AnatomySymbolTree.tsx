/**
 * AnatomySymbolTree — 项目符号树组件
 *
 * 以树形结构展示项目解剖中的符号，支持按语言/类型筛选。
 */
import {
  ChevronRight,
  Code2,
  FileCode,
  FolderOpen,
  FunctionSquare,
  Box,
  Variable,
  Layers,
  Search,
} from 'lucide-react';
import { useState, useMemo } from 'react';

import type { SymbolEntry } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface SymbolTreeProps {
  symbols: SymbolEntry[];
  loading?: boolean;
  onSelect?: (symbol: SymbolEntry) => void;
}

interface TreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children: TreeNode[];
  symbols: SymbolEntry[];
}

function buildTree(symbols: SymbolEntry[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const sym of symbols) {
    const parts = sym.file_path.split('/');
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const fullPath = parts.slice(0, i + 1).join('/');

      let node = current.find((n) => n.name === part);
      if (!node) {
        node = {
          name: part,
          path: fullPath,
          isDirectory: !isLast,
          children: [],
          symbols: [],
        };
        current.push(node);
      }

      if (isLast) {
        node.symbols.push(sym);
      }
      current = node.children;
    }
  }

  return root;
}

function TreeNodeRow({
  node,
  depth,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  onSelect?: (symbol: SymbolEntry) => void;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  const kindIcon = (kind: string) => {
    switch (kind) {
      case 'function':
      case 'method':
        return <FunctionSquare className="h-3 w-3" />;
      case 'class':
        return <Box className="h-3 w-3" />;
      case 'variable':
        return <Variable className="h-3 w-3" />;
      case 'module':
        return <Layers className="h-3 w-3" />;
      default:
        return <Code2 className="h-3 w-3" />;
    }
  };

  return (
    <div>
      {/* Directory / File Row */}
      <button
        className="flex items-center gap-1 w-full px-1 py-0.5 text-left text-sm hover:bg-muted/50 rounded"
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={() => setExpanded(!expanded)}
      >
        <ChevronRight
          className={`h-3 w-3 shrink-0 transition-transform ${expanded ? 'rotate-90' : ''}`}
        />
        {node.isDirectory ? (
          <FolderOpen className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
        ) : (
          <FileCode className="h-3.5 w-3.5 text-blue-500 shrink-0" />
        )}
        <span className="truncate text-xs ml-1">{node.name}</span>
        {node.symbols.length > 0 && (
          <Badge variant="secondary" className="ml-auto text-[10px] h-4 px-1">
            {node.symbols.length}
          </Badge>
        )}
      </button>

      {/* Symbols & Children */}
      {expanded && (
        <div>
          {node.symbols.map((sym) => (
            <button
              key={sym.id}
              className="flex items-center gap-1 w-full px-1 py-0.5 text-left text-xs hover:bg-muted/50 rounded"
              style={{ paddingLeft: `${(depth + 1) * 16 + 4}px` }}
              onClick={() => onSelect?.(sym)}
            >
              {kindIcon(sym.kind)}
              <span className="font-mono font-medium truncate">{sym.name}</span>
              <Badge variant="outline" className="ml-auto text-[10px] h-4 px-1">
                {sym.kind}
              </Badge>
            </button>
          ))}
          {node.children.map((child) => (
            <TreeNodeRow
              key={child.path}
              node={child}
              depth={depth + 1}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function AnatomySymbolTree({ symbols, loading, onSelect }: SymbolTreeProps) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState('');
  const [kindFilter, setKindFilter] = useState<string | null>(null);

  const filteredSymbols = useMemo(() => {
    let result = symbols;
    if (filter) {
      const q = filter.toLowerCase();
      result = result.filter(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          s.file_path.toLowerCase().includes(q) ||
          (s.signature ?? '').toLowerCase().includes(q),
      );
    }
    if (kindFilter) {
      result = result.filter((s) => s.kind === kindFilter);
    }
    return result;
  }, [symbols, filter, kindFilter]);

  const kinds = useMemo(() => {
    const set = new Set(symbols.map((s) => s.kind));
    return Array.from(set).sort();
  }, [symbols]);

  const filteredTree = useMemo(() => buildTree(filteredSymbols), [filteredSymbols]);

  return (
    <div className="flex flex-col gap-2">
      {/* Search & Filter */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder={t('context.searchSymbols')}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="pl-7 h-8 text-sm"
          />
        </div>
        <div className="flex gap-1">
          <Button
            variant={kindFilter === null ? 'secondary' : 'ghost'}
            size="sm"
            className="h-8 text-xs"
            onClick={() => setKindFilter(null)}
          >
            All
          </Button>
          {kinds.slice(0, 5).map((kind) => (
            <Button
              key={kind}
              variant={kindFilter === kind ? 'secondary' : 'ghost'}
              size="sm"
              className="h-8 text-xs"
              onClick={() => setKindFilter(kind === kindFilter ? null : kind)}
            >
              {kind}
            </Button>
          ))}
        </div>
      </div>

      {/* Tree */}
      <div className="rounded-lg border max-h-[500px] overflow-y-auto">
        {loading ? (
          <div className="p-4 text-sm text-muted-foreground">{t('common.loading')}</div>
        ) : filteredTree.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-8">
            <Code2 className="h-6 w-6 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">{t('context.noSymbolsLoaded')}</p>
          </div>
        ) : (
          <div className="p-2">
            {filteredTree.map((node) => (
              <TreeNodeRow
                key={node.path}
                node={node}
                depth={0}
                onSelect={onSelect}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default AnatomySymbolTree;