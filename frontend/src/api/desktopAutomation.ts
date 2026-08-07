/**
 * Desktop Automation API client.
 *
 * Endpoints:
 * - POST   /api/desktop-automation/sessions                — create session
 * - GET    /api/desktop-automation/sessions                — list sessions
 * - DELETE /api/desktop-automation/sessions/{id}            — delete session
 * - POST   /api/desktop-automation/sessions/{id}/tree       — extract UI tree
 * - POST   /api/desktop-automation/sessions/{id}/actions    — dispatch action
 * - GET    /api/desktop-automation/sessions/{id}/actions    — action history
 * - GET    /api/desktop-automation/actions                  — available actions
 * - POST   /api/desktop-automation/sessions/{id}/screenshot — capture screenshot
 */
import { client } from './client';

export interface TreeElement {
  element_id: number;
  role: string;
  title: string;
  text: string;
}

export interface ExtractTreeResponse {
  tree_text: string;
  elements: TreeElement[];
  element_count: number;
}

export interface DispatchActionRequest {
  action_type: string;
  params: Record<string, unknown>;
}

export interface DispatchActionResponse {
  action_type: string;
  params: Record<string, unknown>;
  code: string;
  timestamp: string;
}

export interface AutomationSession {
  session_id: string;
  status: string;
  action_count: number;
  created_at: string;
  updated_at: string;
}

export interface AvailableAction {
  name: string;
  doc: string;
}

export const desktopAutomationApi = {
  createSession: () =>
    client.post<{ session_id: string; status: string }>(
      '/api/desktop-automation/sessions'
    ),

  listSessions: () =>
    client.get<AutomationSession[]>('/api/desktop-automation/sessions'),

  deleteSession: (sessionId: string) =>
    client.delete(`/api/desktop-automation/sessions/${sessionId}`),

  extractTree: (sessionId: string, showAll = false) =>
    client.post<ExtractTreeResponse>(
      `/api/desktop-automation/sessions/${sessionId}/tree`,
      { show_all: showAll }
    ),

  dispatchAction: (sessionId: string, body: DispatchActionRequest) =>
    client.post<DispatchActionResponse>(
      `/api/desktop-automation/sessions/${sessionId}/actions`,
      body
    ),

  getActionHistory: (sessionId: string) =>
    client.get<{ session_id: string; history: DispatchActionResponse[] }>(
      `/api/desktop-automation/sessions/${sessionId}/actions`
    ),

  listAvailableActions: () =>
    client.get<AvailableAction[]>('/api/desktop-automation/actions'),

  captureScreenshot: (sessionId: string) =>
    client.post<{ session_id: string; image_base64: string; format: string }>(
      `/api/desktop-automation/sessions/${sessionId}/screenshot`
    ),
};