import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { TooltipProvider } from '@/components/ui/tooltip';

import './index.css';
import './i18n';
import App from './App';

// ── PWA: Service Worker DISABLED ───────────────────────────────────────────
// SW is disabled in all environments until caching issues are resolved.
// To re-enable, restore the registerSW() function below.
async function cleanupSW() {
  if ('serviceWorker' in navigator) {
    const regs = await navigator.serviceWorker.getRegistrations();
    for (const r of regs) {
      console.log('[PWA] Unregistering old SW:', r.scope);
      await r.unregister();
    }
  }
  if ('caches' in window) {
    const keys = await caches.keys();
    for (const key of keys) {
      console.log('[PWA] Deleting old cache:', key);
      await caches.delete(key);
    }
  }
}
cleanupSW();

createRoot(document.getElementById('root')!).render(
	<StrictMode>
		<TooltipProvider>
			<App />
		</TooltipProvider>
	</StrictMode>,
);