import {
	BarChart3,
	Clock,
	GitCompare,
	LayoutDashboard,
	Table,
	Zap,
	type LucideIcon,
} from 'lucide-react';
import { useCallback, useRef, useState } from 'react';

import type { VisualType } from '@/components/chat/custom-blocks';
import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';
import { ActionCard } from './ActionCard';
import { ChartCard } from './ChartCard';
import { ComparisonCard } from './ComparisonCard';
import { DashboardCard } from './DashboardCard';
import { TimelineCard } from './TimelineCard';

const FALLBACK_HEIGHT = 320;
const MIN_HEIGHT = 200;

const VISUAL_ICONS: Record<string, LucideIcon> = {
	chart: BarChart3,
	table: Table,
	comparison: GitCompare,
	dashboard: LayoutDashboard,
	timeline: Clock,
	action: Zap,
};

interface VisualCardProps {
	title: string;
	visualType: VisualType | (string & {});
	html: string;
	summary?: string;
	/** Optional structured JSON data for dedicated frontend components (comparison, dashboard, timeline, action). */
	data?: Record<string, unknown> | null;
}

/**
 * Render a visual card. When ``data`` is provided and the visual type
 * matches a dedicated component, the structured data is rendered with
 * that component instead of the raw HTML iframe.
 */
export function VisualCard({ title, visualType, html, summary, data }: VisualCardProps) {
	const { t } = useTranslation();
	const iframeRef = useRef<HTMLIFrameElement>(null);
	const [height, setHeight] = useState(FALLBACK_HEIGHT);

	const Icon = VISUAL_ICONS[visualType] ?? BarChart3;
	const typeLabel = t(`visual.type.${visualType}`, { defaultValue: visualType });

	const handleLoad = useCallback(() => {
		try {
			const doc = iframeRef.current?.contentDocument;
			const scrollHeight = doc?.body?.scrollHeight;
			if (scrollHeight && scrollHeight > 0) {
				setHeight(Math.max(MIN_HEIGHT, scrollHeight));
			}
		} catch {
			// Cross-origin sandboxed document
		}
	}, []);

	// Route to dedicated component when structured data is available.
	if (data && typeof data === 'object') {
		switch (visualType) {
			case 'comparison':
				return <ComparisonCard title={title} data={data} summary={summary} />;
			case 'dashboard':
				return <DashboardCard title={title} data={data} summary={summary} />;
			case 'timeline':
				return <TimelineCard title={title} data={data} summary={summary} />;
			case 'action':
				return <ActionCard title={title} data={data} summary={summary} />;
			case 'chart':
				return <ChartCard title={title} data={data} summary={summary} />;
			case 'table':
				// table — fall through to HTML iframe
				break;
			default:
				// unknown — fall through to HTML iframe
				break;
		}
	}

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<Icon className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">{typeLabel}</Badge>
			</div>
			{html ? (
				<ItemContent className="max-w-full">
					<iframe
						ref={iframeRef}
						sandbox="allow-scripts"
						srcDoc={html}
						title={title || typeLabel}
						onLoad={handleLoad}
						className="rounded-md"
						style={{
							border: 0,
							width: '100%',
							minHeight: MIN_HEIGHT,
							height,
							background: 'transparent',
						}}
					/>
				</ItemContent>
			) : null}
			{summary ? (
				<p className="text-muted-foreground text-xs whitespace-pre-wrap">{summary}</p>
			) : null}
		</Item>
	);
}
