import { lazy, Suspense, useEffect, useState } from 'react';
import { createBrowserRouter, Navigate, RouterProvider } from 'react-router-dom';
import { Toaster } from 'sonner';

import { RouteError } from '@/components/error/RouteError';
import { AppLayout } from '@/components/layout/AppLayout';
import { Spinner } from '@/components/ui/spinner';
import { UploadProvider } from '@/context/UploadContext';
import { dispatchAskPrompt, SKPL_VSCODE_SOURCE } from '@/lib/vscodeBridge';
// ── Eagerly loaded (always needed) ──────────────────────────────────────────
import AdminPage from '@/pages/admin';
import { BugLogPage } from '@/pages/buglog';
import { ChatPage } from '@/pages/chat';
import { CredentialPage } from '@/pages/credential';
import { DashboardPage } from '@/pages/dashboard';
import { KnowledgePage } from '@/pages/knowledge';
import { MorePage } from '@/pages/more';
const WhatsAppPage = lazy(() =>
  import('@/pages/whatsapp').then((mod) => ({ default: mod.default })),
);
import { SchedulePage } from '@/pages/schedule';
import { SettingsPage } from '@/pages/settings';
import { SetupPage } from '@/pages/setup';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import { MobileGuard } from '@/components/auth/MobileGuard';

// ── Lazy loaded (large pages, loaded on demand) ─────────────────────────────
const DesktopPage = lazy(() =>
  import('@/pages/desktop').then((mod) => ({ default: mod.DesktopPage })),
);
const ContextPage = lazy(() =>
  import('@/pages/context').then((mod) => ({ default: mod.ContextPage })),
);
const FirecrawlPage = lazy(() =>
  import('@/pages/firecrawl').then((mod) => ({ default: mod.FirecrawlPage })),
);
const CodeGenerationPage = lazy(() =>
  import('@/pages/code-generation').then((mod) => ({ default: mod.CodeGenerationPage })),
);
const WebIntelligencePage = lazy(() =>
  import('@/pages/web-intelligence').then((mod) => ({ default: mod.WebIntelligencePage })),
);
const AgentMarketPage = lazy(() =>
  import('@/pages/agent-market').then((mod) => ({ default: mod.default })),
);
const UpdatesPage = lazy(() =>
  import('@/pages/updates').then((mod) => ({ default: mod.UpdatesPage })),
);

// ── Lazy-loaded page wrapper ────────────────────────────────────────────────
function LazyPage({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center">
          <Spinner className="h-8 w-8" />
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function SetupPageRoute() {
	const handleComplete = () => {
		// Force a full page reload so App re-checks auth_token and renders the main app
		window.location.href = '/dashboard';
	};
	return (
		<>
			<div className="h-screen">
				<SetupPage onComplete={handleComplete} />
			</div>
			<Toaster richColors position="top-right" />
		</>
	);
}

const router = createBrowserRouter([
	{
		element: <AppLayout />,
		errorElement: <RouteError />,
		children: [
			{
				// Content-level boundary: a crash in a page replaces only
				// the Outlet area, so AppLayout (the icon rail / nav) stays
				// usable. The parent route keeps its own errorElement as a
				// last-resort catch-all for AppLayout/AppSidebar crashes.
				errorElement: <RouteError />,
				children: [
					{ path: '/', element: <Navigate to="/dashboard" replace /> },
					{
						path: '/dashboard',
						element: <ProtectedRoute><DashboardPage /></ProtectedRoute>,
					},
					{
						path: '/chat/:agentId?/:sessionId?/:memberId?',
						element: <ProtectedRoute><ChatPage /></ProtectedRoute>,
					},
					{
						path: '/context',
						element: <ProtectedRoute><LazyPage><ContextPage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/buglog',
						element: <ProtectedRoute><BugLogPage /></ProtectedRoute>,
					},
					{
						path: '/firecrawl',
						element: <ProtectedRoute><LazyPage><FirecrawlPage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/desktop',
						element: <ProtectedRoute><MobileGuard feature="desktop"><LazyPage><DesktopPage /></LazyPage></MobileGuard></ProtectedRoute>,
					},
					{
						path: '/web-intelligence',
						element: <ProtectedRoute><LazyPage><WebIntelligencePage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/code-generation',
						element: <ProtectedRoute><MobileGuard feature="code-generation"><LazyPage><CodeGenerationPage /></LazyPage></MobileGuard></ProtectedRoute>,
					},
					{
						path: '/agent-market',
						element: <ProtectedRoute><LazyPage><AgentMarketPage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/updates',
						element: <ProtectedRoute><LazyPage><UpdatesPage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/schedule',
						element: <ProtectedRoute><SchedulePage /></ProtectedRoute>,
					},
					{
						path: '/credential',
						element: <ProtectedRoute><MobileGuard feature="credential"><CredentialPage /></MobileGuard></ProtectedRoute>,
					},
					{
						path: '/knowledge',
						element: <ProtectedRoute><KnowledgePage /></ProtectedRoute>,
					},
					{
						path: '/knowledge/:kbId',
						element: <ProtectedRoute><KnowledgePage /></ProtectedRoute>,
					},
					{
						path: '/settings',
						element: <ProtectedRoute><SettingsPage /></ProtectedRoute>,
					},
					{
						path: '/admin',
						element: <ProtectedRoute><AdminPage /></ProtectedRoute>,
					},
					{
						path: '/whatsapp',
						element: <ProtectedRoute><LazyPage><WhatsAppPage /></LazyPage></ProtectedRoute>,
					},
					{
						path: '/more',
						element: <ProtectedRoute><MorePage /></ProtectedRoute>,
					},
				],
			},
		],
	},
	{ path: '/setup', element: <SetupPageRoute />, errorElement: <RouteError /> },
]);

function App() {
	const [authenticated, setAuthenticated] = useState(
		() => !!localStorage.getItem('auth_token')
	);

	// VS Code extension bridge: the extension host posts
	// {source:'skpl-vscode', type:'ask', text} into the webview. Persist the
	// prompt and broadcast it so a mounted chat input can fill itself; the
	// stored copy also survives navigation to a later-mounted chat page.
	// The listener lives at the app root so prompts are captured on any page.
	useEffect(() => {
		const handleMessage = (e: MessageEvent) => {
			const data = e.data as
				| { source?: string; type?: string; text?: unknown }
				| undefined;
			if (data?.source !== SKPL_VSCODE_SOURCE || data?.type !== 'ask') return;
			if (typeof data.text !== 'string' || !data.text.trim()) return;
			dispatchAskPrompt(data.text);
		};
		window.addEventListener('message', handleMessage);
		return () => window.removeEventListener('message', handleMessage);
	}, []);

	if (!authenticated) {
		return <SetupPage onComplete={() => setAuthenticated(true)} />;
	}

	return (
		<>
			<UploadProvider>
				<RouterProvider router={router} />
			</UploadProvider>
			<Toaster richColors position="top-right" />
		</>
	);
}

export default App;