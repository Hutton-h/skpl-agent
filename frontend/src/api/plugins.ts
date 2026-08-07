import { client } from './client';

// ── Anatomy 认知引擎 ──

export interface AnatomySummary {
	summary: string;
	stats: {
		total_files: number;
		total_tokens: number;
		total_symbols: number;
		languages: Record<string, number>;
		built_at: string;
	};
}

export interface AnatomyStatus {
	enabled: boolean;
	project_root: string;
	index_built: boolean;
}

export const anatomyApi = {
	getStatus: () => client.get<AnatomyStatus>('/api/plugins/anatomy/status'),
	getSummary: () => client.get<AnatomySummary>('/api/plugins/anatomy/summary'),
};

// ── Memory 记忆系统 ──

export interface MemoryStats {
	total_entries: number;
	by_category: Record<string, number>;
	db_path: string;
	db_size_bytes: number;
}

export const memoryApi = {
	getStats: () => client.get<MemoryStats>('/api/plugins/memory/stats'),
};

// ── Token 追踪 ──

export interface TokenSummary {
	lifetime_total: number;
	session_total: number;
	detailed: {
		session_total: number;
		lifetime_total: number;
	};
}

export const tokenApi = {
	getSummary: () => client.get<TokenSummary>('/api/plugins/token/summary'),
};