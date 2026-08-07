import { Brain, Database, HardDrive, Layers } from 'lucide-react';
import { useEffect, useState } from 'react';

import type { MemoryStats } from '@/api/plugins';
import { memoryApi } from '@/api/plugins';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

function formatBytes(bytes: number): string {
	if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(2)} MB`;
	if (bytes >= 1_024) return `${(bytes / 1_024).toFixed(1)} KB`;
	return `${bytes} B`;
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

export function MemoryPage() {
	const [data, setData] = useState<MemoryStats | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		async function fetchData() {
			try {
				setLoading(true);
				const stats = await memoryApi.getStats();
				setData(stats);
			} catch (err) {
				setError(err instanceof Error ? err.message : 'Failed to load memory data');
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
				<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
					{Array.from({ length: 3 }).map((_, i) => (
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
					<p className="text-destructive font-medium">Failed to load memory data</p>
					<p className="text-sm text-muted-foreground">{error}</p>
				</div>
			</div>
		);
	}

	if (!data) return null;

	const categoryEntries = Object.entries(data.by_category).sort(
		([, a], [, b]) => b - a,
	);
	const totalCategories = categoryEntries.length;

	return (
		<div className="p-8 space-y-6 overflow-y-auto h-full">
			{/* Header */}
			<div className="flex items-center gap-x-3">
				<div className="flex items-center justify-center size-10 rounded-lg bg-primary/10">
					<Brain className="size-5 text-primary" />
				</div>
				<div>
					<h1 className="text-2xl font-bold">Cerebrum Memory</h1>
					<p className="text-sm text-muted-foreground">
						Agent memory system &amp; knowledge storage
					</p>
				</div>
			</div>

			{/* Stats Grid */}
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				<StatCard
					icon={Layers}
					label="Total Entries"
					value={data.total_entries.toLocaleString()}
				/>
				<StatCard
					icon={Database}
					label="Categories"
					value={totalCategories}
				/>
				<StatCard
					icon={HardDrive}
					label="Database Size"
					value={formatBytes(data.db_size_bytes)}
				/>
			</div>

			{/* Category Breakdown */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Memory Categories</CardTitle>
				</CardHeader>
				<CardContent>
					{categoryEntries.length === 0 ? (
						<div className="flex flex-col items-center justify-center py-12 text-center">
							<Brain className="size-12 text-muted-foreground/40 mb-3" />
							<p className="text-sm text-muted-foreground">
								No memory entries yet. Memories will be created as agents work.
							</p>
						</div>
					) : (
						<div className="space-y-3">
							{categoryEntries.map(([category, count]) => {
								const pct =
									data.total_entries > 0
										? ((count / data.total_entries) * 100).toFixed(1)
										: '0';
								return (
									<div key={category} className="space-y-1">
										<div className="flex items-center justify-between text-sm">
											<span className="font-medium capitalize">{category}</span>
											<span className="text-muted-foreground">
												{count} entries ({pct}%)
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
					)}
				</CardContent>
			</Card>

			{/* DB Info */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Storage</CardTitle>
				</CardHeader>
				<CardContent>
					<div className="text-sm space-y-1">
						<p>
							<span className="text-muted-foreground">Database path: </span>
							<code className="text-xs bg-muted px-1.5 py-0.5 rounded">
								{data.db_path}
							</code>
						</p>
						<p>
							<span className="text-muted-foreground">Size: </span>
							<span className="font-medium">{formatBytes(data.db_size_bytes)}</span>
						</p>
					</div>
				</CardContent>
			</Card>
		</div>
	);
}