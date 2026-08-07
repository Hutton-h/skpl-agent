import { BarChart3, Coins, TrendingUp, Zap } from 'lucide-react';
import { useEffect, useState } from 'react';

import type { TokenSummary } from '@/api/plugins';
import { tokenApi } from '@/api/plugins';
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
	subtitle,
}: {
	icon: React.ComponentType<{ className?: string }>;
	label: string;
	value: string | number;
	subtitle?: string;
}) {
	return (
		<Card>
			<CardHeader className="flex flex-row items-center justify-between pb-2 space-y-0">
				<CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
				<Icon className="size-4 text-muted-foreground" />
			</CardHeader>
			<CardContent>
				<div className="text-2xl font-bold">{value}</div>
				{subtitle && <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>}
			</CardContent>
		</Card>
	);
}

export function TokenPage() {
	const [data, setData] = useState<TokenSummary | null>(null);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		async function fetchData() {
			try {
				setLoading(true);
				const summary = await tokenApi.getSummary();
				setData(summary);
			} catch (err) {
				setError(err instanceof Error ? err.message : 'Failed to load token data');
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
			</div>
		);
	}

	if (error) {
		return (
			<div className="flex items-center justify-center h-full">
				<div className="text-center space-y-2">
					<p className="text-destructive font-medium">Failed to load token data</p>
					<p className="text-sm text-muted-foreground">{error}</p>
				</div>
			</div>
		);
	}

	if (!data) return null;

	const sessionTokens = data.detailed.session_total;
	const lifetimeTokens = data.detailed.lifetime_total;

	return (
		<div className="p-8 space-y-6 overflow-y-auto h-full">
			{/* Header */}
			<div className="flex items-center gap-x-3">
				<div className="flex items-center justify-center size-10 rounded-lg bg-primary/10">
					<Coins className="size-5 text-primary" />
				</div>
				<div>
					<h1 className="text-2xl font-bold">Token Tracker</h1>
					<p className="text-sm text-muted-foreground">
						Monitor token consumption across all agents
					</p>
				</div>
			</div>

			{/* Stats Grid */}
			<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
				<StatCard
					icon={Zap}
					label="This Session"
					value={formatTokens(sessionTokens)}
					subtitle="Tokens consumed in current session"
				/>
				<StatCard
					icon={TrendingUp}
					label="Lifetime Total"
					value={formatTokens(lifetimeTokens)}
					subtitle="All-time token consumption"
				/>
				<StatCard
					icon={BarChart3}
					label="Session Ratio"
					value={lifetimeTokens > 0 ? `${((sessionTokens / lifetimeTokens) * 100).toFixed(1)}%` : 'N/A'}
					subtitle="Session vs lifetime usage"
				/>
			</div>

			{/* Usage Visualization */}
			<Card>
				<CardHeader>
					<CardTitle className="text-lg">Usage Overview</CardTitle>
				</CardHeader>
				<CardContent>
					{lifetimeTokens === 0 ? (
						<div className="flex flex-col items-center justify-center py-12 text-center">
							<Coins className="size-12 text-muted-foreground/40 mb-3" />
							<p className="text-sm text-muted-foreground">
								No tokens consumed yet. Start chatting with agents to see usage.
							</p>
						</div>
					) : (
						<div className="space-y-6">
							{/* Session bar */}
							<div className="space-y-2">
								<div className="flex items-center justify-between text-sm">
									<span className="font-medium">Session</span>
									<span className="text-muted-foreground">{formatTokens(sessionTokens)}</span>
								</div>
								<div className="w-full bg-secondary rounded-full h-3">
									<div
										className="bg-primary rounded-full h-3 transition-all"
										style={{
											width: `${Math.min((sessionTokens / lifetimeTokens) * 100, 100)}%`,
										}}
									/>
								</div>
							</div>
							{/* Lifetime bar */}
							<div className="space-y-2">
								<div className="flex items-center justify-between text-sm">
									<span className="font-medium">Lifetime</span>
									<span className="text-muted-foreground">{formatTokens(lifetimeTokens)}</span>
								</div>
								<div className="w-full bg-secondary rounded-full h-3">
									<div className="bg-emerald-500 rounded-full h-3 w-full" />
								</div>
							</div>
						</div>
					)}
				</CardContent>
			</Card>
		</div>
	);
}