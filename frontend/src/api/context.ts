/**
 * Context API client — SKPL context management endpoints.
 *
 * Covers:
 * - Context generation & session summary
 * - Anatomy scanning & symbol search
 * - Bug logging & management
 * - Cerebrum memory
 * - Token tracking & waste detection
 */
import { client } from './client';

// ── Types ───────────────────────────────────────────────────────────────────

export interface ContextGenerationRequest {
  include_anatomy?: boolean;
  include_bugs?: boolean;
  include_memory?: boolean;
  max_anatomy_entries?: number;
  max_bug_entries?: number;
  max_memory_entries?: number;
}

export interface ContextGenerationResponse {
  context: string;
  estimated_tokens: number;
}

export interface SessionContextSummary {
  session_id: string;
  agent_id: string | null;
  created_at: string;
  anatomy: AnatomyStats | null;
  bugs: BugStats | null;
  memory: MemoryStats | null;
  tokens: TokenLedgerSummary | null;
  waste: WasteSummary | null;
  last_scan: ScanResultSummary | null;
}

export interface AnatomyStats {
  total_symbols: number;
  total_files: number;
  languages: Record<string, number>;
}

export interface BugStats {
  total: number;
  open: number;
  resolved: number;
  duplicate: number;
}

export interface MemoryStats {
  total_memories: number;
  by_category: Record<string, number>;
}

export interface TokenLedgerSummary {
  session_id: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_waste_tokens: number;
  waste_rate: number;
  total_cost_usd: number;
  entry_count: number;
  model_breakdown: Record<string, number>;
  provider_breakdown: Record<string, number>;
}

export interface WasteSummary {
  total_waste_tokens: number;
  waste_rate: number;
  pattern_count: number;
}

export interface ScanResultSummary {
  mode: string;
  files_scanned: number;
  symbols_extracted: number;
  duration_seconds: number;
}

// ── Scan ────────────────────────────────────────────────────────────────────

export interface ScanRequest {
  root_path?: string;
  mode?: 'full' | 'incremental';
  changed_files?: string[];
}

export interface ScanStatus {
  task_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  progress?: number;
  result?: ScanResultSummary;
  error?: string;
}

// ── Symbol ──────────────────────────────────────────────────────────────────

export interface SymbolEntry {
  id: string;
  name: string;
  kind: string;
  language: string;
  line_start: number;
  line_end: number;
  signature: string | null;
  description: string | null;
  parent: string | null;
  is_exported: boolean;
  file_path: string;
}

export interface SymbolSearchRequest {
  query: string;
  language?: string;
  kind?: string;
  limit?: number;
}

// ── Bug ─────────────────────────────────────────────────────────────────────

