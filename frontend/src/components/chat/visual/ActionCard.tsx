import { TriangleAlert, Zap } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

interface Action {
	label: string;
	value: string;
	style?: string; // 'primary' | 'secondary' | 'outline' | 'destructive'
}

interface ActionCardProps {
	title: string;
	/** Structured data: { actions: { label, value, style? }[], risk_level?: string } */
	data: Record<string, unknown>;
	summary?: string;
}

const RISK_COLORS: Record<string, string> = {
	low: 'text-green-600',
	medium: 'text-yellow-600',
	high: 'text-orange-600',
	critical: 'text-red-600',
};

export function ActionCard({ title, data, summary }: ActionCardProps) {
	const { t } = useTranslation();
	const actions = (Array.isArray(data.actions) ? data.actions : []) as Action[];
	const riskLevel = (data.risk_level as string) ?? null;

	if (actions.length === 0) return null;

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<Zap className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">{t('visual.type.action', { defaultValue: 'action' })}</Badge>
			</div>
			{riskLevel ? (
				<div className="flex items-center gap-x-1.5">
					<TriangleAlert className={cn('size-3.5', RISK_COLORS[riskLevel] ?? 'text-muted-foreground')} />
					<span className={cn('text-xs font-medium', RISK_COLORS[riskLevel] ?? 'text-muted-foreground')}>
						{t('visual.action.riskLevel', { defaultValue: 'Risk Level' })}: {riskLevel}
					</span>
				</div>
			) : null}
			<ItemContent>
				<div className="flex flex-wrap gap-2">
					{actions.map((action, i) => (
						<Button
							key={i}
							variant={action.style === 'destructive' ? 'destructive' : action.style === 'outline' ? 'outline' : action.style === 'secondary' ? 'secondary' : 'default'}
							size="sm"
							className="gap-x-1.5"
						>
							{action.label}
							<span className="text-xs opacity-70">({action.value})</span>
						</Button>
					))}
				</div>
			</ItemContent>
			{summary ? (
				<p className="text-muted-foreground text-xs whitespace-pre-wrap">{summary}</p>
			) : null}
		</Item>
	);
}
