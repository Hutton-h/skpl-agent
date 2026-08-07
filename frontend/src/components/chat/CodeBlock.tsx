import { Check, Copy } from 'lucide-react';
import React, { useCallback, useState } from 'react';

import { cn } from '@/lib/utils';

/** Props for the CodeBlock component */
interface CodeBlockProps {
  /** The code content to display */
  children: string;
  /** Programming language for syntax label */
  className?: string;
  /** Whether this is inline code (vs block code) */
  inline?: boolean;
}

/**
 * Secure code block renderer for ReactMarkdown.
 *
 * Renders code blocks with syntax highlighting label and copy button.
 * Uses ONLY React component composition — never dangerouslySetInnerHTML.
 * This prevents XSS attacks while still providing a polished code display.
 */
export function CodeBlock({
  children,
  className,
  inline,
}: CodeBlockProps): React.ReactElement {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available, fallback silently
    }
  }, [children]);

  // Extract language from className (format: "language-xxx")
  const language = className?.replace('language-', '') || '';

  // Inline code: simple styled span
  if (inline) {
    return (
      <code className="rounded bg-muted px-1.5 py-0.5 text-sm font-mono">
        {children}
      </code>
    );
  }

  // Block code: full container with header and copy button
  return (
    <div className="group relative my-3 rounded-lg border bg-muted/30">
      {/* Header bar */}
      <div className="flex items-center justify-between rounded-t-lg border-b bg-muted/50 px-4 py-2">
        <span className="text-xs font-medium text-muted-foreground">
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className={cn(
            'flex items-center gap-1 rounded px-2 py-1 text-xs transition-colors',
            'hover:bg-muted',
            copied ? 'text-green-500' : 'text-muted-foreground',
          )}
          aria-label={copied ? 'Copied' : 'Copy code'}
        >
          {copied ? (
            <Check className="h-3 w-3" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>

      {/* Code content — rendered as plain text, NO dangerouslySetInnerHTML */}
      <pre className="overflow-x-auto p-4 text-sm leading-relaxed">
        <code className={cn('font-mono text-sm', className)}>
          {children}
        </code>
      </pre>
    </div>
  );
}