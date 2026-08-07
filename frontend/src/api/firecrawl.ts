/**
 * Firecrawl API client.
 *
 * Endpoints:
 * - POST /api/firecrawl/crawl     — start a new crawl
 * - GET  /api/firecrawl/crawl/{id} — get crawl status
 * - GET  /api/firecrawl/crawls     — list crawls
 * - POST /api/firecrawl/crawl/{id}/cancel — cancel a crawl
 * - GET  /api/firecrawl/config     — get config
 * - PUT  /api/firecrawl/config     — update config
 * - GET  /api/firecrawl/stats      — get stats
 */
import { client } from './client';

export interface CrawlRequest {
  url: string;
  mode?: string;
  max_pages?: number;
  include_patterns?: string[];
  exclude_patterns?: string[];
  wait_for?: number;
}

export interface CrawlResult {
  id: string;
  url: string;
  status: string;
  pages_crawled: number;
  pages_failed: number;
  content: Array<Record<string, unknown>>;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface FirecrawlConfig {
  api_key: string;
  api_endpoint: string;
  max_concurrent_crawls: number;
  rate_limit_per_minute: number;
  default_max_pages: number;
  timeout_seconds: number;
  respect_robots_txt: boolean;
  user_agent: string;
}

export interface FirecrawlStats {
  total_crawls: number;
  completed_crawls: number;
  failed_crawls: number;
  active_crawls: number;
  total_pages_crawled: number;
}

export const firecrawlApi = {
  startCrawl: (body: CrawlRequest) =>
    client.post<CrawlResult>('/api/firecrawl/crawl', body),

  getCrawlStatus: (crawlId: string) =>
    client.get<CrawlResult>(`/api/firecrawl/crawl/${crawlId}`),

  listCrawls: (limit?: number) =>
    client.get<CrawlResult[]>(`/api/firecrawl/crawls${limit ? `?limit=${limit}` : ''}`),

  cancelCrawl: (crawlId: string) =>
    client.post<{ success: boolean }>(`/api/firecrawl/crawl/${crawlId}/cancel`),

  getConfig: () =>
    client.get<FirecrawlConfig>('/api/firecrawl/config'),

  updateConfig: (body: Partial<FirecrawlConfig>) =>
    client.put<FirecrawlConfig>('/api/firecrawl/config', body),

  getStats: () =>
    client.get<FirecrawlStats>('/api/firecrawl/stats'),
};