import { Clock } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';

interface TimelineItem {
	time: string;
	title: string;
	description?: string;
}

interface TimelineCardProps {
	title: string;
	/** Structured data: { items: { time, title, description? }[] } */
	data: Record<string, unknown>;
	summary?: string;
}

export function TimelineCard({ title, data, summary }: TimelineCardProps) {
	const { t } = useTranslation();
	const items = (Array.isArray(data.items) ? data.items : []) as TimelineItem[];

	if (items.length === 0) return null;

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<Clock className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">{t('visual.type.timeline', { defaultValue: 'timeline' })}</Badge>
			</div>
			<ItemContent>
				<div className="relative pl-4 border-l-2 border-border">
					{items.map((item, i) => (
						<div key={i} className="relative pb-3 last:pb-0">
							{/* Dot */}
							<div className="absolute -left-[21px] top-1 size-2.5 rounded-full border-2 border-border bg-background" />
							<time className="text-xs text-muted-foreground">{item.time}</time>
							<h4 className="text-sm font-medium">{item.title}</h4>
							{item.description ? (
								<p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
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
