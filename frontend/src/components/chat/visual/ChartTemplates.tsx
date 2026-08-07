import { useEffect, useRef } from 'react';

/**
 * Reusable chart component for agent-published visuals.
 * 
 * Renders a self-contained HTML/SVG chart inside a sandboxed iframe
 * with auto-height adjustment. This is the recommended way for agents
 * to display charts, tables, and comparisons via publish_visual.
 *
 * Usage by agents (via publish_visual tool):
 *     publish_visual(
 *         title="Q2 Revenue",
 *         visual_type="chart",
 *         html='<svg>...</svg>',
 *         summary="Q2 revenue grew 12% YoY"
 *     )
 */

interface ChartWidgetProps {
  /** The HTML content (SVG or self-contained HTML with inline styles) */
  html: string;
  /** Optional title for accessibility */
  title?: string;
  /** Minimum height in pixels */
  minHeight?: number;
  /** Fallback height when auto-measurement fails */
  fallbackHeight?: number;
}

export function ChartWidget({
  html,
  title = 'Chart',
  minHeight = 200,
  fallbackHeight = 320,
}: ChartWidgetProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const iframe = iframeRef.current;
    if (!iframe) return;

    const handleLoad = () => {
      try {
        const doc = iframe.contentDocument;
        const body = doc?.body;
        if (body) {
          // Inject a script to report actual height
          const script = doc.createElement('script');
          script.textContent = `
            (function() {
              function reportHeight() {
                const h = Math.max(
                  document.body.scrollHeight,
                  document.body.offsetHeight,
                  document.documentElement.clientHeight
                );
                window.parent.postMessage({ type: 'chart-height', height: h }, '*');
              }
              window.addEventListener('load', reportHeight);
              // Also report after a short delay for async-rendered charts
              setTimeout(reportHeight, 500);
              setTimeout(reportHeight, 1500);
            })();
          `;
          body.appendChild(script);
        }
      } catch {
        // Cross-origin — keep fallback height
      }
    };

    iframe.addEventListener('load', handleLoad);
    return () => iframe.removeEventListener('load', handleLoad);
  }, [html]);

  // Listen for height reports from the iframe
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === 'chart-height' && iframeRef.current) {
        const h = Math.max(minHeight, event.data.height);
        iframeRef.current.style.height = `${h}px`;
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [minHeight]);

  return (
    <iframe
      ref={iframeRef}
      sandbox="allow-scripts"
      srcDoc={html}
      title={title}
      style={{
        border: 0,
        width: '100%',
        minHeight,
        height: fallbackHeight,
        background: 'transparent',
        borderRadius: '0.375rem',
      }}
    />
  );
}

/**
 * Pre-built chart templates that agents can use as a starting point.
 * Each function returns an HTML string with inline styles.
 */

export interface ChartData {
  labels: string[];
  values: number[];
  colors?: string[];
}

export interface TableData {
  headers: string[];
  rows: string[][];
}

