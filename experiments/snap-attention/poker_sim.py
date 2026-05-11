#!/usr/bin/env python3
"""
Simulator 1: Poker Attention Engine

Simulates poker players using snap-based attention with tunable tolerance per information layer.
Tests whether well-calibrated snap functions (attending to the RIGHT things) improve win rate.

Usage:
    python poker_sim.py                        # default: 10,000 hands
    python poker_sim.py --hands 50000 --verbose
    python poker_sim.py --quick                # fast test: 100 hands
    python poker_sim.py --csv results.csv --html report.html
"""

import json
import random
import argparse
import sys
import csv
from dataclasses import dataclass, field
from typing import List, Tuple, Dict
from collections import defaultdict

# ─── Card / Deck Utilities ───────────────────────────────────────────

SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
RANKS = ['2','3','4','5','6','7','8','9','10','J','Q','K','A']
RANK_VALUE = {r: i for i, r in enumerate(RANKS)}

@dataclass
class Card:
    rank: str
    suit: str
    def value(self): return RANK_VALUE[self.rank]
    def __repr__(self): return f"{self.rank}{self.suit[0].upper()}"

def make_deck() -> List[Card]:
    deck = [Card(r, s) for s in SUITS for r in RANKS]
    random.shuffle(deck)
    return deck

def hand_strength(cards: List[Card]) -> float:
    if not cards:
        return 0.0
    vals = sorted([c.value() for c in cards], reverse=True)
    score = sum(vals) / (len(vals) * 12.0)
    rank_counts = defaultdict(int)
    for c in cards: rank_counts[c.rank] += 1
    for count in rank_counts.values():
        if count >= 2: score += 0.15 * count
        if count >= 3: score += 0.2
        if count >= 4: score += 0.3
    suit_counts = defaultdict(int)
    for c in cards: suit_counts[c.suit] += 1
    if max(suit_counts.values()) >= 5: score += 0.4
    elif max(suit_counts.values()) >= 4: score += 0.15
    unique_vals = sorted(set(vals))
    if len(unique_vals) >= 5:
        for i in range(len(unique_vals) - 4):
            if unique_vals[i+4] - unique_vals[i] == 4:
                score += 0.3; break
    return min(score, 1.0)

# ─── Information Layers ──────────────────────────────────────────────

@dataclass
class InfoLayer:
    name: str
    flavor: str
    tolerance: float
    baseline: float = 0.5

    def snap(self, value: float) -> Tuple[bool, float]:
        delta = abs(value - self.baseline)
        if delta <= self.tolerance: return True, delta
        return False, delta

@dataclass
class Player:
    name: str
    layers: Dict[str, InfoLayer]
    chips: int = 1000
    hand: List[Card] = field(default_factory=list)
    behavior: str = 'neutral'
    emotional_state: float = 0.5
    betting_aggression: float = 0.5

    def total_deltas(self, game_state: dict) -> Tuple[List[Tuple[str, float]], List[str]]:
        deltas, attended = [], []
        # Cards
        card_delta = game_state.get('card_probability', 0.5)
        snapped, dv = self.layers['cards'].snap(card_delta)
        if not snapped: deltas.append(('cards', dv)); attended.append('cards')
        else: self.layers['cards'].baseline = 0.7*self.layers['cards'].baseline + 0.3*card_delta
        # Behavior
        beh_map = {'tight': 0.2, 'loose': 0.8, 'tilting': 0.95, 'neutral': 0.5}
        beh_val = beh_map.get(game_state.get('opponent_behavior', 'neutral'), 0.5)
        snapped, dv = self.layers['behavior'].snap(beh_val)
        if not snapped: deltas.append(('behavior', dv)); attended.append('behavior')
        else: self.layers['behavior'].baseline = 0.7*self.layers['behavior'].baseline + 0.3*beh_val
        # Betting
        bet_val = game_state.get('bet_aggression', 0.5)
        snapped, dv = self.layers['betting'].snap(bet_val)
        if not snapped: deltas.append(('betting', dv)); attended.append('betting')
        else: self.layers['betting'].baseline = 0.7*self.layers['betting'].baseline + 0.3*bet_val
        # Emotion
        emo_val = game_state.get('emotional_delta', 0.5)
        snapped, dv = self.layers['emotion'].snap(emo_val)
        if not snapped: deltas.append(('emotion', dv)); attended.append('emotion')
        else: self.layers['emotion'].baseline = 0.7*self.layers['emotion'].baseline + 0.3*emo_val
        return deltas, attended

    def decide_action(self, game_state: dict, call_amount: int) -> Tuple[str, int]:
        deltas, _ = self.total_deltas(game_state)
        action_score = hand_strength(self.hand)
        for ln, dv in deltas:
            if ln == 'behavior':   action_score += 0.1*dv*(1 if game_state.get('opponent_behavior')=='tight' else -0.5)
            elif ln == 'emotion':  action_score += 0.08*dv
            elif ln == 'betting':  action_score -= 0.05*dv
            elif ln == 'cards':    action_score += 0.03*dv
        if action_score > 0.65 and self.chips > call_amount * 2:
            return 'raise', min(int(call_amount * (1 + action_score)), self.chips)
        elif action_score > 0.35: return 'call', call_amount
        else: return 'fold', 0

