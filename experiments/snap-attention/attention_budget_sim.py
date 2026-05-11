#!/usr/bin/env python3
"""
Simulator 4: Multi-Flavor Attention Budget

Agent with finite attention budget across multiple information streams.
Each stream has different randomness flavor. Snap compresses within-tolerance.
Three strategies: uniform, reactive, smart (actionability-weighted).

Usage:
    python attention_budget_sim.py                        # default: 100,000 timesteps
    python attention_budget_sim.py --timesteps 200000 --verbose
    python attention_budget_sim.py --quick                # fast test: 1,000 timesteps
    python attention_budget_sim.py --csv budget.csv --html budget.html
"""

import json
import random
import math
import argparse
import sys
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from collections import defaultdict

# ─── Randomness Flavors ─────────────────────────────────────────────

def coin_stream(n): return [random.choice([0.0, 1.0]) for _ in range(n)]
def d6_stream(n): return [random.randint(1, 6) / 6.0 for _ in range(n)]
def d20_stream(n): return [random.randint(1, 20) / 20.0 for _ in range(n)]
def bell_stream(n): return [(random.randint(1,6)+random.randint(1,6))/12.0 for _ in range(n)]
def gaussian_stream(n): return [max(0,min(1,random.gauss(0.5,0.15))) for _ in range(n)]
def spike_stream(n): return [1.0 if random.random()<0.05 else 0.0 for _ in range(n)]
def sine_stream(n): return [0.5+0.4*math.sin(2*math.pi*i/20) for i in range(n)]
def drift_stream(n):
    val, result = 0.5, []
    for _ in range(n): val += random.gauss(0,0.02); val = max(0,min(1,val)); result.append(val)
    return result
def categorical_stream(n): return [random.choice([0.0,0.25,0.5,0.75,1.0]) for _ in range(n)]
def burst_stream(n):
    result = []
    for _ in range(n):
        if random.random() < 0.1: result.extend([random.uniform(0.7,1.0)]*random.randint(1,3))
        else: result.append(random.uniform(0.0,0.3))
    return result[:n]

STREAM_GENERATORS = {'coin':coin_stream,'d6':d6_stream,'d20':d20_stream,'bell':bell_stream,
    'gaussian':gaussian_stream,'spike':spike_stream,'sine':sine_stream,'drift':drift_stream,
    'categorical':categorical_stream,'burst':burst_stream}

# ─── Information Stream ─────────────────────────────────────────────

@dataclass
class InfoStream:
    name: str; flavor: str; data: List[float]; actionability: float; true_anomaly_rate: float
    tolerance: float = 0.15; baseline: float = 0.5
    
    def __post_init__(self): self.baseline = self.data[0] if self.data else 0.5
    
    def snap(self, value):
        delta = abs(value - self.baseline)
        if delta <= self.tolerance:
            self.baseline = 0.9*self.baseline + 0.1*value; return True, delta
        return False, delta
    
    def is_true_anomaly(self, value, t):
        w = 20; s = max(0, t-w); wd = self.data[s:t]
        if not wd: return False
        m = sum(wd)/len(wd); std = (sum((x-m)**2 for x in wd)/len(wd))**0.5
        return abs(value - m) > max(std * 1.5, 0.1)

# ─── Attention Strategies ───────────────────────────────────────────

def allocate_uniform(streams, deltas, budget):
    if not deltas: return []
    random.shuffle(deltas); return [d[0] for d in deltas[:budget]]

def allocate_reactive(streams, deltas, budget):
    return [d[0] for d in sorted(deltas, key=lambda x: x[1], reverse=True)[:budget]]

def allocate_smart(streams, deltas, budget):
    scored = sorted([(idx, delta*streams[idx].actionability) for idx, delta in deltas],
                    key=lambda x: x[1], reverse=True)
    return [s[0] for s in scored[:budget]]

STRATEGIES = {'uniform': allocate_uniform, 'reactive': allocate_reactive, 'smart': allocate_smart}

# ─── Display Helpers ─────────────────────────────────────────────────

def progress_bar(current, total, width=40, prefix=""):
    pct = current / total; filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    sys.stdout.write(f"\r{prefix}[{bar}] {pct*100:.0f}% ({current:,}/{total:,})")
    sys.stdout.flush()
    if current == total: sys.stdout.write('\n')

def box(title, lines, width=55):
    top = f"╔{'═'*width}╗"; mid = f"╠{'═'*width}╣"; bot = f"╚{'═'*width}╝"
    def row(t): return f"║ {t:<{width-2}} ║"
    out = [top, row(f"  {title}"), mid]
    for l in lines: out.append(row(l) if l is not None else row(""))
    out.append(bot)
    return '\n'.join(out)

