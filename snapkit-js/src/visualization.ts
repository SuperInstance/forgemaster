/**
 * Visualization — Terminal + HTML Output
 *
 * Provides zero-dependency visualization utilities for snap-attention:
 * - Terminal-friendly table output (ASCII)
 * - Minimal HTML rendering for browser demos
 * - No external dependencies — works in any modern JS runtime
 *
 * @module
 */

import type {
  SnapResult,
  Delta,
  AttentionAllocation,
} from './types.js';

// ─── Terminal Visualization ──────────────────────────────────────────────────

/**
 * Format a SnapResult as a colored/annotated string for terminal.
 */
export function formatSnapResult(result: SnapResult): string {
  const status = result.withinTolerance ? '✓' : 'Δ';
  return `${status} ${result.original.toFixed(4)} → ${result.snapped.toFixed(4)} (δ=${result.delta.toFixed(4)}, tol=${result.tolerance})`;
}

/**
 * Format a Delta as a string.
 */
export function formatDelta(delta: Delta): string {
  const icon = _severityIcon(delta.severity);
  const isDelta = delta.magnitude > delta.tolerance;
  return isDelta
    ? `${icon} [${delta.streamId}] Δ=${delta.magnitude.toFixed(4)} (exp=${delta.expected.toFixed(4)}) act=${delta.actionability.toFixed(2)} urg=${delta.urgency.toFixed(2)}`
    : `  [${delta.streamId}] — within tolerance (δ=${delta.magnitude.toFixed(4)})`;
}

/**
 * Format an AttentionAllocation as a string.
 */
export function formatAllocation(alloc: AttentionAllocation): string {
  const delta = alloc.delta;
  return `#${alloc.priority} [${delta.streamId}] allocated ${alloc.allocated.toFixed(2)} units — ${alloc.reason}`;
}

/**
 * Render a full pipeline snapshot as a multiline string.
 */
export function formatPipelineSnapshot(
  snapResult: SnapResult,
  deltas?: Delta[],
  allocations?: AttentionAllocation[]
): string {
  const lines: string[] = [];
  lines.push('═══ Snap Pipeline Snapshot ═══');
  lines.push('');
  lines.push('Snap:');
  lines.push(`  ${formatSnapResult(snapResult)}`);
  lines.push('');

  if (deltas && deltas.length > 0) {
    lines.push('Deltas:');
    for (const d of deltas) {
      lines.push(`  ${formatDelta(d)}`);
    }
    lines.push('');
  }

  if (allocations && allocations.length > 0) {
    lines.push('Allocations:');
    for (const a of allocations) {
      lines.push(`  ${formatAllocation(a)}`);
    }
    lines.push('');
  }

  lines.push('════════════════════════════════');
  return lines.join('\n');
}

/**
 * Create an ASCII bar chart of delta magnitudes by stream.
 */
export function deltaBarChart(
  deltas: Record<string, Delta>,
  width: number = 40
): string {
  const entries = Object.entries(deltas).filter(
    ([, d]) => d.magnitude > d.tolerance
  );

  if (entries.length === 0) return '(no deltas to chart)';

  const maxMag = Math.max(...entries.map(([, d]) => d.magnitude));
  const scale = maxMag > 0 ? width / maxMag : 1;

  const lines: string[] = ['Delta Magnitudes:'];

  for (const [id, delta] of entries) {
    const barWidth = Math.round(delta.magnitude * scale);
    const bar = '█'.repeat(Math.max(1, barWidth));
    const icon = _severityIcon(delta.severity);
    lines.push(
      ` ${icon} ${id.padEnd(12)} ${bar} ${delta.magnitude.toFixed(3)}`
    );
  }

  return lines.join('\n');
}

// ─── HTML Visualization ──────────────────────────────────────────────────────

/**
 * Generate a complete HTML page for visualizing snap-attention data.
 *
 * Returns the HTML as a string — no DOM manipulation needed.
 */
