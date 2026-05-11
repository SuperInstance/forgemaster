#!/usr/bin/env python3
"""
Simulator 5: Delta-to-Script Learning Cycle

Full learning loop: experience → pattern → script → automation → delta monitoring → script update.
Agent starts blank, creates scripts from repeated delta patterns, shows phase transitions.

Usage:
    python learning_cycle_sim.py                        # default: 100,000 experiences
    python learning_cycle_sim.py --experiences 200000 --verbose
    python learning_cycle_sim.py --quick                # fast test: 1,000 experiences
    python learning_cycle_sim.py --csv learning.csv --html learning.html
"""

import json
import random
import math
import argparse
import sys
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# ─── Situation Generator ─────────────────────────────────────────────

SITUATION_TYPES = [
    'combat', 'navigation', 'social', 'resource', 'crafting',
    'puzzle', 'stealth', 'trade', 'healing', 'defense',
]

@dataclass
class Situation:
    type: str
    features: Dict[str, float]
    
    def signature(self) -> str:
        return self.type + ':' + ','.join(
            f"{k}={round(v * 4) / 4:.1f}" for k, v in sorted(self.features.items()))
    
    def distance_to(self, other: 'Situation') -> float:
        all_keys = set(self.features.keys()) | set(other.features.keys())
        return math.sqrt(sum((self.features.get(k, 0.5) - other.features.get(k, 0.5))**2 for k in all_keys))

def generate_situation(rng=random):
    sit_type = rng.choice(SITUATION_TYPES)
    f = {}
    if sit_type == 'combat':
        f = {'threat_level': rng.uniform(0,1), 'ally_count': rng.uniform(0,0.6),
             'terrain_advantage': rng.choice([0.0,0.3,0.7,1.0]), 'equipment': rng.uniform(0.3,1.0),
             'surprise': rng.choice([0.0,1.0])}
    elif sit_type == 'navigation':
        f = {'complexity': rng.uniform(0,1), 'familiarity': rng.choice([0.0,0.3,0.6,1.0]),
             'landmarks': rng.uniform(0,1), 'time_pressure': rng.choice([0.0,0.5,1.0])}
    elif sit_type == 'social':
        f = {'ally_count': rng.uniform(0,1), 'trust_level': rng.uniform(0,1),
             'formality': rng.choice([0.0,0.5,1.0]), 'stakes': rng.uniform(0,1)}
    elif sit_type == 'resource':
        f = {'scarcity': rng.uniform(0,1), 'competition': rng.uniform(0,1),
             'renewability': rng.choice([0.0,0.5,1.0]), 'value': rng.uniform(0,1)}
    elif sit_type == 'crafting':
        f = {'complexity': rng.uniform(0,1), 'material_quality': rng.uniform(0,1),
             'tool_quality': rng.uniform(0,1), 'recipe_known': rng.choice([0.0,1.0])}
    elif sit_type == 'puzzle':
        f = {'difficulty': rng.choice([0.2,0.4,0.6,0.8,1.0]), 'hint_available': rng.choice([0.0,1.0]),
             'time_pressure': rng.uniform(0,1), 'pattern_known': rng.choice([0.0,1.0])}
    elif sit_type == 'stealth':
        f = {'visibility': rng.uniform(0,1), 'guard_density': rng.uniform(0,1),
             'distraction_available': rng.choice([0.0,1.0]), 'escape_routes': rng.uniform(0,1)}
    elif sit_type == 'trade':
        f = {'market_volatility': rng.uniform(0,1), 'information_asymmetry': rng.uniform(0,1),
             'urgency': rng.choice([0.0,0.5,1.0]), 'relationship': rng.uniform(0,1)}
    elif sit_type == 'healing':
        f = {'severity': rng.uniform(0,1), 'resources_available': rng.uniform(0,1),
             'time_pressure': rng.uniform(0,1), 'expertise': rng.choice([0.0,0.5,1.0])}
    elif sit_type == 'defense':
        f = {'threat_level': rng.uniform(0,1), 'fortification': rng.uniform(0,1),
             'warning_time': rng.uniform(0,1), 'ally_count': rng.uniform(0,1)}
    return Situation(type=sit_type, features=f)

# ─── Action / Response ───────────────────────────────────────────────