def ascii_bar(value, max_val, width=20):
    filled = int(width * value / max_val) if max_val > 0 else 0
    return '█' * filled + '░' * (width - filled)

# ─── Exporters ───────────────────────────────────────────────────────

def generate_csv(results, filename):
    with open(filename, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Strategy','Utility','Missed Opportunities','Attention Waste','Precision','Net Value','Deltas Detected'])
        for name, d in results['strategies'].items():
            w.writerow([name, d['total_utility'], d['missed_opportunities'], d['attention_waste'],
                        d['precision'], d['net_value'], d['total_deltas_detected']])

def generate_html(results, filename):
    s = results['strategies']
    max_net = max(d['net_value'] for d in s.values())
    rows = ""
    for n, d in s.items():
        cls = 'good' if d['net_value'] == max_net else 'neutral'
        bar_w = int(d['net_value'] / max_net * 100) if max_net > 0 else 0
        rows += f'<tr><td><strong>{n}</strong></td><td class="{cls}">{d["total_utility"]:.1f}</td>'
        rows += f'<td>{d["missed_opportunities"]}</td><td>{d["attention_waste"]:.1f}</td>'
        rows += f'<td>{d["precision"]:.4f}</td><td><div class="bar"><div class="bar-fill" style="width:{bar_w}%"></div></div></td>'
        rows += f'<td class="{cls}">{d["net_value"]:.1f}</td></tr>\n'
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Attention Budget Results</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#f9a825;border-bottom:2px solid #f9a825}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th{{background:#0f3460;color:#fff;padding:.6rem;text-align:left}}td{{padding:.6rem;border-bottom:1px solid #333}}
tr:hover{{background:#16213e}}.good{{color:#4ecca3;font-weight:bold}}.neutral{{color:#a0a0a0}}
.bar{{height:18px;background:#0f3460;border-radius:3px;overflow:hidden}}.bar-fill{{height:100%;background:linear-gradient(90deg,#4ecca3,#f9a825)}}
.insight{{background:#16213e;border-left:4px solid #f9a825;padding:1rem;margin:1rem 0;border-radius:0 4px 4px 0}}</style></head>
<body><h1>📡 Multi-Flavor Attention Budget</h1>
<p>{results['timesteps']:,} timesteps · {results['num_streams']} streams · budget={results['budget']}</p>
<h2>Strategy Comparison</h2>
<table><tr><th>Strategy</th><th>Utility</th><th>Missed</th><th>Waste</th><th>Precision</th><th>Net Value</th><th>Score</th></tr>
{rows}</table>
<div class="insight"><strong>💡 Insight</strong><br>{results['insight']}</div>
<p style="color:#666;font-size:.85em">Generated by attention_budget_sim.py</p></body></html>"""
    with open(filename, 'w') as f: f.write(html)

# ─── Main Simulation ────────────────────────────────────────────────

def run_simulation(num_timesteps=100000, budget=3, verbose=False):
    stream_configs = [
        ('coin', 0.3, 0.02), ('d6', 0.5, 0.05), ('d20', 0.6, 0.04),
        ('bell', 0.7, 0.03), ('gaussian', 0.8, 0.06), ('spike', 0.9, 0.05),
        ('sine', 0.2, 0.01), ('drift', 0.6, 0.04), ('categorical', 0.4, 0.05),
        ('burst', 0.85, 0.05),
    ]
    stream_data = {}
    for name, act, ar in stream_configs:
        data = STREAM_GENERATORS[name](num_timesteps)
        for i in range(num_timesteps):
            if random.random() < ar: data[i] = 1.0 - data[i]
        stream_data[name] = (data, act, ar)
    
    results = {}
    for strategy_name, strategy_fn in STRATEGIES.items():
        if verbose: print(f"  Running {strategy_name}...", flush=True)
        streams = [InfoStream(name=n, flavor=n, data=d[:], actionability=a, true_anomaly_rate=ar,
                   tolerance=0.15, baseline=d[0] if d else 0.5) for n,(d,a,ar) in stream_data.items()]
        total_utility = missed = waste = total_deltas = correct = false_ = missed_true = 0
        for t in range(num_timesteps):
            if verbose and t % max(1, num_timesteps//10) == 0:
                progress_bar(t+1, num_timesteps, prefix=f"  {strategy_name}: ")
            deltas = []
            for idx, stream in enumerate(streams):
                value = stream.data[t]
                snapped, delta = stream.snap(value)
                if not snapped: deltas.append((idx, delta)); total_deltas += 1
            attended = strategy_fn(streams, deltas, budget)
            for idx in attended:
                stream = streams[idx]; value = stream.data[t]
                if stream.is_true_anomaly(value, t): total_utility += stream.actionability; correct += 1
                else: waste += 0.1; false_ += 1
            for idx in range(len(streams)):
                if idx not in attended:
                    stream = streams[idx]; value = stream.data[t]
                    if stream.is_true_anomaly(value, t) and any(d[0]==idx for d in deltas):
                        missed += 1; missed_true += 1
        results[strategy_name] = {
            'total_utility': round(total_utility, 2), 'missed_opportunities': missed,
            'attention_waste': round(waste, 2), 'total_deltas_detected': total_deltas,
            'correct_attends': correct, 'false_attends': false_, 'true_anomalies_missed': missed_true,
            'precision': round(correct / max(correct + false_, 1), 4),
            'net_value': round(total_utility - waste, 2)}
    
    return {'timesteps': num_timesteps, 'budget': budget, 'num_streams': len(stream_configs),
            'strategies': results,
            'insight': "Smart strategy (actionability-weighted) should outperform because it directs attention to deltas where thinking can actually change outcomes. Reactive wastes attention on large deltas from low-actionability streams. Uniform wastes attention randomly."}

def display_results(results):
    s = results['strategies']
    max_net = max(d['net_value'] for d in s.values())
    max_prec = max(d['precision'] for d in s.values())
    
    hdr = f"  {'Strategy':<12} {'Utility':>8}  {'Missed':>7}  {'Waste':>7}  {'Precision':>10}  {'Net Value':>10}"
    sep = "  " + "─" * 60
    rows = []
    for name, d in s.items():
        star = " ⭐" if d['net_value'] == max_net else ""
        rows.append(f"  {name:<12} {d['total_utility']:>8.1f}  {d['missed_opportunities']:>7,}  {d['attention_waste']:>7.1f}  {d['precision']:>10.4f}  {d['net_value']:>10.1f}{star}")
    
    lines = [None, f"  {results['timesteps']:,} timesteps · {results['num_streams']} streams · budget={results['budget']}", None, hdr, sep] + rows + [None]
    
    # Bar comparison
    lines.append("  Net value comparison:")
    for name, d in s.items():
        bar = ascii_bar(d['net_value'], max_net, 25)
        lines.append(f"    {name:<12} │{bar} {d['net_value']:.1f}")
    lines += [None]
    
    print(box("📡 ATTENTION BUDGET RESULTS", lines, width=65))
    
    # Interpretation
    smart = s.get('smart', {})
    reactive = s.get('reactive', {})
    uniform = s.get('uniform', {})
    
    print()
    interp = [None,
        "  WHAT THIS MEANS:",
        None,
        "  Three strategies compete for limited attention (budget",
        f"  = {results['budget']} out of {results['num_streams']} streams per timestep):",
        None,
        "  • Uniform:  Spreads attention evenly. Fair but",
        "             wastes slots on uninformative streams.",
        None,
        "  • Reactive: Attends to biggest deltas. Sounds smart",
        "             but wastes attention on high-magnitude",
        "             noise from low-value streams (e.g., coin).",
        None,
        "  • Smart:    Weights deltas by actionability — how much",
        "             thinking can change the outcome. Prioritizes",
        "             spike/burst streams where attention matters.",
        None]
    if smart and reactive:
        diff = smart.get('net_value',0) - reactive.get('net_value',0)
        interp += [f"  📊 Smart vs Reactive: +{diff:.1f} net value ({'wins' if diff > 0 else 'loses'})"]
    if smart and uniform:
        diff = smart.get('net_value',0) - uniform.get('net_value',0)
        interp += [f"  📊 Smart vs Uniform:  +{diff:.1f} net value ({'wins' if diff > 0 else 'loses'})"]
    interp += [None,
        "  ⚠️  CAVEAT: Actionability weights are hand-assigned.",
        "  Real systems would need to learn them from experience.",
        None]
    print(box("📋 INTERPRETATION", interp, width=55))

def parse_args():
    parser = argparse.ArgumentParser(description="Multi-Flavor Attention Budget Simulator")
    parser.add_argument('--timesteps', type=int, default=100000, help='Timesteps (default: 100000)')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 1,000 timesteps')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress per strategy')
    parser.add_argument('--csv', type=str, default=None, help='Export CSV')
    parser.add_argument('--html', type=str, default=None, help='Generate HTML report')
    parser.add_argument('--json-out', type=str, default='results_attention_budget.json', help='JSON output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    ts = 1000 if args.quick else args.timesteps
    print(f"📡 Multi-Flavor Attention Budget — Running {ts:,} timesteps...")
    results = run_simulation(ts, verbose=args.verbose)
    with open(args.json_out, 'w') as f: json.dump(results, f, indent=2)
    display_results(results)
    if args.csv: generate_csv(results, args.csv); print(f"\n📄 CSV → {args.csv}")
    if args.html: generate_html(results, args.html); print(f"🌐 HTML → {args.html}")
    print(f"\n✅ JSON → {args.json_out}")
