/**
 * TreeView — 项目目录树
 *
 * 从 symbols 数据构建目录树，递归渲染目录结构。
 * 文件夹可折叠展开，文件显示图标 + 名称 + 符号数。
 * 点击文件触发 onSelectFile 回调。
 */
import {
  Folder,
  FolderOpen,
  FileCode,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';
import { useMemo, useState, useCallback } from 'react';

import type { SymbolEntry } from '@/api/context';
import { useTranslation } from '@/i18n/useI18n';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Button } from '@/components/ui/button';

interface TreeViewProps {
  sessionId: string;
  /** 通过 symbols 数据构建目录树 */
  symbols: SymbolEntry[];
  onSelectFile?: (filePath: string) => void;
}

/** 树节点 */
interface TreeNode {
  name: string;
  path: string;
  isDirectory: boolean;
  children: TreeNode[];
  symbolCount: number;
  /** 文件独有的多个语言 */
  languages?: string[];
}

/** 从 symbols 构建目录树 */
function buildTree(symbols: SymbolEntry[]): TreeNode[] {
  const root: TreeNode[] = [];

  for (const sym of symbols) {
    const parts = sym.file_path.replace(/\\/g, '/').split('/');
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
          symbolCount: 0,
          languages: isLast ? [sym.language] : undefined,
        };
        current.push(node);
      }

      if (isLast) {
        node.symbolCount += 1;
        if (node.languages && !node.languages.includes(sym.language)) {
          node.languages.push(sym.language);
        }
      }
      current = node.children;
    }
  }

  /** 递归排序：目录在前，文件在后；各自按名称字母排序 */
  function sortChildren(nodes: TreeNode[]) {
    nodes.sort((a, b) => {
      if (a.isDirectory !== b.isDirectory) {
        return a.isDirectory ? -1 : 1;
      }
      return a.name.localeCompare(b.name);
    });
    for (const node of nodes) {
      if (node.children.length > 0) {
        sortChildren(node.children);
      }
    }
  }
  sortChildren(root);

  return root;
}

/** 递归统计目录下的总符号数 */
function countTotalSymbols(node: TreeNode): number {
  if (!node.isDirectory) return node.symbolCount;
  let total = node.symbolCount;
  for (const child of node.children) {
    total += countTotalSymbols(child);
  }
  return total;
}

/** 单个树节点行 */
function TreeNodeRow({
  node,
  depth,
  onSelectFile,
  selectedFilePath,
}: {
  node: TreeNode;
  depth: number;
  onSelectFile?: (filePath: string) => void;
  selectedFilePath: string | null;
}) {
  const [expanded, setExpanded] = useState(depth < 2);

  const totalSymbols = node.isDirectory ? countTotalSymbols(node) : node.symbolCount;

  const handleClick = useCallback(() => {
    if (node.isDirectory) {
      setExpanded((prev) => !prev);
    } else {
      onSelectFile?.(node.path);
    }
  }, [node, onSelectFile]);

  const isSelected = !node.isDirectory && selectedFilePath === node.path;

  return (
    <div>
      <button
        type="button"
        className={`flex items-center gap-1 w-full px-1 py-0.5 text-left text-sm hover:bg-muted/50 rounded transition-colors ${
          isSelected ? 'bg-accent ring-1 ring-primary/20' : ''
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
        onClick={handleClick}
      >
        {/* Chevron for directories */}
        {node.isDirectory ? (
          expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          )
        ) : (
          <span className="w-3.5 shrink-0" />
        )}

        {/* Icon */}
        {node.isDirectory ? (
          expanded ? (
            <FolderOpen className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
          ) : (
            <Folder className="h-3.5 w-3.5 text-yellow-500 shrink-0" />
          )
        ) : (
          <FileCode className="h-3.5 w-3.5 text-blue-500 shrink-0" />
        )}

        {/* Name */}
        <span className="truncate text-xs ml-1">{node.name}</span>

        {/* Symbol count badge */}
        {totalSymbols > 0 && (
          <Badge variant="secondary" className="ml-auto text-[10px] h-4 px-1 shrink-0">
            {totalSymbols}
          </Badge>
        )}
      </button>

      {/* Children (recursive) */}
      {node.isDirectory && expanded && (
        <div>
          {node.children.map((child) => (
            <TreeNodeRow
              key={child.path}
              node={child}
              depth={depth + 1}
              onSelectFile={onSelectFile}
              selectedFilePath={selectedFilePath}
            />
          ))}
          {node.children.length === 0 && (
            <div
              className="text-xs text-muted-foreground py-1"
              style={{ paddingLeft: `${(depth + 1) * 16 + 4}px` }}
            >
              (empty)
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function TreeView({ sessionId: _sessionId, symbols, onSelectFile }: TreeViewProps) {
  const { t } = useTranslation();
  const [selectedFilePath, setSelectedFilePath] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState(false);

  /** 构建目录树 */
  const tree = useMemo(() => buildTree(symbols), [symbols]);

  /** 统计文件数和目录数 */
  const stats = useMemo(() => {
    const allFiles = new Set(symbols.map((s) => s.file_path));
    const allDirs = new Set<string>();
    for (const f of allFiles) {
      const parts = f.replace(/\\/g, '/').split('/');
      for (let i = 1; i < parts.length; i++) {
        allDirs.add(parts.slice(0, i).join('/'));
      }
    }
    return { fileCount: allFiles.size, dirCount: allDirs.size };
  }, [symbols]);

  const handleSelectFile = useCallback(
    (filePath: string) => {
      setSelectedFilePath(filePath);
      onSelectFile?.(filePath);
    },
    [onSelectFile],
  );

  const handleExpandAll = useCallback(() => {
    setExpandAll((prev) => !prev);
  }, []);

  if (symbols.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm flex items-center gap-2">
            <Folder className="h-4 w-4" />
            Project Tree
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
            <Folder className="h-6 w-6" />
            <p className="text-sm">{t('context.noFilesToDisplay')}</p>
            <p className="text-xs">{t('context.noFilesHint')}</p>
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
            <Folder className="h-4 w-4" />
            Project Tree
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {stats.fileCount} files
            </Badge>
            <Badge variant="outline" className="text-xs">
              {stats.dirCount} dirs
            </Badge>
          </div>
        </div>
        {/* Toolbar */}
        <div className="flex items-center gap-2 mt-1.5">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 text-xs"
            onClick={handleExpandAll}
          >
            {expandAll ? 'Collapse All' : 'Expand All'}
          </Button>
        </div>
      </CardHeader>
      <Separator />
      <CardContent className="flex-1 p-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-2">
            {tree.map((node) => (
              <TreeNodeRow
                key={node.path}
                node={node}
                depth={0}
                onSelectFile={handleSelectFile}
                selectedFilePath={selectedFilePath}
              />
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}

export default TreeView;