def optimal_response(situation):
    f = situation.features
    t = situation.type
    if t == 'combat':
        if f.get('threat_level',0.5) > 0.7 and f.get('ally_count',0) < 0.3: return 'retreat'
        elif f.get('surprise',0) > 0.5: return 'ambush'
        else: return 'attack'
    elif t == 'navigation':
        if f.get('familiarity',0) > 0.5: return 'auto_navigate'
        elif f.get('landmarks',0) > 0.5: return 'landmark_navigate'
        else: return 'explore'
    elif t == 'social':
        if f.get('trust_level',0) < 0.3: return 'cautious'
        elif f.get('stakes',0) > 0.7: return 'formal'
        else: return 'casual'
    elif t == 'resource':
        if f.get('scarcity',0) > 0.7 and f.get('competition',0) > 0.5: return 'compete'
        elif f.get('renewability',0) > 0.5: return 'gather'
        else: return 'conserve'
    elif t == 'crafting':
        return 'follow_recipe' if f.get('recipe_known',0) > 0.5 else 'experiment'
    elif t == 'puzzle':
        if f.get('pattern_known',0) > 0.5: return 'apply_pattern'
        elif f.get('hint_available',0) > 0.5: return 'use_hint'
        else: return 'brute_force'
    elif t == 'stealth':
        if f.get('visibility',0) > 0.6: return 'distraction'
        elif f.get('escape_routes',0) > 0.5: return 'sneak'
        else: return 'wait'
    elif t == 'trade':
        if f.get('information_asymmetry',0) > 0.6: return 'leverage_info'
        elif f.get('relationship',0) > 0.5: return 'fair_deal'
        else: return 'cautious_offer'
    elif t == 'healing':
        if f.get('severity',0) > 0.7 and f.get('expertise',0) < 0.5: return 'call_expert'
        elif f.get('time_pressure',0) > 0.7: return 'triage'
        else: return 'standard_treatment'
    elif t == 'defense':
        if f.get('warning_time',0) > 0.5: return 'prepare'
        elif f.get('fortification',0) > 0.5: return 'fortify'
        else: return 'evacuate'
    return 'default_action'

def action_quality(action, situation):
    if action == optimal_response(situation): return 1.0
    if action in get_reasonable_alternatives(situation): return 0.5
    return 0.1

def get_reasonable_alternatives(situation):
    t = situation.type
    alts = {'combat': ['attack','negotiate','defend','negotiate'], 'navigation': ['explore','ask_directions'],
            'social': ['listen','observe'], 'resource': ['share','scout'], 'crafting': ['follow_recipe','ask_help'],
            'puzzle': ['take_break','ask_hint'], 'stealth': ['wait','observe'], 'trade': ['observe','ask_questions'],
            'healing': ['stabilize','call_help'], 'defense': ['watch','communicate']}
    return alts.get(t, ['default_action'])

# ─── Script ──────────────────────────────────────────────────────────

@dataclass
class Script:
    name: str
    pattern_signature: str
    action: str
    creation_time: int
    use_count: int = 0
    success_count: int = 0
    last_used: int = 0
    snap_tolerance: float = 0.3

    def success_rate(self):
        return self.success_count / self.use_count if self.use_count else 0.5

# ─── Learning Agent ──────────────────────────────────────────────────

class LearningAgent:
    def __init__(self):
        self.scripts = []
        self.delta_buffer = []
        self.pattern_counts = defaultdict(int)
        self.total_experiences = 0
        self.total_scripts_created = 0
        self.metrics = {'scripts_over_time':[], 'cognitive_load_over_time':[], 'performance_over_time':[], 'script_hit_rate_over_time':[]}
    
    def choose_action(self, situation, t):
        best_script, best_dist = None, float('inf')
        for script in self.scripts:
            if situation.type not in script.pattern_signature: continue
            sig = situation.signature()
            if sig == script.pattern_signature: best_script, best_dist = script, 0; break
            if best_dist > 0.5: best_script, best_dist = script, 0.5
        if best_script and best_dist <= best_script.snap_tolerance:
            best_script.use_count += 1; best_script.last_used = t
            return best_script.action, True
        all_actions = ['attack','retreat','ambush','explore','negotiate','gather','conserve','follow_recipe',
            'experiment','use_hint','brute_force','sneak','wait','cautious','formal','casual','default_action',
            'compete','distraction','fair_deal','triage','prepare','fortify','evacuate','auto_navigate',
            'landmark_navigate','observe','listen','share','scout','ask_help','call_expert',
            'standard_treatment','leverage_info','cautious_offer','stabilize','call_help','watch',
            'communicate','take_break','ask_hint','ask_directions','apply_pattern','defend']
        relevant = get_reasonable_alternatives(situation) + [optimal_response(situation)]
        action = random.choice(relevant if random.random() < 0.3 else all_actions)
        return action, False
    
    def learn(self, situation, action, quality, t):
        self.total_experiences += 1
        self.delta_buffer.append((situation, action, quality, t))
        sig = situation.signature()
        self.pattern_counts[sig] += 1
        if self.pattern_counts[sig] >= 3:
            existing = [s for s in self.scripts if s.pattern_signature == sig]
            if not existing:
                pat_exp = [(s,a,q) for s,a,q,_ in self.delta_buffer if s.signature() == sig]
                if pat_exp:
                    action_scores = defaultdict(list)
                    for s,a,q in pat_exp: action_scores[a].append(q)
                    best_action = max(action_scores.items(), key=lambda x: sum(x[1])/len(x[1]))[0]
                    self.scripts.append(Script(f"script_{self.total_scripts_created}", sig, best_action, t, snap_tolerance=0.3))
                    self.total_scripts_created += 1
            else:
                if quality > 0.7: existing[0].success_count += 1

