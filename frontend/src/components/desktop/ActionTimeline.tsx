/**
 * ActionTimeline — Desktop action history timeline component.
 *
 * Displays a chronological timeline of desktop automation actions
 * with their status, duration, and results. Supports filtering
 * by action type, status, and time range.
 *
 * Features:
 * - Chronological action list
 * - Status indicators (completed, failed, pending, running)
 * - Duration display
 * - Action type icons
 * - Expandable details
 * - Filtering and search
 */
import { cn } from '@/lib/utils';
import {
  CheckCircle2,
  Clock,
  Loader2,
  MousePointerClick,
  Keyboard,
  Camera,
  MousePointer2,
  GripHorizontal,
  XCircle,
  Timer,
  ArrowUpDown,
  Filter,
  Search,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from '@/i18n/useI18n';

/**
 * Action status type.
 */
export type ActionStatus = 'completed' | 'failed' | 'pending' | 'running' | 'cancelled' | 'timed_out';

/**
 * Action type.
 */
export type ActionType =
  | 'click'
  | 'double_click'
  | 'right_click'
  | 'type'
  | 'key_press'
  | 'hotkey'
  | 'scroll'
  | 'drag'
  | 'move'
  | 'wait'
  | 'screenshot'
  | 'open_app'
  | 'switch_app'
  | 'custom_code';

/**
 * A single action entry in the timeline.
 */
export interface ActionEntry {
  id: string;
  type: ActionType;
  status: ActionStatus;
  timestamp: string;
  durationMs: number;
  params: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
}

interface ActionTimelineProps {
  /** List of action entries */
  actions: ActionEntry[];
  /** Whether to show the filter bar */
  showFilters?: boolean;
  /** Maximum number of actions to show */
  maxItems?: number;
  /** Callback when an action is clicked */
  onActionClick?: (action: ActionEntry) => void;
  /** Additional CSS classes */
  className?: string;
}

/** Action type to icon mapping */
const ACTION_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  click: MousePointerClick,
  double_click: MousePointerClick,
  right_click: MousePointerClick,
  type: Keyboard,
  key_press: Keyboard,
  hotkey: Keyboard,
  scroll: MousePointer2,
  drag: GripHorizontal,
  move: MousePointer2,
  wait: Timer,
  screenshot: Camera,
  open_app: ArrowUpDown,
  switch_app: ArrowUpDown,
  custom_code: Keyboard,
};

/** Status color & icon mapping */
const STATUS_CONFIG: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string }
> = {
  completed: { icon: CheckCircle2, color: 'text-green-500', bgColor: 'bg-green-500/10' },
  failed: { icon: XCircle, color: 'text-red-500', bgColor: 'bg-red-500/10' },
  pending: { icon: Clock, color: 'text-yellow-500', bgColor: 'bg-yellow-500/10' },
  running: { icon: Loader2, color: 'text-blue-500', bgColor: 'bg-blue-500/10' },
  cancelled: { icon: XCircle, color: 'text-gray-400', bgColor: 'bg-gray-400/10' },
  timed_out: { icon: Timer, color: 'text-orange-500', bgColor: 'bg-orange-500/10' },
};