/** Generate a simple bar chart as SVG */
export function generateBarChart(data: ChartData, title: string): string {
  const colors = data.colors || ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
  const maxVal = Math.max(...data.values, 1);
  const barWidth = 40;
  const gap = 20;
  const chartHeight = 200;
  const chartWidth = data.labels.length * (barWidth + gap) + 40;
  const baseY = chartHeight - 30;

  const bars = data.labels.map((label, i) => {
    const h = (data.values[i] / maxVal) * (chartHeight - 60);
    const x = 30 + i * (barWidth + gap);
    const y = baseY - h;
    const color = colors[i % colors.length];
    return `
      <rect x="${x}" y="${y}" width="${barWidth}" height="${h}" fill="${color}" rx="4">
        <title>${label}: ${data.values[i]}</title>
      </rect>
      <text x="${x + barWidth / 2}" y="${baseY + 18}" text-anchor="middle" font-size="11" fill="#6b7280">${label}</text>
      <text x="${x + barWidth / 2}" y="${y - 8}" text-anchor="middle" font-size="11" fill="#374151" font-weight="600">${data.values[i]}</text>
    `;
  }).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif; background: #fff; }
  h3 { margin: 0 0 16px; font-size: 14px; color: #374151; }
  svg { display: block; }
</style>
</head>
<body>
  <h3>${escapeHtml(title)}</h3>
  <svg width="${chartWidth}" height="${chartHeight}" xmlns="http://www.w3.org/2000/svg">
    <line x1="25" y1="${baseY}" x2="${chartWidth - 10}" y2="${baseY}" stroke="#e5e7eb" stroke-width="1"/>
    ${bars}
  </svg>
</body>
</html>`;
}

/** Generate a simple data table as HTML */
export function generateTable(data: TableData, title: string): string {
  const headerRow = data.headers.map(h => `<th>${escapeHtml(h)}</th>`).join('');
  const rows = data.rows.map(row =>
    `<tr>${row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`
  ).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif; background: #fff; }
  h3 { margin: 0 0 12px; font-size: 14px; color: #374151; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { background: #f3f4f6; padding: 8px 12px; text-align: left; font-weight: 600; color: #374151; border-bottom: 2px solid #e5e7eb; }
  td { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; color: #4b5563; }
  tr:hover td { background: #f9fafb; }
</style>
</head>
<body>
  <h3>${escapeHtml(title)}</h3>
  <table>
    <thead><tr>${headerRow}</tr></thead>
    <tbody>${rows}</tbody>
  </table>
</body>
</html>`;
}

/** Generate a comparison card (side-by-side) */
export function generateComparison(
  left: { title: string; items: string[] },
  right: { title: string; items: string[] },
  title: string
): string {
  const leftItems = left.items.map(i => `<li>${escapeHtml(i)}</li>`).join('');
  const rightItems = right.items.map(i => `<li>${escapeHtml(i)}</li>`).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif; background: #fff; }
  h3 { margin: 0 0 12px; font-size: 14px; color: #374151; }
  .comparison { display: flex; gap: 16px; }
  .column { flex: 1; min-width: 0; }
  .column h4 { font-size: 13px; font-weight: 600; margin: 0 0 8px; padding: 8px 12px; border-radius: 6px; }
  .column:first-child h4 { background: #eff6ff; color: #1d4ed8; }
  .column:last-child h4 { background: #fef2f2; color: #dc2626; }
  ul { margin: 0; padding: 0 0 0 20px; font-size: 13px; color: #4b5563; }
  li { margin-bottom: 4px; }
</style>
</head>
<body>
  <h3>${escapeHtml(title)}</h3>
  <div class="comparison">
    <div class="column">
      <h4>${escapeHtml(left.title)}</h4>
      <ul>${leftItems}</ul>
    </div>
    <div class="column">
      <h4>${escapeHtml(right.title)}</h4>
      <ul>${rightItems}</ul>
    </div>
  </div>
</body>
</html>`;
}

/** Generate a timeline card */
export function generateTimeline(
  events: { time: string; title: string; description?: string }[],
  title: string
): string {
  const items = events.map((e, i) => `
    <div class="event">
      <div class="dot"></div>
      ${i < events.length - 1 ? '<div class="line"></div>' : ''}
      <div class="content">
        <span class="time">${escapeHtml(e.time)}</span>
        <span class="title">${escapeHtml(e.title)}</span>
        ${e.description ? `<span class="desc">${escapeHtml(e.description)}</span>` : ''}
      </div>
    </div>
  `).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif; background: #fff; }
  h3 { margin: 0 0 16px; font-size: 14px; color: #374151; }
  .event { display: flex; align-items: flex-start; position: relative; padding-left: 24px; min-height: 40px; }
  .event:last-child { min-height: 24px; }
  .dot { position: absolute; left: 0; top: 6px; width: 10px; height: 10px; border-radius: 50%; background: #3b82f6; border: 2px solid #bfdbfe; }
  .line { position: absolute; left: 4px; top: 18px; width: 2px; height: calc(100% - 12px); background: #e5e7eb; }
  .content { display: flex; flex-direction: column; gap: 2px; }
  .time { font-size: 11px; color: #9ca3af; }
  .title { font-size: 13px; font-weight: 500; color: #374151; }
  .desc { font-size: 12px; color: #6b7280; }
</style>
</head>
<body>
  <h3>${escapeHtml(title)}</h3>
  ${items}
</body>
</html>`;
}

/** Generate a dashboard card with metrics */
export function generateDashboard(
  metrics: { label: string; value: string; change?: string }[],
  title: string
): string {
  const cards = metrics.map(m => `
    <div class="metric">
      <span class="label">${escapeHtml(m.label)}</span>
      <span class="value">${escapeHtml(m.value)}</span>
      ${m.change ? `<span class="change ${m.change.startsWith('+') ? 'positive' : 'negative'}">${escapeHtml(m.change)}</span>` : ''}
    </div>
  `).join('');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body { margin: 0; padding: 16px; font-family: system-ui, -apple-system, sans-serif; background: #fff; }
  h3 { margin: 0 0 12px; font-size: 14px; color: #374151; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 12px; }
  .metric { background: #f9fafb; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; gap: 4px; }
  .label { font-size: 11px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.5px; }
  .value { font-size: 20px; font-weight: 700; color: #111827; }
  .change { font-size: 12px; }
  .change.positive { color: #10b981; }
  .change.negative { color: #ef4444; }
</style>
</head>
<body>
  <h3>${escapeHtml(title)}</h3>
  <div class="grid">${cards}</div>
</body>
</html>`;
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}