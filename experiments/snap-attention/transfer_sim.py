#!/usr/bin/env python3
"""
Simulator 2: Cross-Domain Transfer

Test whether snap topologies transfer across domains.
A well-calibrated snap from domain A should work in domain B when the randomness shape matches.

Usage:
    python transfer_sim.py                        # default: 50,000 trials
    python transfer_sim.py --trials 100000 --verbose
    python transfer_sim.py --quick                # fast test: 500 trials
    python transfer_sim.py --csv transfer.csv --html transfer.html
"""

import json
import random
import argparse
import sys
import csv
from collections import defaultdict
from typing import List, Tuple, Dict

# ─── Randomness Flavors ─────────────────────────────────────────────

def generate_coin(n): return [random.choice([0.0, 1.0]) for _ in range(n)]
def generate_d6(n): return [random.randint(1, 6) / 6.0 for _ in range(n)]
def generate_d20(n): return [random.randint(1, 20) / 20.0 for _ in range(n)]
def generate_2d6(n): return [(random.randint(1,6)+random.randint(1,6))/12.0 for _ in range(n)]
def generate_categorical(n, categories=4): return [random.randint(1,categories)/categories for _ in range(n)]
def generate_directional(n): return [random.randint(1, 8) / 8.0 for _ in range(n)]
def generate_gaussian(n): return [max(0,min(1,random.gauss(0.5,0.15))) for _ in range(n)]

FLAVORS = {'coin':generate_coin,'d6':generate_d6,'d20':generate_d20,'2d6':generate_2d6,
           'categorical':generate_categorical,'directional':generate_directional,'gaussian':generate_gaussian}

SHAPE_GROUPS = {'binary': ['coin'], 'uniform': ['d6', 'd20'], 'bell': ['2d6', 'gaussian'],
                'categorical': ['categorical', 'directional']}

# ─── Snap Function ───────────────────────────────────────────────────

class SnapFunction:
    def __init__(self, tolerance=0.2):
        self.tolerance = tolerance; self.baseline = 0.5
        self.calibration_samples = 0; self.calibration_sum = 0.0; self.calibration_var = 0.0
    
    def snap(self, value):
        delta = abs(value - self.baseline); return (delta <= self.tolerance, delta)
    
    def calibrate(self, values, rate=0.1):
        for v in values:
            self.calibration_samples += 1; self.calibration_sum += v
            old = self.baseline; self.baseline = self.baseline * (1-rate) + v * rate
            self.tolerance = self.tolerance * 0.95 + abs(v - old) * 0.05
    
    def copy_tolerance(self):
        new = SnapFunction(self.tolerance); new.calibration_samples = self.calibration_samples; return new

def transfer_efficiency(source, target, cal_size=500, test_size=500):
    source_data = FLAVORS[source](cal_size + test_size)
    snap = SnapFunction(); snap.calibrate(source_data[:cal_size])
    trained_tol = snap.tolerance
    
    transferred = snap.copy_tolerance()
    target_data = FLAVORS[target](test_size)
    fresh = SnapFunction(); fresh.calibrate(FLAVORS[target](cal_size))
    
    target_mean = sum(target_data) / len(target_data)
    trans_baseline, fresh_baseline = 0.5, 0.5
    trans_errors, fresh_errors = [], []
    trans_deltas, fresh_deltas = 0, 0
    
    for v in target_data:
        ts, _ = transferred.snap(v)
        if not ts: trans_deltas += 1
        trans_baseline = trans_baseline * 0.9 + v * 0.1
        trans_errors.append(abs(trans_baseline - target_mean))
        transferred.baseline = trans_baseline
        
        fs, _ = fresh.snap(v)
        if not fs: fresh_deltas += 1
        fresh_baseline = fresh_baseline * 0.9 + v * 0.1
        fresh_errors.append(abs(fresh_baseline - target_mean))
        fresh.baseline = fresh_baseline
    
    avg_te = sum(trans_errors[-100:])/100
    avg_fe = sum(fresh_errors[-100:])/100
    matching = any(source in g and target in g for g in SHAPE_GROUPS.values())
    
    return {'source':source,'target':target,'shapes_match':matching,
            'trained_tolerance':round(trained_tol,4),
            'transferred_final_error':round(avg_te,4),'fresh_final_error':round(avg_fe,4),
            'transfer_efficiency':round(avg_fe/max(avg_te,0.0001),4),
            'transferred_deltas_detected':trans_deltas,'fresh_deltas_detected':fresh_deltas,
            'convergence_ratio':round(sum(trans_errors)/max(sum(fresh_errors),1),4)}

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
        w.writerow(['Source','Target','Shapes Match','Transfer Efficiency','Convergence Ratio','Trans Deltas','Fresh Deltas'])
        for r in results['sample_transfers']:
            w.writerow([r['source'], r['target'], r['shapes_match'], r['transfer_efficiency'],
                        r['convergence_ratio'], r['transferred_deltas_detected'], r['fresh_deltas_detected']])
        # Summary rows
        w.writerow([]); w.writerow(['--- SUMMARY ---'])
        s = results['summary']
        w.writerow(['Matching','efficiency','',s['avg_transfer_efficiency_matching']])
        w.writerow(['Mismatching','efficiency','',s['avg_transfer_efficiency_mismatching']])

