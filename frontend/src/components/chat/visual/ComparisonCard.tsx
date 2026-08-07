import { GitCompare } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { cn } from '@/lib/utils';

interface ComparisonCardProps {
	title: string;
	/** Structured data: { headers: string[], rows: string[][] } */
	data: Record<string, unknown>;
	summary?: string;
}

export function ComparisonCard({ title, data, summary }: ComparisonCardProps) {
	const { t } = useTranslation();
	const headers = (Array.isArray(data.headers) ? data.headers : []) as string[];
	const rows = (Array.isArray(data.rows) ? data.rows : []) as string[][];

	if (headers.length === 0 || rows.length === 0) return null;

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<GitCompare className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">{t('visual.type.comparison', { defaultValue: 'comparison' })}</Badge>
			</div>
			<ItemContent className="max-w-full overflow-x-auto">
				<table className="w-full text-xs border-collapse">
					<thead>
						<tr className="border-b border-border">
							{headers.map((h, i) => (
								<th
									key={i}
									className={cn(
										'px-2 py-1.5 text-left font-semibold text-muted-foreground whitespace-nowrap',
										i === 0 && 'pl-0',
										i === headers.length - 1 && 'pr-0',
									)}
								>
									{h}
								</th>
							))}
						</tr>
					</thead>
					<tbody>
						{rows.map((row, ri) => (
							<tr key={ri} className="border-b border-border/50 last:border-0">
								{row.map((cell, ci) => (
									<td
										key={ci}
										className={cn(
											'px-2 py-1.5 whitespace-nowrap',
											ci === 0 && 'pl-0 font-medium',
											ci === headers.length - 1 && 'pr-0',
										)}
									>
										{cell}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</ItemContent>
			{summary ? (
				<p className="text-muted-foreground text-xs whitespace-pre-wrap">{summary}</p>
			) : null}
		</Item>
	);
}
