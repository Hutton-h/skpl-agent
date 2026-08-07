/**
 * Web Intelligence API client.
 *
 * Endpoints:
 * - POST /api/web-intelligence/search    — web search
 * - POST /api/web-intelligence/knowledge — knowledge retrieval
 * - POST /api/web-intelligence/research  — start research task
 * - GET  /api/web-intelligence/research/{id} — research status
 * - GET  /api/web-intelligence/research  — list research tasks
 * - GET  /api/web-intelligence/engines   — available engines
 */
import { client } from './client';

export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
  source: string;
}

export interface SearchRequest {
  query: string;
  engine?: string;
  num_results?: number;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface KnowledgeRequest {
  instruction: string;
  search_query?: string;
  engine?: string;
}

export interface KnowledgeResponse {
  query: string;
  results: SearchResult[];
}

export interface ResearchRequest {
  query: string;
  context?: string;
  max_sources?: number;
}

export interface ResearchResponse {
  task_id: string;
  query: string;
  synthesis: string;
  sources: SearchResult[];
  sub_queries_used: string[];
  iterations: number;
  duration_seconds: number;
}

export interface ResearchStatus {
  task_id: string;
  query: string;
  status: string;
  sub_queries: string[];
  sources_count: number;
  synthesis: string;
}

export interface ResearchListItem {
  task_id: string;
  query: string;
  status: string;
  sources_count: number;
}

export const webIntelligenceApi = {
  search: (body: SearchRequest) =>
    client.post<SearchResponse>('/api/web-intelligence/search', body),

  retrieveKnowledge: (body: KnowledgeRequest) =>
    client.post<KnowledgeResponse>('/api/web-intelligence/knowledge', body),

  startResearch: (body: ResearchRequest) =>
    client.post<ResearchResponse>('/api/web-intelligence/research', body),

  getResearchStatus: (taskId: string) =>
    client.get<ResearchStatus>(`/api/web-intelligence/research/${taskId}`),

  listResearchTasks: () =>
    client.get<ResearchListItem[]>('/api/web-intelligence/research'),

  listEngines: () =>
    client.get<{ engines: string[] }>('/api/web-intelligence/engines'),
};