/**
 * VS Code Extension Bridge
 *
 * Provides communication between the SKPL web frontend and the VS Code extension.
 * Used to dispatch prompts from VS Code into the SKPL Agent chat interface.
 */

export const SKPL_VSCODE_SOURCE = "vscode";
export const SKPL_ASK_EVENT = "skpl:ask";

/** Dispatch an ask prompt from VS Code extension into the web app */
export function dispatchAskPrompt(prompt: string, source: string = SKPL_VSCODE_SOURCE) {
  window.dispatchEvent(
    new CustomEvent(SKPL_ASK_EVENT, {
      detail: { prompt, source },
    })
  );
}

/** Take a pending prompt from VS Code (if any) and return it, clearing the queue */
export function takePendingPrompt(): { prompt: string; source: string } | null {
  // Check if there's a pending prompt stored by the VS Code bridge
  const pending = (window as any).__skpl_pending_prompt;
  if (pending) {
    (window as any).__skpl_pending_prompt = null;
    return pending;
  }
  return null;
}

/** Listen for ask events from VS Code */
export function onAskPrompt(callback: (prompt: string, source: string) => void): () => void {
  const handler = (event: Event) => {
    const detail = (event as CustomEvent).detail;
    if (detail?.prompt) {
      callback(detail.prompt, detail.source || SKPL_VSCODE_SOURCE);
    }
  };
  window.addEventListener(SKPL_ASK_EVENT, handler);
  return () => window.removeEventListener(SKPL_ASK_EVENT, handler);
}