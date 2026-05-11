#!/usr/bin/env python3
"""
Simulator 3: Rubik's Cube Script Engine

Simulate the script-building + mind-freeing cycle.
Three solver types: brute force, script executor, planning solver.

Usage:
    python rubik_sim.py                        # default: 500 solves per type
    python rubik_sim.py --solves 1000 --verbose
    python rubik_sim.py --quick                # fast test: 10 solves
    python rubik_sim.py --csv rubik.csv --html rubik.html
"""

import json
import random
import argparse
import sys
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# ─── Cube Representation ─────────────────────────────────────────────

class Cube:
    def __init__(self):
        self.state = [[f]*9 for f in range(6)]
    
    def copy(self):
        c = Cube(); c.state = [face[:] for face in self.state]; return c
    
    def is_solved(self): return all(len(set(face)) == 1 for face in self.state)
    
    MOVES = ['U',"U'",'D',"D'",'F',"F'",'B',"B'",'L',"L'",'R',"R'",'U2','D2','F2','B2','L2','R2']
    
    def rotate_face_cw(self, face):
        f = self.state[face]
        self.state[face] = [f[6],f[3],f[0],f[7],f[4],f[1],f[8],f[5],f[2]]
    
    def rotate_face_ccw(self, face):
        f = self.state[face]
        self.state[face] = [f[2],f[5],f[8],f[1],f[4],f[7],f[0],f[3],f[6]]
    
    def apply_move(self, move):
        s = self.state
        if move == 'U':
            self.rotate_face_cw(0); temp=s[2][0:3]; s[2][0:3]=s[4][0:3]; s[4][0:3]=s[3][0:3]; s[3][0:3]=s[5][0:3]; s[5][0:3]=temp
        elif move == "U'":
            self.rotate_face_ccw(0); temp=s[2][0:3]; s[2][0:3]=s[5][0:3]; s[5][0:3]=s[3][0:3]; s[3][0:3]=s[4][0:3]; s[4][0:3]=temp
        elif move == 'D':
            self.rotate_face_cw(1); temp=s[2][6:9]; s[2][6:9]=s[5][6:9]; s[5][6:9]=s[3][6:9]; s[3][6:9]=s[4][6:9]; s[4][6:9]=temp
        elif move == "D'":
            self.rotate_face_ccw(1); temp=s[2][6:9]; s[2][6:9]=s[4][6:9]; s[4][6:9]=s[3][6:9]; s[3][6:9]=s[5][6:9]; s[5][6:9]=temp
        elif move == 'F':
            self.rotate_face_cw(2); temp=[s[0][6],s[0][7],s[0][8]]
            s[0][6],s[0][7],s[0][8]=s[4][8],s[4][5],s[4][2]; s[4][8],s[4][5],s[4][2]=s[1][2],s[1][1],s[1][0]
            s[1][2],s[1][1],s[1][0]=s[5][0],s[5][3],s[5][6]; s[5][0],s[5][3],s[5][6]=temp[0],temp[1],temp[2]
        elif move == "F'":
            self.rotate_face_ccw(2); temp=[s[0][6],s[0][7],s[0][8]]
            s[0][6],s[0][7],s[0][8]=s[5][0],s[5][3],s[5][6]; s[5][0],s[5][3],s[5][6]=s[1][2],s[1][1],s[1][0]
            s[1][2],s[1][1],s[1][0]=s[4][8],s[4][5],s[4][2]; s[4][8],s[4][5],s[4][2]=temp[0],temp[1],temp[2]
        elif move == 'B':
            self.rotate_face_cw(3); temp=[s[0][0],s[0][1],s[0][2]]
            s[0][0],s[0][1],s[0][2]=s[5][2],s[5][5],s[5][8]; s[5][2],s[5][5],s[5][8]=s[1][8],s[1][7],s[1][6]
            s[1][8],s[1][7],s[1][6]=s[4][6],s[4][3],s[4][0]; s[4][6],s[4][3],s[4][0]=temp[0],temp[1],temp[2]
        elif move == "B'":
            self.rotate_face_ccw(3); temp=[s[0][0],s[0][1],s[0][2]]
            s[0][0],s[0][1],s[0][2]=s[4][6],s[4][3],s[4][0]; s[4][6],s[4][3],s[4][0]=s[1][8],s[1][7],s[1][6]
            s[1][8],s[1][7],s[1][6]=s[5][2],s[5][5],s[5][8]; s[5][2],s[5][5],s[5][8]=temp[0],temp[1],temp[2]
        elif move == 'L':
            self.rotate_face_cw(4); temp=[s[0][0],s[0][3],s[0][6]]
            s[0][0],s[0][3],s[0][6]=s[3][8],s[3][5],s[3][2]; s[3][8],s[3][5],s[3][2]=s[1][0],s[1][3],s[1][6]
            s[1][0],s[1][3],s[1][6]=s[2][0],s[2][3],s[2][6]; s[2][0],s[2][3],s[2][6]=temp[0],temp[1],temp[2]
        elif move == "L'":
            self.rotate_face_ccw(4); temp=[s[0][0],s[0][3],s[0][6]]
            s[0][0],s[0][3],s[0][6]=s[2][0],s[2][3],s[2][6]; s[2][0],s[2][3],s[2][6]=s[1][0],s[1][3],s[1][6]
            s[1][0],s[1][3],s[1][6]=s[3][8],s[3][5],s[3][2]; s[3][8],s[3][5],s[3][2]=temp[0],temp[1],temp[2]
        elif move == 'R':
            self.rotate_face_cw(5); temp=[s[0][2],s[0][5],s[0][8]]
            s[0][2],s[0][5],s[0][8]=s[2][2],s[2][5],s[2][8]; s[2][2],s[2][5],s[2][8]=s[1][2],s[1][5],s[1][8]
            s[1][2],s[1][5],s[1][8]=s[3][6],s[3][3],s[3][0]; s[3][6],s[3][3],s[3][0]=temp[0],temp[1],temp[2]
        elif move == "R'":
            self.rotate_face_ccw(5); temp=[s[0][2],s[0][5],s[0][8]]
            s[0][2],s[0][5],s[0][8]=s[3][6],s[3][3],s[3][0]; s[3][6],s[3][3],s[3][0]=s[1][2],s[1][5],s[1][8]
            s[1][2],s[1][5],s[1][8]=s[2][2],s[2][5],s[2][8]; s[2][2],s[2][5],s[2][8]=temp[0],temp[1],temp[2]
        elif move in ('U2','D2','F2','B2','L2','R2'):
            base = move[0]; self.apply_move(base); self.apply_move(base)
    
    def apply_sequence(self, moves):
        for m in moves: self.apply_move(m)
    
    def scramble(self, num_moves=20):
        moves = random.choices(Cube.MOVES, k=num_moves)
        for m in moves: self.apply_move(m)
        return moves
    
    def count_solved_stickers(self):
        return sum(1 for f in range(6) for s in self.state[f] if s == f)
    
    def heuristic(self): return 54 - self.count_solved_stickers()

