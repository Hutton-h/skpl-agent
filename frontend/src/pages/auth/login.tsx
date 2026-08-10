import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getBaseUrl, setAuth } from '@/api/client';
import { Button } from '@/components/ui/button';
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from '@/components/ui/card';
import { Field, FieldDescription, FieldGroup, FieldLabel } from '@/components/ui/field';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/spinner';
import { cn } from '@/lib/utils';

interface Props {
	className?: string;
}

type Mode = 'login' | 'register';

export const LoginPage = ({ className }: Props) => {
	const navigate = useNavigate();
	const [mode, setMode] = useState<Mode>('login');
	const [username, setUsername] = useState('');
	const [password, setPassword] = useState('');
	const [email, setEmail] = useState('');
	const [error, setError] = useState('');
	const [loading, setLoading] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError('');
		setLoading(true);

		try {
			const baseUrl = getBaseUrl();
			const endpoint = mode === 'login' ? '/api/auth/login' : '/api/auth/register';
			const body: Record<string, string> = { username, password };
			if (mode === 'register' && email) {
				body.email = email;
			}

			const res = await fetch(`${baseUrl}${endpoint}`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(body),
			});

			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || `${mode === 'login' ? 'Login' : 'Registration'} failed`);
			}

			const data = await res.json();
			setAuth(data.token, data.user.id, data.user.username);
			localStorage.setItem('user_role', data.user.role);
			navigate('/dashboard', { replace: true });
		} catch (err) {
			setError(err instanceof Error ? err.message : 'An unexpected error occurred');
		} finally {
			setLoading(false);
		}
	};

	const toggleMode = () => {
		setMode(mode === 'login' ? 'register' : 'login');
		setError('');
	};

	const serverUrl = import.meta.env.DEV ? 'Vite Proxy (dev mode)' : (localStorage.getItem('server_url') || 'Not configured');

	const handleChangeServer = () => {
		localStorage.removeItem('server_url');
		window.location.href = '/setup';
	};

	return (
		<div className="flex items-center justify-center h-full">
			<div className={cn('flex flex-col gap-6 w-full max-w-sm', className)}>
				<Card>
					<CardHeader>
						<CardTitle>
							{mode === 'login' ? 'Sign In' : 'Create Account'}
						</CardTitle>
						<CardDescription>
							{mode === 'login'
								? 'Enter your credentials to access your account'
								: 'Create a new account to get started'}
						</CardDescription>
						<CardDescription className="text-xs text-muted-foreground mt-1">
							Server: {serverUrl}
						</CardDescription>
					</CardHeader>
					<CardContent>
						<form onSubmit={handleSubmit}>
							<FieldGroup>
								<Field>
									<FieldLabel htmlFor="auth-username">Username</FieldLabel>
									<Input
										id="auth-username"
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
									<FieldLabel htmlFor="auth-password">Password</FieldLabel>
									<Input
										id="auth-password"
										type="password"
										placeholder={mode === 'register' ? 'Min 8 characters' : 'Enter your password'}
										value={password}
										onChange={(e) => setPassword(e.target.value)}
										required
										minLength={mode === 'register' ? 8 : undefined}
										autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
									/>
								</Field>
								{mode === 'register' && (
									<Field>
										<FieldLabel htmlFor="auth-email">Email (optional)</FieldLabel>
										<Input
											id="auth-email"
											type="email"
											placeholder="your@email.com"
											value={email}
											onChange={(e) => setEmail(e.target.value)}
											autoComplete="email"
										/>
									</Field>
								)}
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
										{mode === 'login' ? 'Sign In' : 'Create Account'}
									</Button>
								</Field>
							</FieldGroup>
						</form>
					</CardContent>
				</Card>
				<FieldDescription className="px-6 text-center">
					{mode === 'login' ? (
						<>
							Don't have an account?{' '}
							<button
								type="button"
								onClick={toggleMode}
								className="underline underline-offset-2 hover:text-foreground"
							>
								Create one
							</button>
						</>
					) : (
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
					)}
				</FieldDescription>
				{!import.meta.env.DEV && (
					<FieldDescription className="px-6 text-center">
						<button
							type="button"
							onClick={handleChangeServer}
							className="underline underline-offset-2 hover:text-foreground text-muted-foreground"
						>
							Change server
						</button>
					</FieldDescription>
				)}
			</div>
		</div>
	);
};