export function ActionTimeline({
  actions,
  showFilters = true,
  maxItems = 50,
  onActionClick,
  className,
}: ActionTimelineProps) {
  const { t } = useTranslation();

  const ACTION_LABELS: Record<string, string> = {
    click: t('desktop.actionClick'),
    double_click: t('desktop.actionDoubleClick'),
    right_click: t('desktop.actionRightClick'),
    type: t('desktop.actionType'),
    key_press: t('desktop.actionKeyPress'),
    hotkey: t('desktop.actionHotkey'),
    scroll: t('desktop.actionScroll'),
    drag: t('desktop.actionDrag'),
    move: t('desktop.actionMove'),
    wait: t('desktop.actionWait'),
    screenshot: t('desktop.actionScreenshot'),
    open_app: t('desktop.actionOpenApp'),
    switch_app: t('desktop.actionSwitchApp'),
    custom_code: t('desktop.actionCustomCode'),
  };

  const [statusFilter, setStatusFilter] = useState<ActionStatus | 'all'>('all');
  const [typeFilter, setTypeFilter] = useState<ActionType | 'all'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedActions, setExpandedActions] = useState<Set<string>>(new Set());

  // Filter actions
  const filteredActions = useMemo(() => {
    let result = actions;

    if (statusFilter !== 'all') {
      result = result.filter((a) => a.status === statusFilter);
    }
    if (typeFilter !== 'all') {
      result = result.filter((a) => a.type === typeFilter);
    }
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (a) =>
          a.type.toLowerCase().includes(q) ||
          a.id.toLowerCase().includes(q) ||
          (a.error && a.error.toLowerCase().includes(q)) ||
          JSON.stringify(a.params).toLowerCase().includes(q),
      );
    }

    return result.slice(0, maxItems);
  }, [actions, statusFilter, typeFilter, searchQuery, maxItems]);

  const toggleExpand = (actionId: string) => {
    setExpandedActions((prev) => {
      const next = new Set(prev);
      if (next.has(actionId)) {
        next.delete(actionId);
      } else {
        next.add(actionId);
      }
      return next;
    });
  };

  const formatDuration = (ms: number): string => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${(ms / 60000).toFixed(1)}m`;
  };

  const formatTimestamp = (iso: string): string => {
    try {
      return new Date(iso).toLocaleTimeString();
    } catch {
      return iso;
    }
  };

  const uniqueTypes = useMemo(() => {
    const types = new Set(actions.map((a) => a.type));
    return Array.from(types).sort();
  }, [actions]);

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {/* Filter bar */}
      {showFilters && (
        <div className="flex flex-wrap items-center gap-2 rounded-md bg-muted/30 p-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as ActionStatus | 'all')}
            className="rounded border bg-background px-2 py-1 text-xs"
          >
            <option value="all">{t('desktop.allStatus')}</option>
            <option value="completed">{t('desktop.statusCompleted')}</option>
            <option value="failed">{t('desktop.statusFailed')}</option>
            <option value="running">{t('common.running')}</option>
            <option value="pending">{t('desktop.statusPending')}</option>
            <option value="cancelled">{t('desktop.statusCancelled')}</option>
            <option value="timed_out">{t('desktop.statusTimedOut')}</option>
          </select>
          {/* Type filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as ActionType | 'all')}
            className="rounded border bg-background px-2 py-1 text-xs"
          >
            <option value="all">{t('desktop.allTypes')}</option>
            {uniqueTypes.map((t) => (
              <option key={t} value={t}>
                {ACTION_LABELS[t] ?? t}
              </option>
            ))}
          </select>
          {/* Search */}
          <div className="relative ml-auto">
            <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t('desktop.searchActions')}
              className="w-32 rounded border bg-background py-1 pl-7 pr-2 text-xs"
            />
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="relative">
        {/* Timeline line */}
        <div className="absolute left-[19px] top-2 bottom-2 w-px bg-border" />

        <div className="flex flex-col gap-0.5">
          {filteredActions.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-muted-foreground">
              <Clock className="h-6 w-6" />
              <span className="text-sm">{t('desktop.noActions')}</span>
            </div>
          ) : (
            filteredActions.map((action) => {
              const statusCfg = STATUS_CONFIG[action.status] ?? STATUS_CONFIG.pending;
              const StatusIcon = statusCfg.icon;
              const ActionIcon = ACTION_ICONS[action.type] ?? MousePointerClick;
              const isExpanded = expandedActions.has(action.id);

              return (
                <div
                  key={action.id}
                  className={cn(
                    'group relative ml-10 rounded-md border border-transparent p-2 transition-colors',
                    'hover:border-border hover:bg-muted/30',
                    onActionClick && 'cursor-pointer',
                  )}
                  onClick={() => onActionClick?.(action)}
                >
                  {/* Timeline dot */}
                  <div
                    className={cn(
                      'absolute -left-[26px] top-3 flex h-4 w-4 items-center justify-center rounded-full border-2 border-background',
                      statusCfg.bgColor,
                    )}
                  >
                    <StatusIcon
                      className={cn(
                        'h-3 w-3',
                        statusCfg.color,
                        action.status === 'running' && 'animate-spin',
                      )}
                    />
                  </div>

                  {/* Action header */}
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleExpand(action.id);
                      }}
                      className="text-muted-foreground hover:text-foreground"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5" />
                      )}
                    </button>
                    <ActionIcon className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="text-sm font-medium">
                      {ACTION_LABELS[action.type] ?? action.type}
                    </span>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      {formatDuration(action.durationMs)}
                    </span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {formatTimestamp(action.timestamp)}
                    </span>
                  </div>

                  {/* Action summary */}
                  <div className="mt-1 text-xs text-muted-foreground">
                    <ActionSummary action={action} />
                  </div>

                  {/* Expanded details */}
                  {isExpanded && (
                    <div className="mt-2 space-y-1 border-t pt-2 text-xs">
                      <div>
                        <span className="font-medium">ID:</span>{' '}
                        <code className="text-[11px]">{action.id}</code>
                      </div>
                      <div>
                        <span className="font-medium">Params:</span>{' '}
                        <code className="break-all text-[11px]">
                          {JSON.stringify(action.params)}
                        </code>
                      </div>
                      {action.result && (
                        <div>
                          <span className="font-medium">Result:</span>{' '}
                          <code className="break-all text-[11px]">
                            {JSON.stringify(action.result)}
                          </code>
                        </div>
                      )}
                      {action.error && (
                        <div className="rounded bg-red-500/10 px-2 py-1 text-red-600 dark:text-red-400">
                          {action.error}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Summary footer */}
      {actions.length > 0 && (
        <div className="flex items-center gap-4 border-t pt-2 text-xs text-muted-foreground">
          <span>
            <CheckCircle2 className="mr-1 inline h-3 w-3 text-green-500" />
            {actions.filter((a) => a.status === 'completed').length} {t('desktop.actionsCompleted')}
          </span>
          <span>
            <XCircle className="mr-1 inline h-3 w-3 text-red-500" />
            {actions.filter((a) => a.status === 'failed').length} {t('desktop.actionsFailed')}
          </span>
          <span className="ml-auto">
            {filteredActions.length}{' '}
            {actions.length > maxItems ? `/ ${actions.length}` : ''}{' '}
            {t('desktop.actionsCount')}
          </span>
        </div>
      )}
    </div>
  );
}

/**
 * Renders a human-readable summary of an action's parameters.
 */
function ActionSummary({ action }: { action: ActionEntry }) {
  const { type, params: rawParams, error } = action;
  const params = rawParams as any;

  if (error) {
    return <span className="text-red-600 dark:text-red-400 truncate">{error}</span>;
  }

  switch (type) {
    case 'click':
    case 'double_click':
    case 'right_click':
      return (
        <span>
          at ({params.x}, {params.y})
          {params.button && params.button !== 'left' && ` [${params.button}]`}
        </span>
      );
    case 'type':
      return (
        <span className="truncate">
          &ldquo;{String(params.text ?? '').slice(0, 50)}&rdquo;
        </span>
      );
    case 'key_press':
      return <span>Key: {String(params.key ?? '')}</span>;
    case 'hotkey':
      return (
        <span>
          {Array.isArray(params.keys) ? params.keys.join('+') : String(params.keys ?? '')}
        </span>
      );
    case 'scroll':
      return <span>{params.clicks} clicks</span>;
    case 'drag':
      return (
        <span>
          ({params.x1}, {params.y1}) to ({params.x2}, {params.y2})
        </span>
      );
    case 'move':
      return <span>to ({params.x}, {params.y})</span>;
    case 'wait':
      return <span>{params.duration}s</span>;
    case 'screenshot':
      return <span>Quality: {params.quality ?? 85}</span>;
    case 'open_app':
    case 'switch_app':
      return <span>{String(params.app_name ?? '')}</span>;
    case 'custom_code':
      return (
        <span>
          {String(params.code ?? '').slice(0, 60)}
          {String(params.code ?? '').length > 60 ? '...' : ''}
        </span>
      );
    default:
      return <span>{JSON.stringify(params).slice(0, 80)}</span>;
  }
}

export default ActionTimeline;