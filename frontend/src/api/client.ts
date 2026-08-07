import { toast } from 'sonner';

export const getBaseUrl = () => {
  // In dev mode, Vite proxy handles API routing
  if (import.meta.env.DEV) {
    return '';
  }
  // In production, use the server URL configured in setup page.
  // Validate and normalize to prevent common mistakes like
  // "localhost8000" (missing colon before port).
  const storedUrl = localStorage.getItem('server_url');
  if (storedUrl) {
    try {
      // Ensure protocol prefix
      let url = storedUrl.trim();
      if (!/^https?:\/\//i.test(url)) {
        url = 'http://' + url;
      }
      // Fix "localhost8000" → "localhost:8000" (missing colon before port)
      url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
      // Also fix the end of hostname: "localhost8000" at end of string
      url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');
      new URL(url); // throws if still invalid
      return url;
    } catch {
      // Invalid URL — fall through to default
      console.warn('Invalid server_url in localStorage, using default');
    }
  }
  return 'http://localhost:8000';
};
export const getUserId = () => localStorage.getItem('username') || 'dev-user';

/** Get the stored JWT token, if any. */
export const getToken = (): string | null => localStorage.getItem('auth_token');

/** Store a JWT token and user info after login/register. */
export const setAuth = (token: string, userId: string) => {
	localStorage.setItem('auth_token', token);
	localStorage.setItem('username', userId);
};

/** Clear auth state (logout). */
export const clearAuth = () => {
	localStorage.removeItem('auth_token');
	// Keep username for backward compatibility with X-User-ID mode
};

/** Check if the user is authenticated with a JWT token. */
export const isAuthenticated = (): boolean => {
	return !!getToken();
};

/**
 * Structured error thrown for non-2xx HTTP responses.
 * `message` contains the human-readable detail extracted from the backend.
 */
export class ApiError extends Error {
	readonly status: number;
	readonly detail: string;

	constructor(status: number, detail: string) {
		super(detail);
		this.name = 'ApiError';
		this.status = status;
		this.detail = detail;
	}
}

interface RequestOptions {
	method?: string;
	body?: unknown;
	params?: Record<string, string>;
	/** When true, suppresses the automatic error toast. Useful when the caller shows its own inline error UI. */
	silent?: boolean;
}

function buildHeaders(hasBody: boolean): Record<string, string> {
	const headers: Record<string, string> = {};
	// JWT token takes priority -- no guest/fallback X-User-ID
	const token = getToken();
	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}
	if (hasBody) headers['Content-Type'] = 'application/json';
	return headers;
}

/** Parse the response body and extract the `detail` field if the backend returned JSON. */
async function extractErrorDetail(res: Response): Promise<string> {
	const text = await res.text();
	try {
		const json = JSON.parse(text) as { detail?: unknown };
		if (typeof json.detail === 'string') return json.detail;
		if (json.detail !== undefined) return JSON.stringify(json.detail);
	} catch {
		// not JSON – fall through
	}
	return text || res.statusText;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
	const { method = 'GET', body, params, silent = false } = options;
	const baseUrl = getBaseUrl();
	const url = baseUrl ? new URL(path, baseUrl).toString() : path;
	const queryString = params ? '?' + new URLSearchParams(params).toString() : '';

	const res = await fetch(url + queryString, {
		method,
		headers: buildHeaders(body !== undefined),
		body: body ? JSON.stringify(body) : undefined,
	});

	if (!res.ok) {
		const detail = await extractErrorDetail(res);
		const error = new ApiError(res.status, detail);
		if (!silent) toast.error(detail);
		throw error;
	}

	if (res.status === 204) return undefined as T;
	return res.json() as Promise<T>;
}

async function streamRequest(
	path: string,
	options: RequestOptions & { signal?: AbortSignal } = {},
): Promise<Response> {
	const { method = 'GET', body, params, silent = false } = options;
	const baseUrl = getBaseUrl();
	const url = baseUrl ? new URL(path, baseUrl).toString() : path;
	const queryString = params ? '?' + new URLSearchParams(params).toString() : '';

	// Deliberately omit `signal` from fetch — passing it causes
	// `net::ERR_ABORTED` in the browser console on every navigation.
	// The caller cancels via `reader.cancel()` instead, which is a
	// clean stream-level teardown that the browser treats as a normal
	// close rather than a network error.
	const res = await fetch(url + queryString, {
		method,
		headers: buildHeaders(body !== undefined),
		body: body ? JSON.stringify(body) : undefined,
	});

	if (!res.ok) {
		const detail = await extractErrorDetail(res);
		const error = new ApiError(res.status, detail);
		if (!silent) toast.error(detail);
		throw error;
	}

	return res;
}

export const client = {
	get: <T>(path: string, params?: Record<string, string>) =>
		request<T>(path, { method: 'GET', params }),
	post: <T>(
		path: string,
		body?: unknown,
		params?: Record<string, string>,
		options?: { silent?: boolean },
	) => request<T>(path, { method: 'POST', body, params, silent: options?.silent }),
	patch: <T>(
		path: string,
		body?: unknown,
		params?: Record<string, string>,
		options?: { silent?: boolean },
	) => request<T>(path, { method: 'PATCH', body, params, silent: options?.silent }),
	put: <T>(
		path: string,
		body?: unknown,
		params?: Record<string, string>,
		options?: { silent?: boolean },
	) => request<T>(path, { method: 'PUT', body, params, silent: options?.silent }),
	delete: <T = void>(path: string, params?: Record<string, string>) =>
		request<T>(path, { method: 'DELETE', params }),
	stream: (path: string, options?: RequestOptions & { signal?: AbortSignal }) =>
		streamRequest(path, { ...options, silent: options?.silent ?? true }),
};