def generate_html(results, filename):
    s = results['summary']
    matching_better = s['avg_transfer_efficiency_matching'] > s['avg_transfer_efficiency_mismatching']
    cls = 'good' if matching_better else 'bad'
    comp = f"{s['avg_transfer_efficiency_matching']:.4f}" if matching_better else f"{s['avg_transfer_efficiency_mismatching']:.4f}"
    
    # Per-flavor table
    flavor_rows = ""
    for name, d in results['per_flavor'].items():
        flavor_rows += f'<tr><td>{name}</td><td>{d["avg_transfer_efficiency"]:.4f}</td><td>{d["avg_convergence"]:.4f}</td></tr>\n'
    
    # Shape groups
    sg_html = ""
    for group, flavors in SHAPE_GROUPS.items():
        sg_html += f"<li><strong>{group}</strong>: {', '.join(flavors)}</li>"
    
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Cross-Domain Transfer Results</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#ab47bc;border-bottom:2px solid #ab47bc}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th{{background:#0f3460;color:#fff;padding:.6rem;text-align:left}}td{{padding:.6rem;border-bottom:1px solid #333}}
.good{{color:#4ecca3;font-weight:bold}}.bad{{color:#e94560;font-weight:bold}}
.insight{{background:#16213e;border-left:4px solid #ab47bc;padding:1rem;margin:1rem 0;border-radius:0 4px 4px 0}}</style></head>
<body><h1>🔄 Cross-Domain Transfer</h1><p>{results['num_trials']:,} transfer trials</p>
<h2>Summary</h2>
<table><tr><th>Condition</th><th>Avg Transfer Efficiency</th><th>Avg Convergence</th><th>Trials</th></tr>
<tr><td>Matching shapes</td><td class="{'good' if matching_better else 'bad'}">{s['avg_transfer_efficiency_matching']:.4f}</td>
    <td>{s['avg_convergence_matching']:.4f}</td><td>{s['matching_count']:,}</td></tr>
<tr><td>Mismatching shapes</td><td class="{'bad' if matching_better else 'good'}">{s['avg_transfer_efficiency_mismatching']:.4f}</td>
    <td>{s['avg_convergence_mismatching']:.4f}</td><td>{s['mismatching_count']:,}</td></tr></table>
<h2>Shape Groups</h2><ul>{sg_html}</ul>
<h2>Per-Flavor Transfer Efficiency</h2>
<table><tr><th>Flavor</th><th>Avg Transfer Efficiency</th><th>Avg Convergence</th></tr>
{flavor_rows}</table>
<div class="insight"><strong>💡 Insight</strong><br>{results['insight']}</div>
<p style="color:#666;font-size:.85em">Generated by transfer_sim.py</p></body></html>"""
    with open(filename, 'w') as f: f.write(html)

# ─── Main Simulation ────────────────────────────────────────────────

def run_simulation(num_trials=50000, verbose=False):
    flavor_names = list(FLAVORS.keys())
    all_results, matching, mismatching = [], [], []
    total_runs = (num_trials // (len(flavor_names)**2)) * len(flavor_names)**2
    
    count = 0
    for _ in range(num_trials // (len(flavor_names)**2)):
        for source in flavor_names:
            for target in flavor_names:
                if verbose and count % 100 == 0: progress_bar(count+1, total_runs, prefix="Transfer sim: ")
                r = transfer_efficiency(source, target)
                all_results.append(r)
                (matching if r['shapes_match'] else mismatching).append(r)
                count += 1
    
    def agg(results, key):
        return sum(r[key] for r in results)/len(results) if results else 0
    
    per_flavor = defaultdict(lambda: {'efficiency':[], 'convergence':[]})
    for r in all_results:
        if r['source'] != r['target']:
            per_flavor[r['source']]['efficiency'].append(r['transfer_efficiency'])
            per_flavor[r['source']]['convergence'].append(r['convergence_ratio'])
    
    flavor_summary = {f: {'avg_transfer_efficiency': round(sum(v['efficiency'])/len(v['efficiency']),4),
                           'avg_convergence': round(sum(v['convergence'])/len(v['convergence']),4)}
                      for f, v in per_flavor.items() if v['efficiency']}
    
    return {'num_trials': len(all_results),
        'summary': {'total_transfers': len(all_results),
            'avg_transfer_efficiency_matching': round(agg(matching,'transfer_efficiency'),4),
            'avg_transfer_efficiency_mismatching': round(agg(mismatching,'transfer_efficiency'),4),
            'avg_convergence_matching': round(agg(matching,'convergence_ratio'),4),
            'avg_convergence_mismatching': round(agg(mismatching,'convergence_ratio'),4),
            'avg_deltas_matching': round(agg(matching,'transferred_deltas_detected'),2),
            'avg_deltas_mismatching': round(agg(mismatching,'transferred_deltas_detected'),2),
            'matching_count': len(matching), 'mismatching_count': len(mismatching)},
        'per_flavor': flavor_summary,
        'sample_transfers': all_results[:20],
        'insight': "Matching shapes (e.g., coin→coin, d6→d20) should transfer better than mismatching shapes (e.g., coin→gaussian, 2d6→directional). Transfer efficiency > 1.0 means the transferred snap calibrates FASTER than a fresh snap — supporting the theory that snap topologies are domain-invariant."}

def display_results(results):
    s = results['summary']
    m_eff = s['avg_transfer_efficiency_matching']
    mm_eff = s['avg_transfer_efficiency_mismatching']
    m_con = s['avg_convergence_matching']
    mm_con = s['avg_convergence_mismatching']
    
    lines = [None,
        f"  {results['num_trials']:,} transfer trials",
        None,
        f"  {'Condition':<20} {'Efficiency':>12}  {'Convergence':>12}  {'Trials':>8}",
        "  " + "─" * 58,
        f"  {'Matching shapes':<20} {m_eff:>12.4f}  {m_con:>12.4f}  {s['matching_count']:>8,}",
        f"  {'Mismatching shapes':<20} {mm_eff:>12.4f}  {mm_con:>12.4f}  {s['mismatching_count']:>8,}",
        None,
        "  Shape groups:",
    ]
    for group, flavors in SHAPE_GROUPS.items():
        lines.append(f"    {group:<14}: {', '.join(flavors)}")
    
    lines += [None, "  Per-flavor transfer efficiency:"]
    max_eff = max((d['avg_transfer_efficiency'] for d in results['per_flavor'].values()), default=1)
    for name, d in results['per_flavor'].items():
        bar = ascii_bar(d['avg_transfer_efficiency'], max_eff, 20)
        lines.append(f"    {name:<14} │{bar} {d['avg_transfer_efficiency']:.4f}")
    lines += [None]
    
    print(box("🔄 CROSS-DOMAIN TRANSFER RESULTS", lines, width=62))
    
    # Interpretation
    better = m_eff > mm_eff
    print()
    interp = [None,
        "  WHAT THIS MEANS:",
        None,
        "  The snap-attention theory predicts that calibrating",
        "  a snap function on one domain should transfer to",
        "  another domain IF they share the same randomness",
        "  'shape' (topology).",
        None,
        "  Shape groups:",
        "    • Binary:     coin (2 outcomes)",
        "    • Uniform:    d6, d20 (flat distributions)",
        "    • Bell:       2d6, gaussian (central tendency)",
        "    • Categorical: categorical, directional (discrete)",
        None,
        f"  Result: Matching shapes transfer {'BETTER' if better else 'WORSE'}",
        f"  (efficiency {m_eff:.4f} vs {mm_eff:.4f})",
        None,
        f"  {'✅' if better else '❌'} This {'supports' if better else 'contradicts'} the hypothesis",
        f"  that snap topologies are domain-invariant.",
        None,
        "  Transfer efficiency > 1.0 means the pre-calibrated",
        "  snap converges FASTER than starting fresh —",
        "  'transfer learning' for attention functions.",
        None,
        "  ⚠️  CAVEAT: Efficiency depends heavily on the",
        "  calibration rate and tolerance adaptation. Different",
        "  parameters could change results significantly.",
        None]
    print(box("📋 INTERPRETATION", interp, width=55))

def parse_args():
    parser = argparse.ArgumentParser(description="Cross-Domain Transfer Simulator")
    parser.add_argument('--trials', type=int, default=50000, help='Number of trials (default: 50000)')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 500 trials')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress bar')
    parser.add_argument('--csv', type=str, default=None, help='Export CSV')
    parser.add_argument('--html', type=str, default=None, help='Generate HTML report')
    parser.add_argument('--json-out', type=str, default='results_transfer.json', help='JSON output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    nt = 500 if args.quick else args.trials
    print(f"🔄 Cross-Domain Transfer — Running {nt:,} trials...")
    results = run_simulation(nt, verbose=args.verbose)
    with open(args.json_out, 'w') as f: json.dump(results, f, indent=2)
    display_results(results)
    if args.csv: generate_csv(results, args.csv); print(f"\n📄 CSV → {args.csv}")
    if args.html: generate_html(results, args.html); print(f"🌐 HTML → {args.html}")
    print(f"\n✅ JSON → {args.json_out}")
