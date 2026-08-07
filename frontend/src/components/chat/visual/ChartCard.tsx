import {
	Bar,
	BarChart,
	CartesianGrid,
	Cell,
	Legend,
	Line,
	LineChart,
	Pie,
	PieChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from 'recharts';
import { BarChart3 } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Item, ItemContent } from '@/components/ui/item';
import { useTranslation } from '@/i18n/useI18n';

/** Supported chart types. */
type ChartKind = 'bar' | 'line' | 'pie' | 'area';

/** A single data point. */
interface ChartDataPoint {
	name: string;
	value: number;
	[key: string]: string | number;
}

/** Chart configuration from structured data. */
interface ChartConfig {
	/** Chart type. */
	kind?: ChartKind;
	/** Data series. */
	data?: ChartDataPoint[];
	/** X-axis key (default: 'name'). */
	xKey?: string;
	/** Data key for the main value (default: 'value'). */
	dataKey?: string;
	/** Chart colors. */
	colors?: string[];
	/** Whether to show grid lines. */
	showGrid?: boolean;
	/** Whether to show legend. */
	showLegend?: boolean;
}

interface ChartCardProps {
	title: string;
	/** Structured data: { kind, data, xKey, dataKey, colors, ... } */
	data: Record<string, unknown>;
	summary?: string;
}

const DEFAULT_COLORS = [
	'#3b82f6',
	'#ef4444',
	'#10b981',
	'#f59e0b',
	'#8b5cf6',
	'#ec4899',
	'#06b6d4',
	'#84cc16',
];

const CHART_HEIGHT = 300;

function renderChart(config: ChartConfig) {
	const {
		kind = 'bar',
		data = [],
		xKey = 'name',
		dataKey = 'value',
		colors = DEFAULT_COLORS,
		showGrid = true,
		showLegend = false,
	} = config;

	if (data.length === 0) return null;

	switch (kind) {
		case 'pie':
			return (
				<ResponsiveContainer width="100%" height={CHART_HEIGHT}>
					<PieChart>
						<Pie
							data={data}
							dataKey={dataKey}
							nameKey={xKey}
							cx="50%"
							cy="50%"
							outerRadius={100}
							label={({ name, percent }) =>
								`${name} ${((percent ?? 0) * 100).toFixed(0)}%`
							}
						>
							{data.map((_, i) => (
								<Cell key={i} fill={colors[i % colors.length]} />
							))}
						</Pie>
						<Tooltip />
						{showLegend ? <Legend /> : null}
					</PieChart>
				</ResponsiveContainer>
			);

		case 'line':
			return (
				<ResponsiveContainer width="100%" height={CHART_HEIGHT}>
					<LineChart data={data}>
						{showGrid ? <CartesianGrid strokeDasharray="3 3" opacity={0.3} /> : null}
						<XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
						<YAxis tick={{ fontSize: 12 }} />
						<Tooltip />
						{showLegend ? <Legend /> : null}
						<Line
							type="monotone"
							dataKey={dataKey}
							stroke={colors[0]}
							strokeWidth={2}
							dot={{ r: 3 }}
							activeDot={{ r: 5 }}
						/>
					</LineChart>
				</ResponsiveContainer>
			);

		case 'bar':
		default:
			return (
				<ResponsiveContainer width="100%" height={CHART_HEIGHT}>
					<BarChart data={data}>
						{showGrid ? <CartesianGrid strokeDasharray="3 3" opacity={0.3} /> : null}
						<XAxis dataKey={xKey} tick={{ fontSize: 12 }} />
						<YAxis tick={{ fontSize: 12 }} />
						<Tooltip />
						{showLegend ? <Legend /> : null}
						<Bar dataKey={dataKey} radius={[4, 4, 0, 0]}>
							{data.map((_, i) => (
								<Cell key={i} fill={colors[i % colors.length]} />
							))}
						</Bar>
					</BarChart>
				</ResponsiveContainer>
			);
	}
}

/**
 * Chart card that renders structured data using recharts.
 *
 * When the agent provides ``data`` with a ``kind`` and ``data`` array,
 * this component renders a bar, line, or pie chart. Falls back to the
 * HTML iframe in ``VisualCard`` when no structured data is provided.
 */
export function ChartCard({ title, data, summary }: ChartCardProps) {
	const { t } = useTranslation();
	const config = data as unknown as ChartConfig;

	if (!config.data || config.data.length === 0) return null;

	return (
		<Item variant="outline" className="flex-col items-stretch gap-y-2">
			<div className="flex items-center gap-x-2">
				<BarChart3 className="size-4 shrink-0 text-muted-foreground" />
				<span className="min-w-0 flex-1 truncate text-sm font-medium">{title}</span>
				<Badge variant="outline">
					{t('visual.type.chart', { defaultValue: 'chart' })}
				</Badge>
			</div>
			<ItemContent className="max-w-full">
				{renderChart(config)}
			</ItemContent>
			{summary ? (
				<p className="text-muted-foreground text-xs whitespace-pre-wrap">{summary}</p>
			) : null}
		</Item>
	);
}