export function generateHTMLPage(options: {
  snapResults?: SnapResult[];
  deltas?: Record<string, Delta>;
  allocations?: AttentionAllocation[];
  title?: string;
}): string {
  const title = options.title ?? 'SnapKit Dashboard';

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${_escapeHTML(title)}</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, -apple-system, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 20px; max-width: 1200px; margin: 0 auto; }
h1 { font-size: 1.5rem; margin-bottom: 1rem; color: #00ff88; }
h2 { font-size: 1.1rem; margin: 1.5rem 0 0.5rem; color: #88ccff; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1rem; }
.card { background: #14141f; border: 1px solid #2a2a3f; border-radius: 8px; padding: 1rem; }
.card h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 0.5rem; }
.snap { color: #00ff88; }
.delta { color: #ff8844; }
.critical { color: #ff3344; }
.value { font-size: 1.2rem; font-weight: 600; margin: 0.25rem 0; }
.bar { height: 6px; border-radius: 3px; margin: 0.25rem 0; transition: width 0.3s; }
.bar.snap { background: #00ff88; }
.bar.delta { background: #ff8844; }
.bar.critical { background: #ff3344; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.4rem 0.5rem; text-align: left; border-bottom: 1px solid #2a2a3f; }
th { color: #888; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.05em; }
tr:hover { background: #1a1a2f; }
.priority { display: inline-block; width: 24px; height: 24px; line-height: 24px; text-align: center; border-radius: 50%; background: #2a2a3f; font-size: 0.75rem; font-weight: 600; }
</style>
</head>
<body>
<h1>${_escapeHTML(title)}</h1>
${options.snapResults ? _renderSnapCards(options.snapResults) : ''}
${options.deltas ? _renderDeltaTable(options.deltas) : ''}
${options.allocations ? _renderAllocationCards(options.allocations) : ''}
</body>
</html>`;
}

function _renderSnapCards(results: SnapResult[]): string {
  const rows = results
    .map(
      (r) => `
  <div class="card">
    <h3>original → snapped</h3>
    <div class="value ${r.withinTolerance ? 'snap' : 'delta'}">${r.original.toFixed(4)} → ${r.snapped.toFixed(4)}</div>
    <div class="bar ${r.withinTolerance ? 'snap' : 'delta'}" style="width:${Math.min(100, r.delta / r.tolerance * 50)}%"></div>
    <div>δ = ${r.delta.toFixed(4)} | tol = ${r.tolerance} | ${r.withinTolerance ? '✓ SNAP' : 'Δ DELTA'}</div>
  </div>`
    )
    .join('\n');

  return `<h2>Snap Results</h2><div class="grid">\n${rows}\n</div>`;
}

function _renderDeltaTable(
  deltas: Record<string, Delta>
): string {
  const entries = Object.entries(deltas);
  if (entries.length === 0) return '';

  const rows = entries
    .map(
      ([id, d]) => `
  <tr>
    <td><strong>${_escapeHTML(id)}</strong></td>
    <td class="${_severityClass(d.severity)}">${d.magnitude.toFixed(4)}</td>
    <td>${d.actionability.toFixed(2)}</td>
    <td>${d.urgency.toFixed(2)}</td>
    <td>${d.magnitude > d.tolerance ? '⚠ exceeds' : '✓ within'}</td>
  </tr>`
    )
    .join('\n');

  return `<h2>Delta Streams</h2>
<table>
<thead><tr><th>Stream</th><th>Magnitude</th><th>Actionability</th><th>Urgency</th><th>Status</th></tr></thead>
<tbody>\n${rows}\n</tbody>
</table>`;
}

function _renderAllocationCards(
  allocations: AttentionAllocation[]
): string {
  if (allocations.length === 0) return '';

  const rows = allocations
    .map(
      (a) => `
  <div class="card">
    <h3><span class="priority">${a.priority}</span> ${_escapeHTML(a.delta.streamId)}</h3>
    <div class="value delta">${a.allocated.toFixed(2)} units</div>
    <div style="font-size:0.85rem;color:#888">${_escapeHTML(a.reason)}</div>
    <div style="font-size:0.8rem;margin-top:0.25rem">δ=${a.delta.magnitude.toFixed(3)}, act=${a.delta.actionability.toFixed(2)}, urg=${a.delta.urgency.toFixed(2)}</div>
  </div>`
    )
    .join('\n');

  return `<h2>Attention Allocations</h2><div class="grid">\n${rows}\n</div>`;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function _severityIcon(severity: string): string {
  switch (severity) {
    case 'none':
      return '·';
    case 'low':
      return '⚡';
    case 'medium':
      return '⚠';
    case 'high':
      return '🔥';
    case 'critical':
      return '💥';
    default:
      return '?';
  }
}

function _severityClass(severity: string): string {
  switch (severity) {
    case 'critical':
    case 'high':
      return 'critical';
    case 'medium':
    case 'low':
      return 'delta';
    default:
      return 'snap';
  }
}

function _escapeHTML(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