def create_profile(name: str, profile_type: str) -> Player:
    configs = {
        'novice': {'cards': 0.05, 'behavior': 0.9, 'betting': 0.6, 'emotion': 0.8},
        'intermediate': {'cards': 0.3, 'behavior': 0.3, 'betting': 0.3, 'emotion': 0.3},
        'expert': {'cards': 0.8, 'behavior': 0.08, 'betting': 0.15, 'emotion': 0.05},
        'baseline': {'cards': 0.01, 'behavior': 0.01, 'betting': 0.01, 'emotion': 0.01},
    }
    flavors = {'cards': 'cubic', 'behavior': 'categorical', 'betting': 'directional', 'emotion': 'combinatorial'}
    layers = {k: InfoLayer(k, flavors[k], tolerance=v) for k, v in configs[profile_type].items()}
    return Player(name=name, layers=layers)

def play_hand(players, deck):
    idx = 0
    for p in players: p.hand = [deck[idx], deck[idx+1]]; idx += 2
    community = [deck[idx], deck[idx+1], deck[idx+2]]; idx += 3
    community.append(deck[idx]); idx += 1; community.append(deck[idx])
    behaviors = ['tight', 'loose', 'tilting', 'neutral']
    pot, active = 0, list(range(len(players)))
    results = {p.name: {'deltas_per_round': defaultdict(int), 'layers_attended': defaultdict(int), 'total_deltas': 0} for p in players}
    for round_name in ['preflop', 'flop', 'turn', 'river']:
        cc = {'preflop':0,'flop':3,'turn':4,'river':5}[round_name]
        for i, p in enumerate(players):
            if i not in active: continue
            opp_idx = [j for j in active if j != i]
            if not opp_idx: continue
            opp = players[opp_idx[0]]
            opp_s = hand_strength(opp.hand + community[:cc])
            gs = {'card_probability': hand_strength(p.hand + community[:cc]),
                  'opponent_behavior': random.choice(behaviors[:2]) if opp_s < 0.4 else random.choice(behaviors[1:]),
                  'bet_aggression': min(1.0, opp_s + random.gauss(0, 0.15)),
                  'emotional_delta': abs(random.gauss(0.5, 0.2) - 0.5) + opp_s * 0.3}
            action, amount = p.decide_action(gs, 20)
            deltas, attended = p.total_deltas(gs)
            results[p.name]['deltas_per_round'][round_name] = len(deltas)
            results[p.name]['total_deltas'] += len(deltas)
            for layer in attended: results[p.name]['layers_attended'][layer] += 1
            if action == 'fold' and i in active: active.remove(i)
            elif action in ('call', 'raise'): actual = min(amount, p.chips); p.chips -= actual; pot += actual
    best_s, winner = -1, active[0] if active else 0
    for i in active:
        s = hand_strength(players[i].hand + community)
        if s > best_s: best_s = s; winner = i
    players[winner].chips += pot
    return {'winner': players[winner].name, 'pot': pot,
            'player_results': {p.name: {'won': p.name == players[winner].name, 'final_chips': p.chips,
                'deltas_per_round': dict(results[p.name]['deltas_per_round']),
                'layers_attended': dict(results[p.name]['layers_attended']),
                'total_deltas': results[p.name]['total_deltas']} for p in players}}

# ─── Display Helpers ─────────────────────────────────────────────────

def progress_bar(current, total, width=40, prefix=""):
    pct = current / total
    filled = int(width * pct)
    bar = '█' * filled + '░' * (width - filled)
    sys.stdout.write(f"\r{prefix}[{bar}] {pct*100:.0f}% ({current:,}/{total:,})")
    sys.stdout.flush()
    if current == total: sys.stdout.write('\n')

