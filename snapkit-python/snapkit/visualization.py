"""
visualization.py — Terminal + HTML Visualization
=================================================

Zero external dependencies (stdlib + numpy only).

Provides:
- Terminal tables with box-drawing characters
- ASCII bar/line charts for time series
- Self-contained HTML reports
- Human-readable snap results interpretation
- Multi-panel terminal dashboard
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import html as html_mod
import io


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _color_code(value: float, lo: float = 0.0, hi: float = 1.0) -> str:
    """
    Simple ANSI color code based on value relative to range.
    
    Returns ANSI color string: red=bad, yellow=warning, green=good.
    """
    norm = _clamp((value - lo) / max(hi - lo, 0.01))
    if norm < 0.33:
        return '\033[32m'  # Green
    elif norm < 0.66:
        return '\033[33m'  # Yellow
    return '\033[31m'       # Red


def terminal_table(
    headers: List[str],
    rows: List[List[str]],
    title: str = "",
    color_column: Optional[int] = None,
) -> str:
    """
    Render a table with box-drawing characters.
    
    Args:
        headers: Column headers.
        rows: List of rows, each a list of string values.
        title: Optional title above table.
        color_column: Index of column to use for row coloring (-1 = no color).
    
    Returns:
        String with box-drawing table.
    
    Examples:
        >>> print(terminal_table(
        ...     ['Stream', 'Deltas', 'Budget'],
        ...     [['cpu', '12', '45%'], ['mem', '3', '20%']],
        ...     title="Stream Monitor"
        ... ))
    """
    if not headers or not rows:
        return "<empty table>"
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Build table
    buf = io.StringIO()
    
    # Title
    if title:
        total_width = sum(col_widths) + len(col_widths) * 3 + 1
        buf.write(f"  {title}\n")
    
    # Top border
    top = '┌' + '┬'.join('─' * (w + 2) for w in col_widths) + '┐'
    buf.write(top + '\n')
    
    # Header row
    header = '│'
    for i, h in enumerate(headers):
        header += f' {str(h).center(col_widths[i])} │'
    buf.write(header + '\n')
    
    # Header separator
    sep = '├' + '┼'.join('─' * (w + 2) for w in col_widths) + '┤'
    buf.write(sep + '\n')
    
    # Data rows
    for row_idx, row in enumerate(rows):
        line = '│'
        for i, cell in enumerate(row):
            padded = str(cell).ljust(col_widths[i])
            if color_column is not None and i == color_column:
                try:
                    val = float(cell.rstrip('%'))
                    color = _color_code(val, 0, 100)
                    line += f' {color}{padded}\033[0m │'
                except (ValueError, IndexError):
                    line += f' {padded} │'
            else:
                line += f' {padded} │'
        buf.write(line + '\n')
    
    # Bottom border
    bottom = '└' + '┴'.join('─' * (w + 2) for w in col_widths) + '┘'
    buf.write(bottom + '\n')
    
    return buf.getvalue()


def ascii_chart(
    values: List[float],
    width: int = 40,
    height: int = 10,
    title: str = "",
    symbol: str = '█',
) -> str:
    """
    Render an ASCII bar or line chart.
    
    Args:
        values: Data points to chart.
        width: Chart width in characters.
        height: Chart height in lines.
        title: Optional title.
        symbol: Character to use for bars.
    
    Returns:
        String with ASCII chart.
    
    Examples:
        >>> chart = ascii_chart([0.1, 0.5, 0.8, 0.3, 0.6],
        ...                     width=30, height=8, title="Delta Magnitudes")
        >>> print(chart)
    """
    if not values:
        return "<empty chart>"
    
    buf = io.StringIO()
    
    if title:
        buf.write(f"  {title}\n")
    
    # Downsample if too many values
    if len(values) > width:
        indices = np.linspace(0, len(values) - 1, width, dtype=int)
        display_values = [values[i] for i in indices]
    else:
        display_values = list(values)
    
    vmin, vmax = min(display_values), max(display_values)
    vrange = max(vmax - vmin, 0.001)
    
    # Y-axis labels
    for row in range(height, 0, -1):
        level = vmin + (vrange * row / height)
        label = f'{level:7.3f} '
        line = label + '┫'
        
        for v in display_values:
            vnorm = (v - vmin) / vrange
            bar_height = int(vnorm * height)
            if bar_height >= row:
                line += symbol
            elif bar_height + 1 >= row and vnorm * height - bar_height > 0.5:
                line += '▌'
            else:
                line += ' '
        
        buf.write(line + '\n')
    
    # X-axis
    x_axis = ' ' * 8 + '┗' + '━' * len(display_values)
    buf.write(x_axis + '\n')
    
    # Labels on x-axis (first, middle, last)
    if len(display_values) > 2:
        labels = [' ' * 8]
        for i, _ in enumerate(display_values):
            if i == 0:
                labels[0] += f'{display_values[0]:.2f}'
            elif i == len(display_values) - 1:
                labels[0] += ' ' * (len(display_values) - 1) + f'{display_values[-1]:.2f}'
        if len(display_values) > 3 and len(labels) > 0:
            mid = len(display_values) // 2
            # Place middle label roughly in the right position
            pass
        buf.write(labels[0] + '\n')
    
    return buf.getvalue()


def html_report(
    snap_results: Dict[str, Any],
    title: str = "SnapKit Analysis Report",
    inline_css: bool = True,
) -> str:
    """
    Generate a self-contained HTML report with inline CSS and SVG.
    
    Args:
        snap_results: Dictionary of snap statistics.
        title: Report title.
        inline_css: Whether to inline CSS (for self-contained reports).
    
    Returns:
        Complete HTML string.
    
    Examples:
        >>> results = snap_function.statistics
        >>> html = html_report(results, title="Poker Analysis")
        >>> with open("report.html", "w") as f:
        ...     f.write(html)
    """
    css = """
    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        max-width: 960px;
        margin: 0 auto;
        padding: 20px;
        background: #0f0f1a;
        color: #e0e0e0;
        line-height: 1.6;
    }
    h1, h2, h3 { color: #00d4aa; }
    h1 { border-bottom: 2px solid #00d4aa; padding-bottom: 10px; }
    .metric-card {
        background: #1a1a2e;
        border: 1px solid #2a2a4e;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
    .metric-card h3 { margin-top: 0; }
    .metric-value {
        font-size: 2em;
        font-weight: bold;
        color: #00d4aa;
    }
    .metric-label {
        font-size: 0.85em;
        color: #888;
    }
    .good { color: #00d4aa; }
    .warning { color: #f0a030; }
    .bad { color: #e04040; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 15px 0;
    }
    th, td {
        padding: 8px 12px;
        text-align: left;
        border-bottom: 1px solid #2a2a4e;
    }
    th { background: #1a1a2e; color: #00d4aa; }
    tr:hover { background: #1a1a2e; }
    .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin: 15px 0;
    }
    .status-snap { color: #00d4aa; }
    .status-delta { color: #f0a030; }
    .status-critical { color: #e04040; }
    """
    
    # Build report
    html_parts = [
        '<!DOCTYPE html>',
        f'<html lang="en"><head>',
        f'<meta charset="UTF-8">',
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<title>{html_mod.escape(title)}</title>',
    ]
    
    if inline_css:
        html_parts.append(f'<style>{css}</style>')
    
    html_parts.append('</head><body>')
    html_parts.append(f'<h1>{html_mod.escape(title)}</h1>')
    
    # Summary metrics
    html_parts.append('<div class="grid">')
    
    metric_defs = [
        ('Total Observations', snap_results.get('total_observations', 0), 'good'),
        ('Snap Rate', f"{snap_results.get('snap_rate', 0):.1%}", 
         'good' if snap_results.get('snap_rate', 0) > 0.8 else 'warning'),
        ('Delta Rate', f"{snap_results.get('delta_rate', 0):.1%}",
         'good' if snap_results.get('delta_rate', 0) < 0.2 else 'bad'),
        ('Tolerance', f"{snap_results.get('tolerance', 0):.4f}", 'good'),
    ]
    
    for label, value, css_class in metric_defs:
        html_parts.append(f'''
        <div class="metric-card">
            <div class="metric-label">{html_mod.escape(label)}</div>
            <div class="metric-value {css_class}">{html_mod.escape(str(value))}</div>
        </div>
        ''')
    
    html_parts.append('</div>')
    
    # Detail table
    html_parts.append('<h2>Detail Metrics</h2>')
    html_parts.append('<table><tr><th>Metric</th><th>Value</th></tr>')
    
    for key, value in snap_results.items():
        if key not in ('per_stream',):
            html_parts.append(
                f'<tr><td>{html_mod.escape(str(key))}</td>'
                f'<td>{html_mod.escape(str(value))}</td></tr>'
            )
    
    html_parts.append('</table>')
    
    # Per-stream metrics
    per_stream = snap_results.get('per_stream', {})
    if per_stream:
        html_parts.append('<h2>Per-Stream Analysis</h2>')
        html_parts.append('<div class="grid">')
        
        for stream_id, stream_data in per_stream.items():
            if isinstance(stream_data, dict):
                delta_rate = stream_data.get('delta_rate', 0)
                css_class = 'good' if delta_rate < 0.2 else ('warning' if delta_rate < 0.5 else 'bad')
                html_parts.append(f'''
                <div class="metric-card">
                    <h3>{html_mod.escape(str(stream_id))}</h3>
                    <div class="metric-label">Delta Rate</div>
                    <div class="metric-value {css_class}">{delta_rate:.1%}</div>
                    <div class="metric-label">Observations: {stream_data.get('total_observations', 0)}</div>
                    <div class="metric-label">Tolerance: {stream_data.get('tolerance', 0):.4f}</div>
                </div>
                ''')
        
        html_parts.append('</div>')
    
    html_parts.append('</body></html>')
    
    return '\n'.join(html_parts)


def format_results(
    snap_function: Any,
    verbose: bool = False,
) -> str:
    """
    Human-readable interpretation of snap results.
    
    Takes a SnapFunction and returns a formatted interpretation
    of its current state — calibration quality, delta patterns,
    and recommendations.
    
    Args:
        snap_function: A SnapFunction instance.
        verbose: If True, include all statistics.
    
    Returns:
        Formatted string with interpretation.
    
    Examples:
        >>> snap = SnapFunction(tolerance=0.1)
        >>> snap.observe(0.05)
        >>> snap.observe(0.3)
        >>> print(format_results(snap))
    """
    from snapkit.snap import SnapFunction
    
    if not isinstance(snap_function, SnapFunction):
        return "Error: Expected SnapFunction instance"
    
    stats = snap_function.statistics
    buf = io.StringIO()
    
    # Header
    buf.write(f"╔══{'═' * 50}╗\n")
    buf.write(f"║  SnapKit Analysis{' ' * 37}║\n")
    buf.write(f"╠══{'═' * 50}╣\n")
    buf.write(f"║  Calibration: {snap_function.calibration:.1%}\n")
    
    # Calibration assessment
    cal = snap_function.calibration
    if cal > 0.9:
        assessment = "✅ Excellent — well-calibrated snap function"
    elif cal > 0.7:
        assessment = "⚠️  Good — slight adjustment needed"
    elif cal > 0.4:
        assessment = "🔶 Moderate — recalibration recommended"
    else:
        assessment = "🔴 Poor — snap function needs recalibration"
    
    buf.write(f"║  Assessment:  {assessment}\n")
    
    # Stats
    buf.write(f"╠══{'═' * 50}╣\n")
    buf.write(f"║  Statistics:\n")
    buf.write(f"║    Total observations: {stats['total_observations']}\n")
    buf.write(f"║    Snap rate:          {stats['snap_rate']:.1%}\n")
    buf.write(f"║    Delta rate:         {stats['delta_rate']:.1%}\n")
    buf.write(f"║    Mean delta:         {stats['mean_delta']:.4f}\n")
    buf.write(f"║    Max delta:          {stats['max_delta']:.4f}\n")
    buf.write(f"║    Current baseline:   {stats['current_baseline']:.4f}\n")
    buf.write(f"║    Tolerance:          {stats['tolerance']:.4f}\n")
    
    if verbose:
        buf.write(f"╠══{'═' * 50}╣\n")
        buf.write(f"║  Topology: {snap_function.topology.value}\n")
        buf.write(f"║  Adaptation rate: {snap_function.adaptation_rate:.4f}\n")
        buf.write(f"║  Snap count: {snap_function._snap_count}\n")
        buf.write(f"║  Delta count: {snap_function._delta_count}\n")
    
    buf.write(f"╚══{'═' * 50}╝\n")
    
    return buf.getvalue()


def dashboard(
    title: str = "SnapKit Dashboard",
    **panels: Dict[str, Any],
) -> str:
    """
    Multi-panel terminal dashboard.
    
    Each panel is a keyword argument with a dict containing:
        - 'title': Panel title
        - 'content': Panel content (string)
        - 'width': Panel width (default: 40)
        - 'height': Panel height (default: 5)
    
    Args:
        title: Dashboard title.
        **panels: Named panels with content.
    
    Returns:
        String with multi-panel dashboard.
    
    Examples:
        >>> dash = dashboard(
        ...     snap_panel={'title': 'Snap Status', 'content': snap_summary, 'width': 40},
        ...     delta_panel={'title': 'Recent Deltas', 'content': delta_summary, 'width': 40},
        ... )
        >>> print(dash)
    """
    if not panels:
        return "<empty dashboard>"
    
    buf = io.StringIO()
    
    # Title
    buf.write(f"╔══{'═' * (len(title) + 4)}══╗\n")
    buf.write(f"║    {title}    ║\n")
    buf.write(f"╚══{'═' * (len(title) + 4)}══╝\n\n")
    
    # Layout: arrange panels in rows of up to 2
    panel_items = list(panels.items())
    max_width = max(p.get('width', 40) for _, p in panel_items)
    
    for i in range(0, len(panel_items), 2):
        row = panel_items[i:i + 2]
        
        if len(row) == 2:
            # Two columns
            name1, panel1 = row[0]
            name2, panel2 = row[1]
            width1 = panel1.get('width', 40)
            width2 = panel2.get('width', 40)
            
            content1 = panel1.get('content', '').split('\n')
            content2 = panel2.get('content', '').split('\n')
            
            max_lines = max(len(content1), len(content2))
            content1 += [''] * (max_lines - len(content1))
            content2 += [''] * (max_lines - len(content2))
            
            # Panel headers
            buf.write(f"┌{'─' * width1}┐ ┌{'─' * width2}┐\n")
            title1 = panel1.get('title', name1)[:width1 - 2]
            title2 = panel2.get('title', name2)[:width2 - 2]
            buf.write(f"│ {title1:<{width1 - 2}}│ │ {title2:<{width2 - 2}}│\n")
            buf.write(f"├{'─' * width1}┤ ├{'─' * width2}┤\n")
            
            for line1, line2 in zip(content1, content2):
                buf.write(f"│ {line1:<{width1 - 2}}│ │ {line2:<{width2 - 2}}│\n")
            
            buf.write(f"└{'─' * width1}┘ └{'─' * width2}┘\n\n")
        else:
            # Single column
            name, panel = row[0]
            width = panel.get('width', max_width)
            content = panel.get('content', '').split('\n')
            
            buf.write(f"┌{'─' * width}┐\n")
            buf.write(f"│ {panel.get('title', name):<{width - 2}}│\n")
            buf.write(f"├{'─' * width}┤\n")
            for line in content:
                buf.write(f"│ {line:<{width - 2}}│\n")
            buf.write(f"└{'─' * width}┘\n\n")
    
    return buf.getvalue()


class _StyleContext:
    """Internal helper for consistent terminal styling."""
    
    RESET = '\033[0m'
    BOLD = '\033[1m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    CYAN = '\033[36m'
    MAGENTA = '\033[35m'
    
    @staticmethod
    def status(value: float, threshold_good: float = 0.8, threshold_warn: float = 0.5) -> str:
        """Color a status value."""
        color = _StyleContext.GREEN if value >= threshold_good else (
            _StyleContext.YELLOW if value >= threshold_warn else _StyleContext.RED
        )
        return f"{color}{value}{_StyleContext.RESET}"
    
    @staticmethod
    def label(text: str) -> str:
        return f"{_StyleContext.CYAN}{text}{_StyleContext.RESET}"
    
    @staticmethod
    def header(text: str) -> str:
        return f"{_StyleContext.BOLD}{_StyleContext.MAGENTA}{text}{_StyleContext.RESET}"


def format_attention_insight(
    total_budget: float,
    allocated: float,
    num_deltas: int,
    top_stream: str = "",
) -> str:
    """
    Generate an attention insight string: "you're spending X% of attention on..."
    
    Args:
        total_budget: Total attention budget.
        allocated: Amount of budget allocated.
        num_deltas: Number of deltas consuming attention.
        top_stream: Stream consuming the most attention.
    
    Returns:
        Human-readable insight string.
    """
    utilization = allocated / max(total_budget, 0.01) if total_budget > 0 else 0
    
    if utilization < 0.1:
        return f"Low attention utilization ({utilization:.0%}). Your snap function may be too loose."
    elif utilization < 0.4:
        return f"Comfortable attention allocation ({utilization:.0%}). {num_deltas} deltas being processed."
    elif utilization < 0.7:
        suffix = f"Top consumer: {top_stream}." if top_stream else ""
        return f"Moderate pressure ({utilization:.0%}). {num_deltas} active deltas. {suffix}"
    else:
        return (f"HIGH ATTENTION PRESSURE ({utilization:.0%}). "
                f"{num_deltas} deltas competing for {total_budget:.0f} budget units. "
                f"Consider tightening tolerance on {top_stream or 'heaviest stream'}.")
