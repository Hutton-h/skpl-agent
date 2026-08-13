import { client, getBaseUrl, getUserId, getToken } from './client';
import type {
	AgentEvent,
	CreateSessionRequest,
	CreateSessionResponse,
	InterruptSessionResponse,
	SessionListResponse,
	SessionRecord,
	UpdateSessionRequest,
	Msg,
} from './types';

export interface MessagesResponse {
	messages: Msg[];
	is_running: boolean;
	has_more: boolean;
}

export const sessionApi = {
	list: (agentId: string) => client.get<SessionListResponse>('/sessions/', { agent_id: agentId }),

	create: (body: CreateSessionRequest) => client.post<CreateSessionResponse>('/sessions/', body),

	update: (sessionId: string, agentId: string, body: UpdateSessionRequest) =>
		client.patch<SessionRecord>(`/sessions/${sessionId}`, body, { agent_id: agentId }),

	delete: (sessionId: string, agentId: string) =>
		client.delete(`/sessions/${sessionId}`, { agent_id: agentId }),

	interrupt: (sessionId: string, agentId: string) =>
		client.post<InterruptSessionResponse>(`/sessions/${sessionId}/interrupt`, null, {
			agent_id: agentId,
		}),

	messages: (sessionId: string, agentId: string, params?: { before?: string; limit?: number }) =>
		client.get<MessagesResponse>(`/sessions/${sessionId}/messages`, {
			agent_id: agentId,
			...(params?.before != null && { before: params.before }),
			...(params?.limit != null && { limit: String(params.limit) }),
		}),

	streamEvents: async function* (
		sessionId: string,
		agentId: string,
		signal?: AbortSignal,
	): AsyncGenerator<AgentEvent> {
		const MAX_RETRY_DELAY_MS = 30_000;
		let retryDelay = 1_000;

		const buildUrl = () => {
			const params = new URLSearchParams({
				agent_id: agentId,
				user_id: getUserId(),
			});
			const token = getToken();
			if (token) {
				params.set('token', token);
			}
			// DEV mode: bypass Vite proxy (http-proxy buffers SSE streams,
			// causing net::ERR_ABORTED) and connect directly to backend.
			// Read the backend port from the Vite proxy config or default to 8001.
			const baseUrl = import.meta.env.DEV
				? "http://127.0.0.1:8001"
				: getBaseUrl();
			return `${baseUrl}/sessions/${encodeURIComponent(sessionId)}/stream?${params}`;
		};

		const onAbort = () => {};
		signal?.addEventListener('abort', onAbort, { once: true });

		try {
			while (true) {
				if (signal?.aborted) break;

				const es = new EventSource(buildUrl());
				const eventQueue: AgentEvent[] = [];
				let resolveNext: ((v: IteratorResult<AgentEvent>) => void) | null = null;
				let closed = false;
				let hasReceivedData = false;

				const finish = () => {
					closed = true;
					if (resolveNext) {
						resolveNext({ value: undefined as never, done: true });
						resolveNext = null;
					}
					es.close();
				};

				es.onmessage = (event: MessageEvent) => {
					hasReceivedData = true;
					try {
						const parsed = JSON.parse(event.data) as AgentEvent;
						if (resolveNext) {
							resolveNext({ value: parsed, done: false });
							resolveNext = null;
						} else {
							eventQueue.push(parsed);
						}
					} catch {
						// Skip malformed events
					}
				};

				es.onerror = () => {
					finish();
				};

				if (signal?.aborted) {
					es.close();
					break;
				}

				const onAbortInner = () => finish();
				signal?.addEventListener('abort', onAbortInner, { once: true });

				try {
					while (true) {
						if (closed && eventQueue.length === 0) break;

						if (eventQueue.length > 0) {
							yield eventQueue.shift()!;
						} else if (!closed) {
							const result = await new Promise<IteratorResult<AgentEvent>>(
								(resolve) => {
									resolveNext = resolve;
								},
							);
							if (result.done) break;
							yield result.value;
						}
					}
				} finally {
					signal?.removeEventListener('abort', onAbortInner);
					es.close();
				}

				if (signal?.aborted) break;

				if (!hasReceivedData) {
					await new Promise((resolve) => setTimeout(resolve, retryDelay));
					retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY_MS);
				} else {
					retryDelay = 1_000;
					await new Promise((resolve) => setTimeout(resolve, 500));
				}
			}
		} finally {
			signal?.removeEventListener('abort', onAbort);
		}
	},
};