# ─── Scripts ─────────────────────────────────────────────────────────

SCRIPTS = {
    'sexy_move': ['R','U',"R'","U'"], 'sledgehammer': ["R'",'F','R',"F'"],
    'h_perm': ['R2','U2','R','U2','R2','U2','R2','U2','R','U2','R2'],
    't_perm': ['R','U',"R'","U'","R'",'F','R2',"U'","R'","U'",'R','U',"R'","F'"],
    'y_perm': ['F','R',"U'","R'","U'",'R','U',"R'","F'",'R','U',"R'","U'","R'",'F','R',"F'"],
    'sune': ['R','U','R','U','R','U2',"R'"], 'anti_sune': ["R'",'U2','R','U',"R'",'U','R'],
    'corner_insert': ["R'","D'",'R','D'], 'edge_insert': ['U','R',"U'","R'","U'","F'",'U','F'],
    'cross_solve_d': ['F','R','D'],
}

class SnapDetector:
    def __init__(self, scripts):
        self.scripts = scripts
    
    def snap(self, cube):
        best_script, best_imp = None, 0
        for name, moves in self.scripts.items():
            test = cube.copy(); test.apply_sequence(moves)
            imp = cube.heuristic() - test.heuristic()
            if imp > best_imp: best_imp = imp; best_script = (name, moves)
        return best_script if best_imp > 0 else None

