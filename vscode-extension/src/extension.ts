// SKPL Agent VS Code extension: embeds the SKPL web chat in a sidebar webview,
// provides inline code completions, and exposes skill commands via the palette.
import * as vscode from 'vscode';
import * as path from 'path';

const LOG_PREFIX = '[SKPL]';

// ── Configuration ──────────────────────────────────────────────────────────

function serverUrl(): string {
  return vscode.workspace
    .getConfiguration('skpl')
    .get<string>('serverUrl', 'http://127.0.0.1:5173');
}

function backendUrl(): string {
  return vscode.workspace
    .getConfiguration('skpl')
    .get<string>('backendUrl', 'http://127.0.0.1:8000');
}

function getToken(context: vscode.ExtensionContext): string | undefined {
  return context.globalState.get<string>('skpl.token');
}

// ── Chat View Provider ─────────────────────────────────────────────────────

class SkplChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'skpl.chatView';
  private view?: vscode.WebviewView;

  constructor(private readonly context: vscode.ExtensionContext) {}

  public resolveWebviewView(webviewView: vscode.WebviewView): void {
    this.view = webviewView;
    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.context.extensionUri],
    };
    webviewView.webview.html = this.buildHtml(serverUrl());
    console.log(`${LOG_PREFIX} chat view resolved`);

    // Listen for messages from the webview
    webviewView.webview.onDidReceiveMessage((msg) => {
      if (msg.type === 'ready') {
        console.log(`${LOG_PREFIX} webview ready`);
      } else if (msg.type === 'auth' && msg.token) {
        this.context.globalState.update('skpl.token', msg.token);
      }
    });
  }

  public postPrompt(text: string): void {
    this.view?.webview.postMessage({ type: 'ask', text });
  }

  public postContext(context: { file?: string; selection?: string; language?: string }): void {
    this.view?.webview.postMessage({ type: 'context', ...context });
  }

  private buildHtml(serverUrl: string): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>html,body{margin:0;padding:0;height:100%;overflow:hidden}iframe{border:0;width:100%;height:100%}</style>
</head>
<body>
<iframe id="skpl-frame" src="${serverUrl}" allow="clipboard-read; clipboard-write"></iframe>
<script>
  const frame = document.getElementById('skpl-frame');
  function deliver(text) {
    try {
      frame.contentWindow.localStorage.setItem('skpl.pendingPrompt', text);
    } catch (err) { /* cross-origin */ }
    frame.contentWindow.postMessage({ source: 'skpl-vscode', type: 'ask', text: text }, '*');
  }
  // Forward messages from extension to iframe
  window.addEventListener('message', (event) => {
    const msg = event.data;
    if (msg && msg.source === 'skpl-vscode') {
      frame.contentWindow.postMessage(msg, '*');
    }
  });
  // Notify extension when iframe is ready
  frame.addEventListener('load', () => {
    const vscode = acquireVsCodeApi();
    vscode.postMessage({ type: 'ready' });
  });
</script>
</body>
</html>`;
  }
}

// ── Inline Completion Provider ─────────────────────────────────────────────

class SkplInlineCompletionProvider implements vscode.InlineCompletionItemProvider {
  private abortController: AbortController | null = null;

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionList | vscode.InlineCompletionItem[]> {
    // Skip if triggered by backspace or explicit undo
    if (context.triggerKind === vscode.InlineCompletionTriggerKind.Automatic) {
      // Only trigger after typing at least 3 characters
      const line = document.lineAt(position.line);
      if (line.text.trim().length < 3) return [];
    }

    // Cancel any pending request
    this.abortController?.abort();
    this.abortController = new AbortController();

    const backend = backendUrl();
    if (!backend) return [];

    // Get context: current file content up to cursor
    const startLine = Math.max(0, position.line - 50);
    const prefix = document.getText(
      new vscode.Range(startLine, 0, position.line, position.character)
    );
    const suffix = document.getText(
      new vscode.Range(position.line, position.character, Math.min(document.lineCount - 1, position.line + 5), 0)
    );

    try {
      const response = await fetch(`${backend}/code-generation/complete`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${getToken(this.context)}`,
        },
        body: JSON.stringify({
          prefix,
          suffix,
          language: document.languageId,
          file_path: document.fileName,
          max_tokens: 100,
          temperature: 0.2,
        }),
        signal: this.abortController.signal,
      });

      if (!response.ok) return [];

      const data = await response.json() as { completions?: string[] };
      const completions = data.completions || [];

      return completions.map(text => new vscode.InlineCompletionItem(text));
    } catch {
      return [];
    }
  }
}

