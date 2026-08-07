# SKPL Agent VS Code Extension

Embeds the SKPL Agent web chat in the VS Code sidebar and lets you ask questions about selected code.

## Install
- Dev: open this folder in VS Code, run `npm install`, then press `F5` to launch an Extension Development Host.
- Package: `npm install -g @vscode/vsce && npm run package`, then install the generated `.vsix` via "Extensions: Install from VSIX...".

## Configure
- `skpl.serverUrl` — URL of your running SKPL frontend (default `http://127.0.0.1:5173`).
- `skpl.autoOpenOnSelection` — auto-focus the chat view when asking about a selection.

## Commands
- `SKPL Agent: Open Chat` (`skpl.openChat`) — focus the sidebar chat view.
- `SKPL Agent: Ask About Selection` (`skpl.askSelection`) — also in the editor right-click menu; sends the selected text to the chat (the web app reads `localStorage["skpl.pendingPrompt"]` or listens for `postMessage` with `{source:"skpl-vscode",type:"ask",text}`).

Start your SKPL backend/frontend first; the extension connects at runtime.