export interface BugEntry {
  id: string;
  session_id: string;
  agent_id: string | null;
  error_type: string;
  error_message: string;
  error_traceback: string | null;
  file_path: string | null;
  line_number: number | null;
  fingerprint: string | null;
  duplicate_of: string | null;
  status: string;
  resolution: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LogBugRequest {
  error_type: string;
  error_message: string;
  error_traceback?: string;
  file_path?: string;
  line_number?: number;
}

export interface UpdateBugStatusRequest {
  status: string;
  resolution?: string;
}

// ── Memory ──────────────────────────────────────────────────────────────────

export interface MemoryEntry {
  id: string;
  key: string;
  value: string;
  category: string;
  confidence: number;
  ttl_seconds: number | null;
  access_count: number;
  last_accessed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RememberRequest {
  key: string;
  value: string;
  category?: string;
  confidence?: number;
}

// ── Waste ───────────────────────────────────────────────────────────────────

export interface WastePattern {
  pattern_type: string;
  severity: string;
  description: string;
  tokens_wasted: number;
  file_path: string | null;
  detected_at: string | null;
}

// ── API Functions ───────────────────────────────────────────────────────────

const BASE = '/contexts';

/** Generate a context string for a session. */
export function generateContext(
  sessionId: string,
  req: ContextGenerationRequest = {},
) {
  return client.post<ContextGenerationResponse>(
    `${BASE}/${sessionId}/generate`,
    req,
  );
}

/** Get a comprehensive session context summary. */
export function getSessionSummary(sessionId: string) {
  return client.get<SessionContextSummary>(`${BASE}/${sessionId}/summary`);
}

// ── Anatomy ─────────────────────────────────────────────────────────────────

/** Start an async anatomy scan. */
export function startScan(sessionId: string, req: ScanRequest = {}) {
  return client.post<ScanStatus>(`${BASE}/${sessionId}/anatomy/scan`, req);
}

/** Get scan task status. */
export function getScanStatus(sessionId: string, taskId: string) {
  return client.get<ScanStatus>(
    `${BASE}/${sessionId}/anatomy/scan/${taskId}`,
  );
}

/** Search anatomy symbols. */
export function searchSymbols(
  sessionId: string,
  req: SymbolSearchRequest,
) {
  return client.post<SymbolEntry[]>(
    `${BASE}/${sessionId}/anatomy/search`,
    req,
  );
}

/** Get anatomy store statistics. */
export function getAnatomyStats(sessionId: string) {
  return client.get<AnatomyStats>(`${BASE}/${sessionId}/anatomy/stats`);
}

// ── Bug Log ─────────────────────────────────────────────────────────────────

/** Log a bug. */
export function logBug(sessionId: string, req: LogBugRequest) {
  return client.post<BugEntry>(`${BASE}/${sessionId}/buglog`, req);
}

/** List recent bugs. */
export function listBugs(
  sessionId: string,
  limit?: number,
  status?: string,
) {
  const params: Record<string, string> = {};
  if (limit !== undefined) params.limit = String(limit);
  if (status) params.status = status;
  return client.get<BugEntry[]>(`${BASE}/${sessionId}/buglog`, params);
}

/** Update bug status. */
export function updateBugStatus(
  sessionId: string,
  bugId: string,
  req: UpdateBugStatusRequest,
) {
  return client.patch<BugEntry>(
    `${BASE}/${sessionId}/buglog/${bugId}`,
    req,
  );
}

/** Get bug statistics. */
export function getBugStats(sessionId: string) {
  return client.get<BugStats>(`${BASE}/${sessionId}/buglog/stats`);
}

// ── Cerebrum (Memory) ───────────────────────────────────────────────────────

/** Store a memory. */
export function remember(sessionId: string, req: RememberRequest) {
  return client.post<MemoryEntry>(`${BASE}/${sessionId}/cerebrum`, req);
}

/** List all memories for a session. */
export function listMemories(sessionId: string) {
  return client.get<MemoryEntry[]>(`${BASE}/${sessionId}/cerebrum`);
}

/** Recall a memory by key. */
export function recall(sessionId: string, key: string) {
  return client.get<MemoryEntry>(`${BASE}/${sessionId}/cerebrum/${key}`);
}

/** Update an existing memory. */
export function updateMemory(
  sessionId: string,
  key: string,
  req: RememberRequest,
) {
  return client.patch<MemoryEntry>(
    `${BASE}/${sessionId}/cerebrum/${key}`,
    req,
  );
}

/** Forget a memory. */
export function forget(sessionId: string, key: string) {
  return client.delete(`${BASE}/${sessionId}/cerebrum/${key}`);
}

/** Get memory statistics. */
export function getMemoryStats(sessionId: string) {
  return client.get<MemoryStats>(`${BASE}/${sessionId}/cerebrum/stats`);
}

// ── Memory System Health ────────────────────────────────────────────────────

export interface MemoryHealth {
  l1_cerebrum: boolean;
  l2_mem0: boolean;
  l3_knowledge: boolean;
}

/** Get memory system health status. */
export function getMemoryHealth() {
  return client.get<MemoryHealth>('/api/memory/health');
}

// ── Token Tracking ──────────────────────────────────────────────────────────

/** Get token usage summary. */
export function getTokenSummary(sessionId: string) {
  return client.get<TokenLedgerSummary>(`${BASE}/${sessionId}/tokens`);
}

/** Get detected waste patterns. */
export function getWastePatterns(sessionId: string) {
  return client.get<WastePattern[]>(`${BASE}/${sessionId}/tokens/waste`);
}