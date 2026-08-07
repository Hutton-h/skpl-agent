/**
 * Code Generation API client.
 *
 * Endpoints:
 * - POST /api/code-generation/execute    — execute code task
 * - GET  /api/code-generation/results/{id} — get result
 * - GET  /api/code-generation/results    — list results
 * - POST /api/code-generation/run/python — run Python directly
 * - POST /api/code-generation/run/bash   — run Bash directly
 */
import { client } from './client';

export interface ExecuteCodeRequest {
  task: string;
  context?: string;
  budget?: number;
}

export interface ExecuteCodeResponse {
  task_id: string;
  task_instruction: string;
  completion_reason: string;
  summary: string;
  steps_executed: number;
  budget: number;
  duration_seconds: number;
  execution_history: Array<Record<string, unknown>>;
}

export interface CodeResultResponse {
  task_id: string;
  task_instruction: string;
  completion_reason: string;
  summary: string;
  steps_executed: number;
  duration_seconds: number;
}

export interface CodeResultListItem {
  task_id: string;
  task_instruction: string;
  completion_reason: string;
  steps_executed: number;
}

export interface RunCodeRequest {
  code: string;
  timeout?: number;
}

export interface RunCodeResponse {
  execution_id: string;
  status: string;
  output: string;
  error: string;
  return_code: number;
  duration_seconds: number;
}

export const codeGenerationApi = {
  execute: (body: ExecuteCodeRequest) =>
    client.post<ExecuteCodeResponse>('/api/code-generation/execute', body),

  getResult: (taskId: string) =>
    client.get<CodeResultResponse>(`/api/code-generation/results/${taskId}`),

  listResults: () =>
    client.get<CodeResultListItem[]>('/api/code-generation/results'),

  runPython: (body: RunCodeRequest) =>
    client.post<RunCodeResponse>('/api/code-generation/run/python', body),

  runBash: (body: RunCodeRequest) =>
    client.post<RunCodeResponse>('/api/code-generation/run/bash', body),
};