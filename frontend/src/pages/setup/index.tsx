import { useState } from 'react';

import { Button } from '@/components/ui/button.tsx';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card.tsx';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field.tsx';
import { Input } from '@/components/ui/input.tsx';
import { Spinner } from '@/components/ui/spinner.tsx';
import { cn } from '@/lib/utils.ts';

interface Props {
	onComplete: () => void;
	className?: string;
}

type Mode = 'register' | 'login';

const getApiUrl = (): string => {
	if (import.meta.env.DEV) return '';
	const storedUrl = localStorage.getItem('server_url');
	if (storedUrl) {
		try {
			let url = storedUrl.trim();
			if (!/^https?:\/\//i.test(url)) {
				url = 'http://' + url;
			}
			// Fix "localhost8000" → "localhost:8000"
			url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
			url = url.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');
			new URL(url);
			return url;
		} catch {
			console.warn('Invalid server_url, using default');
		}
	}
	return '';
};

export const SetupPage = ({ onComplete, className }: Props) => {
	const [mode, setMode] = useState<Mode>('register');
	const [serverUrl, setServerUrl] = useState(() => localStorage.getItem('server_url') ?? '');
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [error, setError] = useState('');
	const [loading, setLoading] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError('');
		setLoading(true);

		try {
			// Save server URL first (normalize format)
			if (serverUrl) {
				let normalized = serverUrl.trim();
				// Ensure protocol prefix
				if (!/^https?:\/\//i.test(normalized)) {
					normalized = 'http://' + normalized;
				}
				// Fix "localhost8000" → "localhost:8000"
				normalized = normalized.replace(/\/(localhost|127\.0\.0\.1)(\d+)\//, '$1:$2/');
				normalized = normalized.replace(/\/(localhost|127\.0\.0\.1)(\d+)$/, '$1:$2');
				localStorage.setItem('server_url', normalized);
			}

			const baseUrl = getApiUrl();
			const endpoint = mode === 'register' ? '/api/auth/register' : '/api/auth/login';
			const body: Record<string, string> = { username, password };

			const res = await fetch(`${baseUrl}${endpoint}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
			});

			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || `${mode === 'register' ? 'Registration' : 'Login'} failed`);
			}

			const data = await res.json();
			// Store the actual username (not the UUID id)
			localStorage.setItem('auth_token', data.token);
			localStorage.setItem('username', data.user.username);
			localStorage.setItem('user_role', data.user.role);
			onComplete();
			// Navigation handled by App state change: onComplete sets
			// authenticated=true, App renders RouterProvider, router navigates
			// to /dashboard automatically. No window.location.href needed.
		} catch (err) {
			setError(err instanceof Error ? err.message : 'An unexpected error occurred');
		} finally {
			setLoading(false);
		}
	};

	const toggleMode = () => {
		setMode(mode === 'register' ? 'login' : 'register');
		setError('');
	};

	return (
		<div className="flex items-center justify-center h-full">
			<div className={cn('flex flex-col gap-6 w-full max-w-sm', className)}>
				<Card>
					<CardHeader>
						<CardTitle>
							{mode === 'register' ? 'Setup & Register' : 'Sign In'}
						</CardTitle>
						<CardDescription>
							{mode === 'register'
								? 'Configure your server and create your account'
								: 'Sign in to your existing account'}
						</CardDescription>
					</CardHeader>
					<CardContent>
						<form onSubmit={handleSubmit}>
							<FieldGroup>
								{mode === 'register' && (
									<Field>
										<FieldLabel htmlFor="server-url-input">
											Server URL
										</FieldLabel>
										<Input
											id="server-url-input"
											type="text"
											placeholder="http://your-server:8000"
											value={serverUrl}
											onChange={(e) => setServerUrl(e.target.value)}
											required
										/>
									</Field>
								)}
								<Field>
									<FieldLabel htmlFor="username-input">
										Username
									</FieldLabel>
									<Input
										id="username-input"
										type="text"
										placeholder="Enter your username"
										value={username}
										onChange={(e) => setUsername(e.target.value)}
										required
										minLength={3}
										autoComplete="username"
									/>
								</Field>
								<Field>
									<FieldLabel htmlFor="password-input">
										Password
									</FieldLabel>
									<Input
										id="password-input"
										type="password"
										placeholder={mode === 'register' ? 'Min 8 characters' : 'Enter your password'}
										value={password}
										onChange={(e) => setPassword(e.target.value)}
										required
										minLength={mode === 'register' ? 8 : undefined}
										autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
									/>
								</Field>
								{error && (
									<FieldDescription className="text-red-500 text-sm">
										{error}
									</FieldDescription>
								)}
								<Field>
									<Button type="submit" className="w-full" disabled={loading}>
										{loading ? (
											<Spinner className="h-4 w-4 mr-2" />
										) : null}
										{mode === 'register' ? 'Register' : 'Sign In'}
									</Button>
								</Field>
							</FieldGroup>
						</form>
					</CardContent>
				</Card>
				<FieldDescription className="px-6 text-center">
					{mode === 'register' ? (
						<>
							Already have an account?{' '}
							<button
								type="button"
								onClick={toggleMode}
								className="underline underline-offset-2 hover:text-foreground"
							>
								Sign in
							</button>
						</>
					) : (
						<>
							Don't have an account?{' '}
							<button
								type="button"
								onClick={toggleMode}
								className="underline underline-offset-2 hover:text-foreground"
							>
								Register
							</button>
						</>
					)}
				</FieldDescription>
			</div>
		</div>
	);
};