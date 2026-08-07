import { ArrowDown, ArrowUp, LayoutDashboard, Minus } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

interface Metric {
	label: string;
	value: string;
	change?: string;
}

interface DashboardCardProps {
	title: string;
	/** Structured data: { metrics: { label, value, change? }[] } */
	data: Record<string, unknown>;
	summary?: string;
}

function TrendIcon({ change }: { change?: string }) {
	if (!change) return null;
	const num = parseFloat(change);
	if (isNaN(num)) return null;
	if (num > 0) return <ArrowUp className="size-3 text-green-500" />;
	if (num < 0) return <ArrowDown className="size-3 text-red-500" />;
	return <Minus className="size-3 text-muted-foreground" />;
}

function TrendColor({ change }: { change?: string }): string {
	if (!change) return 'text-muted-foreground';
	const num = parseFloat(change);
	if (isNaN(num)) return 'text-muted-foreground';
	if (num > 0) return 'text-green-600';
	if (num < 0) return 'text-red-600';
	return 'text-muted-foreground';
}

export function DashboardCard({ title, data, summary }: DashboardCardProps) {
	const { t } = useTranslation();
	const metrics = (Array.isArray(data.metrics) ? data.metrics : []) as Metric[];

	if (metrics.length === 0) return null;

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<LayoutDashboard className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">{t('visual.type.dashboard', { defaultValue: 'dashboard' })}</Badge>
			</div>
			<ItemContent>
				<div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
					{metrics.map((m, i) => (
						<div
							key={i}
							className="flex flex-col rounded-md border border-border/60 bg-muted/30 p-2.5"
						>
							<span className="text-xs text-muted-foreground truncate">{m.label}</span>
							<span className="text-lg font-bold">{m.value}</span>
							{m.change !== undefined ? (
								<span className={cn('flex items-center gap-0.5 text-xs', TrendColor({ change: m.change }))}>
									<TrendIcon change={m.change} />
									{m.change}
								</span>
							) : null}
						</div>
					))}
				</div>
			</ItemContent>
			{summary ? (
				<p className="text-muted-foreground text-xs whitespace-pre-wrap">{summary}</p>
			) : null}
		</Item>
	);
}
