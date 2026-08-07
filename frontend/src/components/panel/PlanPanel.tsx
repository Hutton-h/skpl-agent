import {
	CheckCircle2,
	Circle,
	Clock,
	Loader2,
	Play,
	XCircle,
} from 'lucide-react';
import { PanelEmpty } from '@/components/panel/PanelEmpty';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

/** A single step in the plan. */
interface PlanStep {
	/** Step index (1-based). */
	index: number;
	/** The step description. */
	text: string;
	/** Current status: pending, running, done, failed, skipped. */
	status: 'pending' | 'running' | 'done' | 'failed' | 'skipped';
	/** Optional sub-agent name assigned to this step. */
	assignedTo?: string;
	/** Estimated duration or actual duration string. */
	duration?: string;
}

interface PlanPanelProps {
	/** Whether the plan is active (an agent is currently executing it). */
	active?: boolean;
	/** Whether the plan is awaiting user confirmation. */
	needsConfirmation?: boolean;
	/** The plan steps. */
	steps?: PlanStep[];
	/** Total number of steps. */
	totalSteps?: number;
	/** Number of completed steps. */
	completedSteps?: number;
	/** Called when the user approves the plan. */
	onApprove?: () => void;
	/** Called when the user rejects the plan. */
	onReject?: () => void;
}

const STATUS_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
	pending: Circle,
	running: Loader2,
	done: CheckCircle2,
	failed: XCircle,
	skipped: Circle,
};

const STATUS_COLORS: Record<string, string> = {
	pending: 'text-muted-foreground',
	running: 'text-blue-500',
	done: 'text-green-500',
	failed: 'text-red-500',
	skipped: 'text-muted-foreground/50',
};

const STATUS_BADGE_VARIANT: Record<string, 'outline' | 'secondary' | 'default' | 'destructive'> = {
	pending: 'outline',
	running: 'default',
	done: 'secondary',
	failed: 'destructive',
	skipped: 'outline',
};

/**
 * Standalone plan panel displayed in the PanelDock.
 *
 * Shows the agent's execution plan as a timeline of steps with status
 * indicators. When ``needsConfirmation`` is true, renders Approve/Reject
 * buttons so the user can gate execution before the agent starts work.
 */
export function PlanPanel({
	active = false,
	needsConfirmation = false,
	steps = [],
	totalSteps = 0,
	completedSteps = 0,
	onApprove,
	onReject,
}: PlanPanelProps) {
	const { t } = useTranslation();
	// Empty state
	if (!active && !needsConfirmation && steps.length === 0) {
		return (
			<PanelEmpty
				icon={Clock}
				title={t('panel.plan.emptyTitle')}
				description={t('panel.plan.emptyDescription')}
			/>
		);
	}

	const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

	return (
		<div className="flex flex-col flex-1 min-h-0 gap-y-3">
			{/* Header */}
			<div className="flex items-center justify-between shrink-0">
				<div className="flex items-center gap-x-2">
					<Clock className="size-4 text-muted-foreground" />
					<span className="text-sm font-medium">
						{t('panel.plan.title')}
					</span>
					{active ? (
						<Badge variant="default" className="animate-pulse">
							{t('panel.plan.active')}
						</Badge>
					) : needsConfirmation ? (
						<Badge
							variant="outline"
							className="border-yellow-500/50 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
						>
							{t('panel.plan.awaiting')}
						</Badge>
					) : null}
				</div>
				{totalSteps > 0 ? (
					<span className="text-xs text-muted-foreground tabular-nums">
						{completedSteps}/{totalSteps}
					</span>
				) : null}
			</div>

			{/* Progress bar */}
			{totalSteps > 0 ? (
				<div className="shrink-0">
					<div className="h-1.5 w-full rounded-full bg-muted">
						<div
							className={cn(
								'h-1.5 rounded-full transition-all duration-500',
								needsConfirmation
									? 'bg-yellow-500'
									: progress === 100
										? 'bg-green-500'
										: 'bg-blue-500',
							)}
							style={{ width: `${needsConfirmation ? 0 : Math.max(progress, 2)}%` }}
						/>
					</div>
				</div>
			) : null}

			{/* Steps list */}
			{steps.length > 0 ? (
				<div className="flex flex-col flex-1 min-h-0 overflow-y-auto gap-y-1">
					{steps.map((step) => {
						const StatusIcon = STATUS_ICONS[step.status] ?? Circle;
						const isRunning = step.status === 'running';
						return (
							<Item key={step.index} variant="outline" className="items-start gap-x-2 py-1.5">
								<StatusIcon
									className={cn(
										'size-4 shrink-0 mt-0.5',
										STATUS_COLORS[step.status] ?? 'text-muted-foreground',
										isRunning && 'animate-spin',
									)}
								/>
								<ItemContent>
									<div className="flex items-center gap-x-2">
										<span className="text-xs font-medium tabular-nums text-muted-foreground">
											{step.index}.
										</span>
										<span
											className={cn(
												'text-sm',
												step.status === 'done' && 'line-through text-muted-foreground',
												step.status === 'failed' && 'text-red-600',
											)}
										>
											{step.text}
										</span>
									</div>
									<div className="flex items-center gap-x-2 mt-0.5">
										<Badge variant={STATUS_BADGE_VARIANT[step.status] ?? 'outline'} className="text-[10px] px-1 py-0">
											{t(`panel.plan.status.${step.status}`, { defaultValue: step.status })}
										</Badge>
										{step.assignedTo ? (
											<span className="text-[10px] text-muted-foreground">
												{step.assignedTo}
											</span>
										) : null}
										{step.duration ? (
											<span className="text-[10px] text-muted-foreground tabular-nums">
												{step.duration}
											</span>
										) : null}
									</div>
								</ItemContent>
							</Item>
						);
					})}
				</div>
			) : needsConfirmation ? (
				<div className="flex flex-1 items-center justify-center">
					<p className="text-sm text-muted-foreground">
						{t('panel.plan.waitingForPlan')}
					</p>
				</div>
			) : null}

			{/* Confirmation buttons */}
			{needsConfirmation ? (
				<div className="flex items-center gap-x-2 shrink-0">
					<Button
						variant="default"
						size="sm"
						className="flex-1"
						onClick={onApprove}
					>
						<Play className="size-3.5" />
						{t('panel.plan.approve')}
					</Button>
					<Button
						variant="outline"
						size="sm"
						className="flex-1"
						onClick={onReject}
					>
						<XCircle className="size-3.5" />
						{t('panel.plan.reject')}
					</Button>
				</div>
			) : null}
		</div>
	);
}