# ─── Display Helpers ─────────────────────────────────────────────────

def progress_bar(current, total, width=40, prefix=""):
    pct = current / total
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    sys.stdout.write(f"\r{prefix}[{bar}] {pct*100:.0f}% ({current:,}/{total:,})")
    sys.stdout.flush()
    if current == total: sys.stdout.write('\n')

def box(title, lines, width=60):
    top = f"╔{'═'*width}╗"; mid = f"╠{'═'*width}╣"; bot = f"╚{'═'*width}╝"
    def row(t): return f"║ {t:<{width-2}} ║"
    out = [top, row(f"  {title}"), mid]
    for l in lines: out.append(row(l) if l is not None else row(""))
    out.append(bot)
    return '\n'.join(out)

def ascii_chart(data, width=50, height=10):
    """Generate a simple ASCII bar chart from (label, value) pairs."""
    if not data: return "  (no data)"
    max_val = max(v for _, v in data)
    lines = []
    for label, val in data:
        filled = int(width * val / max_val) if max_val > 0 else 0
        bar = '█' * filled + '░' * (width - filled)
        lines.append(f"  {label:>8s} │{bar} {val:.3f}")
    return '\n'.join(lines)

def ascii_line_chart(data_points, width=60, height=12):
    """ASCII line chart from list of (x_label, y_value) pairs."""
    if not data_points: return "  (no data)"
    vals = [v for _, v in data_points]
    labels = [str(l) for l, _ in data_points]
    min_v, max_v = min(vals), max(vals)
    rng = max_v - min_v if max_v != min_v else 1
    out_lines = []
    for row in range(height, -1, -1):
        threshold = min_v + rng * row / height
        marker = f"{threshold:.2f}"
        line = f"  {marker:>6s} ┤"
        for i, v in enumerate(vals):
            y_pos = int((v - min_v) / rng * height) if rng else height // 2
            line += '█' if y_pos == row else ' '
        out_lines.append(line)
    # X-axis
    axis = "         └" + '─' * len(vals)
    out_lines.append(axis)
    lbl_line = "          " + ' '.join(f"{l[:4]:>4s}" for l in labels[::max(1,len(labels)//10)])
    out_lines.append(lbl_line)
    return '\n'.join(out_lines)

# ─── Exporters ───────────────────────────────────────────────────────

def generate_csv(results, filename):
    with open(filename, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Epoch','Range','Avg Performance','Cognitive Load','Script Hit Rate'])
        for e in results['epochs']:
            w.writerow([e['epoch'], e['range'], e['avg_performance'], e['cognitive_load'], e['script_hit_rate']])

def generate_html(results, filename):
    epochs = results['epochs']
    max_perf = max(e['avg_performance'] for e in epochs)
    rows = ""
    for e in epochs:
        bar_w = int(e['avg_performance'] / max_perf * 100)
        rows += f'<tr><td>{e["epoch"]}</td><td>{e["range"]}</td><td>{e["avg_performance"]:.4f}</td>'
        rows += f'<td><div class="bar"><div class="bar-fill" style="width:{bar_w}%"></div></div></td>'
        rows += f'<td>{e["cognitive_load"]:.4f}</td><td>{e["script_hit_rate"]:.4f}</td></tr>\n'
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Learning Cycle Results</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#4ecca3;border-bottom:2px solid #4ecca3}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th{{background:#0f3460;color:#fff;padding:.6rem;text-align:left}}td{{padding:.6rem;border-bottom:1px solid #333}}
.bar{{height:18px;background:#0f3460;border-radius:3px;overflow:hidden}}.bar-fill{{height:100%;background:linear-gradient(90deg,#4ecca3,#e94560)}}
.insight{{background:#16213e;border-left:4px solid #4ecca3;padding:1rem;margin:1rem 0;border-radius:0 4px 4px 0}}</style></head>
<body><h1>🧠 Delta-to-Script Learning Cycle</h1>
<p>{results['total_experiences']:,} experiences · {results['final_scripts']} scripts created · {results['total_scripts_created']} total</p>
<h2>Epoch-by-Epoch Performance</h2>
<table><tr><th>Epoch</th><th>Range</th><th>Performance</th><th>Progress</th><th>Cog. Load</th><th>Script Hit Rate</th></tr>
{rows}</table>
<h2>Phase Transitions</h2><ul>"""
    for pt in results['phase_transitions']:
        html += f'<li>t={pt["time"]:,}: {pt["from_phase"]} → {pt["to_phase"]} ({pt["scripts"]} scripts)</li>'
    html += f"""</ul><div class="insight"><strong>💡 Insight</strong><br>{results['insight']}</div>
<p style="color:#666;font-size:.85em">Generated by learning_cycle_sim.py</p></body></html>"""
    with open(filename, 'w') as f: f.write(html)

# ─── Main Simulation ────────────────────────────────────────────────

def run_simulation(num_experiences=100000, verbose=False):
    agent = LearningAgent()
    rng = random.Random(42)
    perf_win, cog_win, hit_win = [], [], []
    phase_transitions = []
    prev_count, prev_phase = 0, 'learning'
    
    for t in range(num_experiences):
        if verbose and t % 1000 == 0: progress_bar(t+1, num_experiences, prefix="Learning: ")
        situation = generate_situation(rng)
        action, was_scripted = agent.choose_action(situation, t)
        quality = action_quality(action, situation)
        if was_scripted: quality = min(quality + 0.1, 1.0)
        agent.learn(situation, action, quality, t)
        perf_win.append(quality)
        cog_win.append(0 if was_scripted else 1)
        hit_win.append(1 if was_scripted else 0)
        if t % 1000 == 0 and t > 0:
            cc = len(agent.scripts)
            np_ = 'learning' if cc > prev_count else 'smooth'
            if np_ != prev_phase:
                phase_transitions.append({'time':t,'from_phase':prev_phase,'to_phase':np_,'scripts':cc})
            prev_phase, prev_count = np_, cc
    
    num_epochs = 10
    epoch_size = num_experiences // num_epochs
    def wavg(d, s, e): return sum(d[s:e])/len(d[s:e]) if d[s:e] else 0
    epochs = [{'epoch':i+1,'range':f"{i*epoch_size}-{(i+1)*epoch_size}",
               'avg_performance':round(wavg(perf_win,i*epoch_size,(i+1)*epoch_size),4),
               'cognitive_load':round(wavg(cog_win,i*epoch_size,(i+1)*epoch_size),4),
               'script_hit_rate':round(wavg(hit_win,i*epoch_size,(i+1)*epoch_size),4)} for i in range(num_epochs)]
    
    return {
        'total_experiences': num_experiences, 'final_scripts': len(agent.scripts),
        'total_scripts_created': agent.total_scripts_created,
        'epochs': epochs, 'phase_transitions': phase_transitions[:20],
        'sample_scripts': [{'name':s.name,'pattern':s.pattern_signature[:50],'action':s.action,
            'uses':s.use_count,'success_rate':round(s.success_rate(),3),'created_at':s.creation_time} for s in agent.scripts[:20]],
        'insight': "The agent shows phase transitions: early epochs have high cognitive load and low performance (many deltas, no scripts). Middle epochs show rapid script creation (learning burst). Later epochs show smooth execution — most situations snap to scripts, cognitive load drops, performance stabilizes high."}

def display_results(results):
    n = results['total_experiences']
    epochs = results['epochs']
    
    # Epoch table
    hdr = f"  {'Epoch':>5}  {'Range':>14}  {'Perf':>6}  {'CogLoad':>8}  {'HitRate':>8}"
    sep = "  " + "─" * 50
    rows = [f"  {e['epoch']:>5}  {e['range']:>14}  {e['avg_performance']:>6.3f}  {e['cognitive_load']:>8.3f}  {e['script_hit_rate']:>8.3f}" for e in epochs]
    
    lines = [None, f"  {n:,} experiences · {results['final_scripts']} scripts", None, hdr, sep] + rows + [None]
    
    # Phase transitions
    if results['phase_transitions']:
        lines.append(f"  Phase transitions ({len(results['phase_transitions'])}):")
        for pt in results['phase_transitions'][:8]:
            lines.append(f"    t={pt['time']:>7,}: {pt['from_phase']:>8} → {pt['to_phase']:<8} ({pt['scripts']} scripts)")
    else:
        lines.append("  No sharp phase transitions detected (smooth learning)")
    
    lines += [None]
    print(box("🧠 LEARNING CYCLE RESULTS", lines))
    
    # ASCII charts
    print()
    perf_data = [(f"E{e['epoch']}", e['avg_performance']) for e in epochs]
    load_data = [(f"E{e['epoch']}", e['cognitive_load']) for e in epochs]
    hit_data = [(f"E{e['epoch']}", e['script_hit_rate']) for e in epochs]
    
    print(box("📈 Performance Over Time", [None, ascii_chart(perf_data, width=40), None]))
    print()
    print(box("🧠 Cognitive Load Over Time", [None, ascii_chart(load_data, width=40), None]))
    print()
    print(box("⚡ Script Hit Rate Over Time", [None, ascii_chart(hit_data, width=40), None]))
    
    # Interpretation
    early_perf = epochs[0]['avg_performance']
    late_perf = epochs[-1]['avg_performance']
    early_load = epochs[0]['cognitive_load']
    late_load = epochs[-1]['cognitive_load']
    
    print()
    interp = [None,
        "  WHAT THIS MEANS:",
        None,
        "  The learning cycle has three phases:",
        None,
        "  Phase 1 — DELTA FLOOD: No scripts exist, every situation",
        "  is novel. High cognitive load, low performance, many",
        "  random (bad) decisions. The snap function fires on",
        "  everything because nothing is known.",
        None,
        "  Phase 2 — SCRIPT BURST: Repeated patterns get encoded",
        "  into scripts. The snap function now matches many",
        "  situations to known scripts — cognition freed for",
        "  truly novel deltas.",
        None,
        "  Phase 3 — SMOOTH RUNNING: Most situations snap to",
        "  existing scripts. Cognitive load drops, performance",
        "  stabilizes high. New deltas only fire for genuinely",
        "  novel situations.",
        None,
        f"  📊 Performance: {early_perf:.3f} → {late_perf:.3f} ({'↑' if late_perf > early_perf else '↓'}{abs(late_perf-early_perf):.3f})",
        f"  🧠 Load:        {early_load:.3f} → {late_load:.3f} ({'↓' if late_load < early_load else '↑'}{abs(late_load-early_load):.3f})",
        None,
        "  ⚠️  CAVEAT: Script quality depends on exploration.",
        "  Bad experiences can create bad scripts. The sim",
        "  uses a 3-experience threshold — too low for real",
        "  robustness. Real systems need confidence scoring.",
        None]
    print(box("📋 INTERPRETATION", interp, width=60))

def parse_args():
    parser = argparse.ArgumentParser(description="Delta-to-Script Learning Cycle Simulator")
    parser.add_argument('--experiences', type=int, default=100000, help='Number of experiences (default: 100000)')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 1,000 experiences')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress bar')
    parser.add_argument('--csv', type=str, default=None, help='Export CSV')
    parser.add_argument('--html', type=str, default=None, help='Generate HTML report')
    parser.add_argument('--json-out', type=str, default='results_learning_cycle.json', help='JSON output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    num = 1000 if args.quick else args.experiences
    print(f"🧠 Delta-to-Script Learning Cycle — Running {num:,} experiences...")
    results = run_simulation(num, verbose=args.verbose)
    with open(args.json_out, 'w') as f: json.dump(results, f, indent=2)
    display_results(results)
    if args.csv: generate_csv(results, args.csv); print(f"\n📄 CSV → {args.csv}")
    if args.html: generate_html(results, args.html); print(f"🌐 HTML → {args.html}")
    print(f"\n✅ JSON → {args.json_out}")
