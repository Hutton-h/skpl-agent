import { ClipboardList } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

interface PlanCardProps {
	steps: string[];
	needsConfirmation: boolean;
}

/**
 * Card rendering a ``CustomEvent(name="plan")`` payload: an ordered list
 * of planned steps, each prefixed with a numbered circle. When the plan
 * still awaits user confirmation a yellow outline badge is shown;
 * otherwise a muted "planned" badge.
 */
export function PlanCard({ steps, needsConfirmation }: PlanCardProps) {
	const { t } = useTranslation();

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<ClipboardList className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">
					{t('plan-card.title')}
				</span>
				{needsConfirmation ? (
					<Badge
						variant="outline"
						className="border-yellow-500/50 bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
					>
						{t('plan-card.awaitingConfirmation')}
					</Badge>
				) : (
					<Badge variant="secondary">{t('plan-card.planned')}</Badge>
				)}
			</div>
			<ItemContent className="max-w-full">
				<ol className="flex flex-col gap-y-1.5">
					{steps.map((step, i) => (
						<li key={i} className="flex items-start gap-x-2 text-sm">
							<span
								className={cn(
									'mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border text-[11px] tabular-nums',
									needsConfirmation
										? 'border-yellow-500/50 text-yellow-600 dark:text-yellow-400'
										: 'border-border text-muted-foreground',
								)}
							>
								{i + 1}
							</span>
							<span className="min-w-0 flex-1 whitespace-pre-wrap break-words">
								{step}
							</span>
						</li>
					))}
				</ol>
			</ItemContent>
		</Item>
	);
}