# ─── Solvers ─────────────────────────────────────────────────────────

def brute_force_solve(cube, max_moves=500):
    c = cube.copy(); moves_used = []
    for _ in range(max_moves):
        if c.is_solved(): return {'moves':len(moves_used),'solved':True,'cognitive_load':len(moves_used),'script_moves':0,'novel_decisions':len(moves_used)}
        move = random.choice(Cube.MOVES); c.apply_move(move); moves_used.append(move)
    return {'moves':max_moves,'solved':False,'cognitive_load':max_moves,'script_moves':0,'novel_decisions':max_moves}

def script_executor_solve(cube, snap, max_moves=300):
    c = cube.copy(); moves_used = []; script_moves = 0; novel = 0
    for _ in range(max_moves):
        if c.is_solved(): return {'moves':len(moves_used),'solved':True,'cognitive_load':novel,'script_moves':script_moves,'novel_decisions':novel}
        result = snap.snap(c)
        if result:
            _, sm = result; c.apply_sequence(sm); moves_used.extend(sm); script_moves += len(sm); novel += 1
        else:
            move = random.choice(Cube.MOVES); c.apply_move(move); moves_used.append(move); novel += 1
    return {'moves':max_moves,'solved':c.is_solved(),'cognitive_load':novel,'script_moves':script_moves,'novel_decisions':novel}

def planning_solver_solve(cube, snap, max_moves=300):
    c = cube.copy(); moves_used = []; script_moves = 0; novel = 0; plans = 0
    for _ in range(max_moves):
        if c.is_solved(): return {'moves':len(moves_used),'solved':True,'cognitive_load':novel,'script_moves':script_moves,'novel_decisions':novel,'plans_executed':plans}
        script_scores = []
        for name, moves in snap.scripts.items():
            test = c.copy(); test.apply_sequence(moves)
            if test.is_solved():
                c.apply_sequence(moves); moves_used.extend(moves); script_moves += len(moves); novel += 1; plans += 1; break
            script_scores.append((c.heuristic()-test.heuristic(), name, moves))
        else:
            script_scores.sort(reverse=True)
            if script_scores and script_scores[0][0] > 0:
                _, name, moves = script_scores[0]; c.apply_sequence(moves); moves_used.extend(moves)
                script_moves += len(moves); novel += 1; plans += 1
            else:
                best_move = random.choice(Cube.MOVES); best_h = c.heuristic()
                for m in random.sample(Cube.MOVES, min(5, len(Cube.MOVES))):
                    test = c.copy(); test.apply_move(m)
                    if test.heuristic() < best_h: best_h = test.heuristic(); best_move = m
                c.apply_move(best_move); moves_used.append(best_move); novel += 1
            continue
        continue
    return {'moves':len(moves_used),'solved':c.is_solved(),'cognitive_load':novel,'script_moves':script_moves,'novel_decisions':novel,'plans_executed':plans}

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
        w.writerow(['Solver','Avg Moves','Solve Rate (%)','Avg Cognitive Load','Script Ratio (%)','Avg Plans'])
        for name, d in results['solvers'].items():
            sr = d.get('avg_script_ratio',0)
            ap = d.get('avg_plans','')
            w.writerow([name, d['avg_moves'], f"{d['solve_rate']*100:.1f}", d['avg_cognitive_load'],
                        f"{sr*100:.1f}" if sr else '', ap])