// ── Status Bar ─────────────────────────────────────────────────────────────

class SkplStatusBar {
  private item: vscode.StatusBarItem;

  constructor() {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = 'skpl.openChat';
    this.item.text = '$(hubot) SKPL';
    this.item.tooltip = 'Open SKPL Agent chat';
    this.item.show();
  }

  setConnected(connected: boolean) {
    this.item.text = connected ? '$(hubot) SKPL' : '$(circle-slash) SKPL';
    this.item.tooltip = connected
      ? 'SKPL Agent connected'
      : 'SKPL Agent disconnected — click to open chat';
  }

  dispose() {
    this.item.dispose();
  }
}

// ── Extension Activation ───────────────────────────────────────────────────

export function activate(context: vscode.ExtensionContext): void {
  console.log(`${LOG_PREFIX} extension activated`);

  // ── Chat View ────────────────────────────────────────────────────────
  const provider = new SkplChatViewProvider(context);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(SkplChatViewProvider.viewType, provider, {
      webviewOptions: { retainContextWhenHidden: true },
    })
  );

  // ── Status Bar ───────────────────────────────────────────────────────
  const statusBar = new SkplStatusBar();
  context.subscriptions.push(statusBar);

  // ── Commands ─────────────────────────────────────────────────────────
  // Open chat
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.openChat', async () => {
      await vscode.commands.executeCommand('skpl.chatView.focus');
      console.log(`${LOG_PREFIX} openChat: chat view focused`);
    })
  );

  // Ask about selection
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.askSelection', async () => {
      const editor = vscode.window.activeTextEditor;
      const selection = editor?.selection;
      const text = editor && selection && !selection.isEmpty
        ? editor.document.getText(selection)
        : '';
      if (!text) {
        vscode.window.showInformationMessage('SKPL Agent: select some text first.');
        return;
      }
      await vscode.commands.executeCommand('skpl.chatView.focus');
      // Share context with the chat
      provider.postContext({
        file: editor.document.fileName,
        selection: text,
        language: editor.document.languageId,
      });
      provider.postPrompt(text);
      console.log(`${LOG_PREFIX} askSelection: prompt forwarded (${text.length} chars)`);
    })
  );

  // Explain code
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.explainCode', async () => {
      const editor = vscode.window.activeTextEditor;
      const selection = editor?.selection;
      const text = editor && selection && !selection.isEmpty
        ? editor.document.getText(selection)
        : editor?.document.getText();
      if (!text) {
        vscode.window.showInformationMessage('SKPL Agent: no code to explain.');
        return;
      }
      await vscode.commands.executeCommand('skpl.chatView.focus');
      provider.postContext({
        file: editor!.document.fileName,
        selection: text.substring(0, 500),
        language: editor!.document.languageId,
      });
      provider.postPrompt(`Explain this code:\n\`\`\`${editor!.document.languageId}\n${text.substring(0, 1000)}\n\`\`\``);
    })
  );

  // Review code
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.reviewCode', async () => {
      const editor = vscode.window.activeTextEditor;
      const text = editor?.document.getText();
      if (!text) {
        vscode.window.showInformationMessage('SKPL Agent: no code to review.');
        return;
      }
      await vscode.commands.executeCommand('skpl.chatView.focus');
      provider.postContext({
        file: editor!.document.fileName,
        language: editor!.document.languageId,
      });
      provider.postPrompt(`Review this code for quality, security, and best practices. Use the code-review skill:\n\`\`\`${editor!.document.languageId}\n${text.substring(0, 2000)}\n\`\`\``);
    })
  );

  // Debug error
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.debugError', async () => {
      // Try to get the current error from the problems panel
      const diagnostics = vscode.languages.getDiagnostics();
      const errors = diagnostics
        .flatMap(([uri, diags]) => diags.filter(d => d.severity === vscode.DiagnosticSeverity.Error).map(d => ({ uri, message: d.message, line: d.range.start.line })))
        .slice(0, 5);

      if (errors.length === 0) {
        vscode.window.showInformationMessage('SKPL Agent: no errors found in the workspace.');
        return;
      }

      await vscode.commands.executeCommand('skpl.chatView.focus');
      const errorList = errors.map(e => `- ${path.basename(e.uri.fsPath)}:${e.line + 1}: ${e.message}`).join('\n');
      provider.postPrompt(`Help me debug these errors. Use the debug-assistant skill:\n${errorList}`);
    })
  );

  // Generate tests
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.generateTests', async () => {
      const editor = vscode.window.activeTextEditor;
      const text = editor?.document.getText();
      if (!text) {
        vscode.window.showInformationMessage('SKPL Agent: open a file to generate tests for.');
        return;
      }
      await vscode.commands.executeCommand('skpl.chatView.focus');
      provider.postContext({
        file: editor!.document.fileName,
        language: editor!.document.languageId,
      });
      provider.postPrompt(`Generate comprehensive tests for this code. Use the test-generator skill:\n\`\`\`${editor!.document.languageId}\n${text.substring(0, 2000)}\n\`\`\``);
    })
  );

  // Optimize / refactor code
  context.subscriptions.push(
    vscode.commands.registerCommand('skpl.refactorCode', async () => {
      const editor = vscode.window.activeTextEditor;
      const selection = editor?.selection;
      const text = selection && !selection.isEmpty
        ? editor.document.getText(selection)
        : editor?.document.getText();
      if (!text) {
        vscode.window.showInformationMessage('SKPL Agent: select code to refactor.');
        return;
      }
      await vscode.commands.executeCommand('skpl.chatView.focus');
      provider.postContext({
        file: editor!.document.fileName,
        selection: text.substring(0, 500),
        language: editor!.document.languageId,
      });
      provider.postPrompt(`Refactor this code to improve readability and maintainability. Use the refactor-assistant skill:\n\`\`\`${editor!.document.languageId}\n${text.substring(0, 2000)}\n\`\`\``);
    })
  );

  // ── Inline Completion Provider ───────────────────────────────────────
  // Only register if enabled in settings
  const enableInlineCompletion = vscode.workspace
    .getConfiguration('skpl')
    .get<boolean>('enableInlineCompletion', false);

  if (enableInlineCompletion) {
    context.subscriptions.push(
      vscode.languages.registerInlineCompletionItemProvider(
        { pattern: '**' },
        new SkplInlineCompletionProvider()
      )
    );
    console.log(`${LOG_PREFIX} inline completion provider registered`);
  }

  // ── Check backend health ─────────────────────────────────────────────
  checkBackendHealth(statusBar);
}

// ── Health Check ───────────────────────────────────────────────────────────

async function checkBackendHealth(statusBar: SkplStatusBar): Promise<void> {
  const url = backendUrl();
  if (!url) return;

  try {
    const response = await fetch(`${url}/health`, { signal: AbortSignal.timeout(3000) });
    statusBar.setConnected(response.ok);
  } catch {
    statusBar.setConnected(false);
  }
}

export function deactivate(): void {
  console.log(`${LOG_PREFIX} extension deactivated`);
}