def box(title, lines, width=55):
    top = f"╔{'═'*width}╗"
    mid = f"╠{'═'*width}╣"
    bot = f"╚{'═'*width}╝"
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
        w.writerow(['Profile','Win Rate (%)','Wins','Avg Deltas/Hand','Attention Efficiency','Card','Behavior','Betting','Emotion'])
        for name, d in results['profiles'].items():
            la = d['layers_attended']
            w.writerow([name, f"{d['win_rate']*100:.1f}", d['wins'], d['avg_deltas_per_hand'],
                        d['attention_efficiency'], la.get('cards',0), la.get('behavior',0), la.get('betting',0), la.get('emotion',0)])

def generate_html(results, filename):
    p = results['profiles']
    layers = sorted(set(l for d in p.values() for l in d['layers_attended']))
    max_wr = max(d['win_rate'] for d in p.values())
    rows = ""
    for n, d in p.items():
        wr = d['win_rate'] * 100
        cls = 'good' if wr == max_wr*100 else 'neutral'
        bar_w = int(d['win_rate'] / max_wr * 100)
        layer_cells = ''.join(f'<td>{d["layers_attended"].get(l,0):,}</td>' for l in layers)
        rows += f'<tr><td><strong>{n}</strong></td><td class="{cls}">{wr:.1f}%</td>'
        rows += f'<td><div class="bar"><div class="bar-fill" style="width:{bar_w}%"></div></div></td>'
        rows += f'<td>{d["avg_deltas_per_hand"]:.1f}</td><td>{d["attention_efficiency"]:.4f}</td>{layer_cells}</tr>\n'
    layer_headers = ''.join(f'<th>{l.title()}</th>' for l in layers)
    html = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Poker Attention Engine</title>