def generate_html(results, filename):
    s = results['solvers']
    max_sr = max(d['solve_rate'] for d in s.values())
    rows = ""
    for n, d in s.items():
        cls = 'good' if d['solve_rate'] == max_sr else 'neutral'
        bar_w = int(d['solve_rate'] / max_sr * 100)
        sr = f"{d['avg_script_ratio']*100:.1f}%" if 'avg_script_ratio' in d else 'N/A'
        ap = f"{d['avg_plans']:.1f}" if 'avg_plans' in d else 'N/A'
        rows += f'<tr><td><strong>{n}</strong></td><td>{d["avg_moves"]:.1f}</td>'
        rows += f'<td class="{cls}">{d["solve_rate"]*100:.1f}%</td>'
        rows += f'<td><div class="bar"><div class="bar-fill" style="width:{bar_w}%"></div></div></td>'
        rows += f'<td>{d["avg_cognitive_load"]:.1f}</td><td>{sr}</td><td>{ap}</td></tr>\n'
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Rubik's Cube Results</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#42a5f5;border-bottom:2px solid #42a5f5}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th{{background:#0f3460;color:#fff;padding:.6rem;text-align:left}}td{{padding:.6rem;border-bottom:1px solid #333}}
.good{{color:#4ecca3;font-weight:bold}}.bar{{height:18px;background:#0f3460;border-radius:3px;overflow:hidden}}
.bar-fill{{height:100%;background:linear-gradient(90deg,#4ecca3,#42a5f5)}}
.insight{{background:#16213e;border-left:4px solid #42a5f5;padding:1rem;margin:1rem 0;border-radius:0 4px 4px 0}}</style></head>
<body><h1>🧊 Rubik's Cube Script Engine</h1><p>{results['num_solves']} solves per type</p>
<h2>Solver Comparison</h2>
<table><tr><th>Solver</th><th>Avg Moves</th><th>Solve Rate</th><th>Progress</th><th>Cog. Load</th><th>Script %</th><th>Plans</th></tr>
{rows}</table><div class="insight"><strong>💡 Insight</strong><br>{results['insight']}</div>
<p style="color:#666;font-size:.85em">Generated by rubik_sim.py</p></body></html>"""
    with open(filename, 'w') as f: f.write(html)

# ─── Main Simulation ────────────────────────────────────────────────

def run_simulation(num_solves=500, verbose=False):
    snap = SnapDetector(SCRIPTS)
    data = {'brute_force':{'moves':[],'solved':0,'cog':[]},
            'script_executor':{'moves':[],'solved':0,'cog':[],'script_ratio':[]},
            'planning':{'moves':[],'solved':0,'cog':[],'script_ratio':[],'plans':[]}}
    
    for i in range(num_solves):
        if verbose: progress_bar(i+1, num_solves, prefix="Running Rubik's sim: ")
        scramble_n = random.randint(5, 20)
        
        c1 = Cube(); c1.scramble(scramble_n); r1 = brute_force_solve(c1)
        data['brute_force']['moves'].append(r1['moves']); data['brute_force']['cog'].append(r1['cognitive_load'])
        if r1['solved']: data['brute_force']['solved'] += 1
        
        c2 = Cube(); c2.scramble(scramble_n); r2 = script_executor_solve(c2, snap)
        data['script_executor']['moves'].append(r2['moves']); data['script_executor']['cog'].append(r2['cognitive_load'])
        if r2['solved']: data['script_executor']['solved'] += 1
        data['script_executor']['script_ratio'].append(r2['script_moves']/max(r2['moves'],1))
        
        c3 = Cube(); c3.scramble(scramble_n); r3 = planning_solver_solve(c3, snap)
        data['planning']['moves'].append(r3['moves']); data['planning']['cog'].append(r3['cognitive_load'])
        if r3['solved']: data['planning']['solved'] += 1
        data['planning']['script_ratio'].append(r3['script_moves']/max(r3['moves'],1))
        data['planning']['plans'].append(r3.get('plans_executed',0))
    
    avg = lambda l: sum(l)/len(l) if l else 0
    return {'num_solves': num_solves, 'solvers': {
        'brute_force': {'avg_moves':round(avg(data['brute_force']['moves']),1),
            'solve_rate':round(data['brute_force']['solved']/num_solves,4),
            'avg_cognitive_load':round(avg(data['brute_force']['cog']),1)},
        'script_executor': {'avg_moves':round(avg(data['script_executor']['moves']),1),
            'solve_rate':round(data['script_executor']['solved']/num_solves,4),
            'avg_cognitive_load':round(avg(data['script_executor']['cog']),1),
            'avg_script_ratio':round(avg(data['script_executor']['script_ratio']),4)},
        'planning': {'avg_moves':round(avg(data['planning']['moves']),1),
            'solve_rate':round(data['planning']['solved']/num_solves,4),
            'avg_cognitive_load':round(avg(data['planning']['cog']),1),
            'avg_script_ratio':round(avg(data['planning']['script_ratio']),4),
            'avg_plans':round(avg(data['planning']['plans']),1)}},
        'insight': "The planning solver should use MORE total moves but LOWER cognitive load, because scripts execute without thinking while the mind plans ahead. The planning solver's advantage is not fewer moves but more FREED COGNITION."}

def display_results(results):
    n = results['num_solves']
    s = results['solvers']
    
    hdr = f"  {'Solver':<18} {'Moves':>7}  {'Solve%':>7}  {'CogLoad':>8}  {'Script%':>8}  {'Plans':>6}"
    sep = "  " + "─" * 60
    rows = []
    for name, d in s.items():
        sr = f"{d['avg_script_ratio']*100:.1f}%" if 'avg_script_ratio' in d else "N/A"
        ap = f"{d['avg_plans']:.1f}" if 'avg_plans' in d else "N/A"
        rows.append(f"  {name:<18} {d['avg_moves']:>7.1f}  {d['solve_rate']*100:>6.1f}%  {d['avg_cognitive_load']:>8.1f}  {sr:>8}  {ap:>6}")
    
    max_sr = max(d['solve_rate'] for d in s.values())
    lines = [None, f"  {n} solves per solver type", None, hdr, sep] + rows + [None]
    
    # Bar comparison for solve rate
    lines.append("  Solve rate comparison:")
    for name, d in s.items():
        bar = ascii_bar(d['solve_rate'], max_sr, 25)
        lines.append(f"    {name:<16} │{bar} {d['solve_rate']*100:.1f}%")
    lines += [None]
    
    # Cognitive load comparison
    min_cog = min(d['avg_cognitive_load'] for d in s.values())
    lines.append("  Cognitive load comparison (lower = better):")
    max_cog = max(d['avg_cognitive_load'] for d in s.values())
    for name, d in s.items():
        bar = ascii_bar(max_cog - d['avg_cognitive_load'] + 1, max_cog + 1, 25)
        lines.append(f"    {name:<16} │{bar} {d['avg_cognitive_load']:.1f}")
    lines += [None]
    
    print(box("🧊 RUBIK'S CUBE SCRIPT ENGINE RESULTS", lines, width=65))
    
    print()
    interp = [None,
        "  WHAT THIS MEANS:",
        None,
        "  Three solvers tackle scrambled cubes:",
        None,
        "  • Brute Force:  Random moves, no memory.",
        "                  Every move = cognitive effort.",
        "                  High load, low solve rate.",
        None,
        "  • Script Executor: Has scripts (known move",
        "    sequences). Snaps current state to nearest",
        "    script and executes it. Script execution is",
        "    free (automatic) — only the SNAP costs cognition.",
        None,
        "  • Planning Solver: Scripts + evaluates which",
        "    script to chain next. More decisions per step,",
        "    but each decision uses freed cognition (scripts",
        "    run on autopilot).",
        None,
        "  💡 The key insight: scripts don't reduce MOVES,",
        "  they reduce COGNITIVE LOAD. The planning solver",
        "  may use more total moves but THINKS less.",
        None,
        "  ⚠️  CAVEAT: These aren't real Rubik's algorithms.",
        "  The scripts are simple patterns. A real solver",
        "  would use CFOP or similar structured methods.",
        None]
    print(box("📋 INTERPRETATION", interp, width=55))

def parse_args():
    parser = argparse.ArgumentParser(description="Rubik's Cube Script Engine Simulator")
    parser.add_argument('--solves', type=int, default=500, help='Solves per type (default: 500)')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 10 solves')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress bar')
    parser.add_argument('--csv', type=str, default=None, help='Export CSV')
    parser.add_argument('--html', type=str, default=None, help='Generate HTML report')
    parser.add_argument('--json-out', type=str, default='results_rubik.json', help='JSON output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    ns = 10 if args.quick else args.solves
    print(f"🧊 Rubik's Cube Script Engine — Running {ns} solves per type...")
    results = run_simulation(ns, verbose=args.verbose)
    with open(args.json_out, 'w') as f: json.dump(results, f, indent=2)
    display_results(results)
    if args.csv: generate_csv(results, args.csv); print(f"\n📄 CSV → {args.csv}")
    if args.html: generate_html(results, args.html); print(f"🌐 HTML → {args.html}")
    print(f"\n✅ JSON → {args.json_out}")
