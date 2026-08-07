/**
 * Desktop Node API client.
 *
 * Endpoints:
 * - GET /api/desktop/nodes        — list registered desktop nodes
 * - GET /api/desktop/nodes/stats  — node registry statistics
 */
import { client } from './client';

export interface DesktopNode {
  node_id: string;
  node_name: string;
  status: string;  // connecting | online | idle | busy | offline
  os_name: string;
  os_version: string;
  python_version: string;
  screen_width: number;
  screen_height: number;
  cpu_count: number;
  total_memory_mb: number;
  capabilities: string[];
  cpu_percent: number;
  memory_percent: number;
  active_actions: number;
  registered_at: string;
  last_seen: string;
  is_available: boolean;
}

export interface DesktopNodeListResponse {
  nodes: DesktopNode[];
  total: number;
  online_count: number;
}

export const desktopNodeApi = {
  listNodes: () =>
    client.get<DesktopNodeListResponse>('/api/desktop/nodes'),

  getStats: () =>
    client.get<{
      total_nodes: number;
      online_nodes: number;
      offline_nodes: number;
      available_nodes: number;
      by_tenant: Record<string, number>;
      by_os: Record<string, number>;
    }>('/api/desktop/nodes/stats'),
};