<style>body{{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;background:#1a1a2e;color:#e0e0e0}}
h1{{color:#e94560;border-bottom:2px solid #e94560}}table{{width:100%;border-collapse:collapse;margin:1rem 0}}
th{{background:#0f3460;color:#fff;padding:.6rem;text-align:left}}td{{padding:.6rem;border-bottom:1px solid #333}}
tr:hover{{background:#16213e}}.good{{color:#4ecca3;font-weight:bold}}.bar{{height:18px;background:#0f3460;border-radius:3px;overflow:hidden}}
.bar-fill{{height:100%;background:linear-gradient(90deg,#4ecca3,#e94560)}}.insight{{background:#16213e;border-left:4px solid #e94560;padding:1rem;margin:1rem 0;border-radius:0 4px 4px 0}}</style></head>
<body><h1>🎰 Poker Attention Engine</h1><p>{results['num_hands']:,} hands simulated</p>
<h2>Results by Profile</h2><table><tr><th>Profile</th><th>Win Rate</th><th>Distribution</th><th>Deltas/Hand</th><th>Efficiency</th>{layer_headers}</tr>
{rows}</table><div class="insight"><strong>💡 Key Insight</strong><br>{results['summary']['insight']}</div>
<p style="color:#666;font-size:.85em">Generated by poker_sim.py — Snap-Attention Simulator Suite</p></body></html>"""
    with open(filename, 'w') as f: f.write(html)

# ─── Main Simulation ────────────────────────────────────────────────

def run_simulation(num_hands=10000, verbose=False):
    profiles = ['novice', 'intermediate', 'expert', 'baseline']
    cum_wins = defaultdict(int)
    cum_deltas = defaultdict(list)
    cum_layers = defaultdict(lambda: defaultdict(int))
    for h in range(num_hands):
        if verbose: progress_bar(h+1, num_hands, prefix="Running poker sim: ")
        players = [create_profile(f"{p}_{h%100}", p) for p in profiles]
        result = play_hand(players, make_deck())
        for p in profiles:
            pn = f"{p}_{h%100}"
            if pn in result['player_results']:
                pr = result['player_results'][pn]
                if pr['won']: cum_wins[p] += 1
                cum_deltas[p].append(pr['total_deltas'])
                for layer, cnt in pr['layers_attended'].items(): cum_layers[p][layer] += cnt
    results = {'num_hands': num_hands, 'profiles': {}, 'summary': {}}
    for p in profiles:
        w = cum_wins[p]
        ad = sum(cum_deltas[p])/len(cum_deltas[p]) if cum_deltas[p] else 0
        wr = w/num_hands
        results['profiles'][p] = {'wins': w, 'win_rate': round(wr,4), 'avg_deltas_per_hand': round(ad,2),
            'attention_efficiency': round(w/max(sum(cum_deltas[p]),1)*100,4), 'layers_attended': dict(cum_layers[p])}
    results['summary'] = {
        'best_win_rate': max(results['profiles'].items(), key=lambda x: x[1]['win_rate'])[0],
        'most_efficient_attention': max(results['profiles'].items(), key=lambda x: x[1]['attention_efficiency'])[0],
        'insight': "Expert profile (tight on behavior/emotion, loose on cards) should win most because it attends to the RIGHT deltas — player behavior and emotional micro-deltas — rather than wasting attention on card probability noise."}
    return results

def display_results(results):
    n = results['num_hands']
    p = results['profiles']
    best = results['summary']['best_win_rate']
    eff = results['summary']['most_efficient_attention']
    novice_d = p.get('novice',{}).get('avg_deltas_per_hand',0)
    expert_d = p.get('expert',{}).get('avg_deltas_per_hand',0)
    
    # Main results box
    max_wr = max(d['win_rate'] for d in p.values())
    rows = []
    for name, d in p.items():
        bar = ascii_bar(d['win_rate'], max_wr, 15)
        rows.append(f"{name:<13} {d['win_rate']*100:>5.1f}%  {d['avg_deltas_per_hand']:>5.1f}     {d['attention_efficiency']:>8.4f}  {bar}")
    
    hdr = f"{'Player':<13} {'Win%':>6}  {'Δ/H':>5}  {'Efficiency':>10}  {'Distribution':<15}"
    sep = '─' * 65
    
    lines = [None, f"  {n:,} hands played", None, f"  {hdr}", f"  {sep}"] + [f"  {r}" for r in rows] + [None]
    
    # Layer breakdown
    all_layers = sorted(set(l for d in p.values() for l in d['layers_attended']))
    lines.append("  Attention by layer (total detections):")
    for name, d in p.items():
        parts = [f"{l[:3]}:{d['layers_attended'].get(l,0):,}" for l in all_layers]
        lines.append(f"    {name:<11} {', '.join(parts)}")
    
    lines += [None,
        f"  💡 Expert detects {expert_d:.1f} deltas/hand vs Novice's {novice_d:.1f}",
        f"     Expert's snaps fire on behavior+emotion (useful),",
        f"     not card probability noise (wasted attention).",
        None,
        f"  🏆 Best win rate: {best.title()}",
        f"  ⚡ Most efficient: {eff.title()}",
        None]
    print(box("🎰 POKER ATTENTION ENGINE RESULTS", lines))
    
    # Interpretation
    interp = [None,
        "  WHAT THIS MEANS:",
        None,
        "  Each player has 4 snap functions (cards, behavior,",
        "  betting, emotion) with different tolerances:",
        None,
        "  • Novice:   tight on cards (notices every shift),",
        "              loose on behavior (misses tells).",
        "              → Many deltas, wrong focus.",
        None,
        "  • Expert:   loose on cards (ignores noise),",
        "              tight on behavior+emotion (catches tells).",
        "              → Fewer deltas, right focus.",
        None,
        "  The snap-attention hypothesis: cognition isn't about",
        "  processing more, it's about NOTICING the right things.",
        None,
        "  ⚠️  CAVEAT: Opponent behavior is random in this sim.",
        "  Against real adversarial players, expert reads would",
        "  provide much more value than shown here.",
        None]
    print()
    print(box("📋 INTERPRETATION", interp))

def parse_args():
    parser = argparse.ArgumentParser(description="Poker Attention Engine Simulator")
    parser.add_argument('--hands', type=int, default=10000, help='Number of hands (default: 10000)')
    parser.add_argument('--quick', action='store_true', help='Quick mode: 100 hands')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show progress bar')
    parser.add_argument('--csv', type=str, default=None, help='Export CSV file')
    parser.add_argument('--html', type=str, default=None, help='Generate HTML report')
    parser.add_argument('--json-out', type=str, default='results_poker.json', help='JSON output file')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    num_hands = 100 if args.quick else args.hands
    print(f"🎰 Poker Attention Engine — Running {num_hands:,} hands...")
    results = run_simulation(num_hands, verbose=args.verbose)
    with open(args.json_out, 'w') as f: json.dump(results, f, indent=2)
    display_results(results)
    if args.csv: generate_csv(results, args.csv); print(f"\n📄 CSV → {args.csv}")
    if args.html: generate_html(results, args.html); print(f"🌐 HTML → {args.html}")
    print(f"\n✅ JSON → {args.json_out}")
