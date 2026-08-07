import { Activity, Code2, FileCode, FolderTree, Hash, Layers } from 'lucide-react';
import { useEffect, useState } from 'react';

import type { AnatomySummary } from '@/api/plugins';
import { anatomyApi } from '@/api/plugins';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

function formatTokens(n: number): string {
	if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
	if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
	return String(n);
}

function StatCard({
	icon: Icon,
	label,
	value,
}: {
	icon: React.ComponentType<{ className?: string }>;
	label: string;
	value: string | number;
}) {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
				<CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
				<Icon className="size-4 text-muted-foreground" />
			</CardHeader>
			<CardContent>
				<div className="text-2xl font-bold">{value}</div>
			</CardContent>
		</Card>
	);
}

export function AnatomyPage() {
	const [data, setData] = useState<AnatomySummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		async function fetchData() {
			try {
				setLoading(true);
				const summary = await anatomyApi.getSummary();
				setData(summary);
			} catch (err) {
				setError(err instanceof Error ? err.message : 'Failed to load anatomy data');
			} finally {
				setLoading(false);
			}
		}
		fetchData();
	}, []);

	if (loading) {
		return (
			<div className="p-8 space-y-6">
				<div className="flex items-center gap-x-3">
					<Skeleton className="h-8 w-8 rounded-lg" />
					<Skeleton className="h-8 w-48" />
				</div>
				<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
					{Array.from({ length: 4 }).map((_, i) => (
						<Skeleton key={i} className="h-28 rounded-xl" />
					))}
				</div>
				<Skeleton className="h-64 rounded-xl" />
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="text-center space-y-2">
					<p className="text-destructive font-medium">Failed to load anatomy data</p>
					<p className="text-sm text-muted-foreground">{error}</p>
				</div>
			</div>
		);
	}

	if (!data) return null;

	const { stats } = data;
	const langEntries = Object.entries(stats.languages).sort(([, a], [, b]) => b - a);
	const totalLangFiles = langEntries.reduce((sum, [, count]) => sum + count, 0);

	return (
		<div className="p-8 space-y-6 overflow-y-auto h-full">
			{/* Header */}
			<div className="flex items-center gap-x-3">
				<div className="flex items-center justify-center size-10 rounded-lg bg-primary/10">
					<FolderTree className="size-5 text-primary" />
				</div>
				<div>
					<h1 className="text-2xl font-bold">Anatomy Index</h1>
					<p className="text-sm text-muted-foreground">
						Project structure &amp; code intelligence
					</p>
				</div>
			</div>

			{/* Stats Grid */}
			<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
				<StatCard icon={FileCode} label="Indexed Files" value={stats.total_files.toLocaleString()} />
				<StatCard icon={Hash} label="Total Tokens" value={formatTokens(stats.total_tokens)} />
				<StatCard icon={Code2} label="Symbols" value={stats.total_symbols.toLocaleString()} />
				<StatCard icon={Layers} label="Languages" value={langEntries.length} />
			</div>

			{/* Language Distribution */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg flex items-center gap-x-2">
						<Activity className="size-4" />
						Language Distribution
					</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="space-y-3">
						{langEntries.map(([lang, count]) => {
							const pct = ((count / totalLangFiles) * 100).toFixed(1);
							return (
								<div key={lang} className="space-y-1">
									<div className="flex items-center justify-between text-sm">
										<span className="font-medium">{lang}</span>
										<span className="text-muted-foreground">
											{count} files ({pct}%)
										</span>
									</div>
									<div className="w-full bg-secondary rounded-full h-2">
										<div
											className="bg-primary rounded-full h-2 transition-all"
											style={{ width: `${pct}%` }}
										/>
									</div>
								</div>
							);
						})}
					</div>
				</CardContent>
			</Card>

			{/* Build Info */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Build Information</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="grid grid-cols-2 gap-4 text-sm">
						<div>
							<span className="text-muted-foreground">Built at: </span>
							<span className="font-medium">{new Date(stats.built_at).toLocaleString()}</span>
						</div>
						<div>
							<span className="text-muted-foreground">Avg tokens/file: </span>
							<span className="font-medium">
								{formatTokens(Math.round(stats.total_tokens / stats.total_files))}
							</span>
						</div>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}