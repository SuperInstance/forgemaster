#!/usr/bin/env python3
"""
Simulator 1: Poker Attention Engine

Simulates poker players using snap-based attention with tunable tolerance per information layer.
Tests whether well-calibrated snap functions (attending to the RIGHT things) improve win rate.
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
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
    """Simplified hand strength: sum of rank values + bonus for pairs/suits."""
    if not cards:
        return 0.0
    vals = sorted([c.value() for c in cards], reverse=True)
    score = sum(vals) / (len(vals) * 12.0)  # normalize to 0-1
    
    # Pair bonus
    rank_counts = defaultdict(int)
    for c in cards:
        rank_counts[c.rank] += 1
    for count in rank_counts.values():
        if count >= 2: score += 0.15 * count
        if count >= 3: score += 0.2
        if count >= 4: score += 0.3
    
    # Flush bonus
    suit_counts = defaultdict(int)
    for c in cards:
        suit_counts[c.suit] += 1
    if max(suit_counts.values()) >= 5: score += 0.4
    elif max(suit_counts.values()) >= 4: score += 0.15
    
    # Straight bonus
    unique_vals = sorted(set(vals))
    if len(unique_vals) >= 5:
        for i in range(len(unique_vals) - 4):
            if unique_vals[i+4] - unique_vals[i] == 4:
                score += 0.3
                break
    
    return min(score, 1.0)


# ─── Information Layers ──────────────────────────────────────────────

@dataclass
class InfoLayer:
    """Each layer has a different randomness flavor and tolerance."""
    name: str
    flavor: str  # 'cubic', 'categorical', 'directional', 'combinatorial'
    tolerance: float  # 0.0 = very tight, 1.0 = very loose
    baseline: float = 0.5
    
    def snap(self, value: float) -> Tuple[bool, float]:
        """Returns (snapped, delta). snapped=True means within tolerance (ignore)."""
        delta = abs(value - self.baseline)
        if delta <= self.tolerance:
            return True, delta  # snapped to baseline, ignore
        return False, delta  # delta detected, attend


@dataclass
class Player:
    name: str
    layers: Dict[str, InfoLayer]
    chips: int = 1000
    hand: List[Card] = field(default_factory=list)
    behavior: str = 'neutral'  # tight, loose, tilting, neutral
    emotional_state: float = 0.5
    betting_aggression: float = 0.5
    
    def total_deltas(self, game_state: dict) -> Tuple[List[Tuple[str, float]], List[str]]:
        """Check all layers for deltas. Returns (deltas, attended_layers)."""
        deltas = []
        attended = []
        
        # Layer 1: Card probabilities (cubic/uniform)
        card_delta = game_state.get('card_probability', 0.5)
        snapped, delta_val = self.layers['cards'].snap(card_delta)
        if not snapped:
            deltas.append(('cards', delta_val))
            attended.append('cards')
        else:
            self.layers['cards'].baseline = 0.7 * self.layers['cards'].baseline + 0.3 * card_delta
        
        # Layer 2: Player behavior (categorical)
        behavior_map = {'tight': 0.2, 'loose': 0.8, 'tilting': 0.95, 'neutral': 0.5}
        beh_val = behavior_map.get(game_state.get('opponent_behavior', 'neutral'), 0.5)
        snapped, delta_val = self.layers['behavior'].snap(beh_val)
        if not snapped:
            deltas.append(('behavior', delta_val))
            attended.append('behavior')
        else:
            self.layers['behavior'].baseline = 0.7 * self.layers['behavior'].baseline + 0.3 * beh_val
        
        # Layer 3: Betting patterns (directional)
        bet_val = game_state.get('bet_aggression', 0.5)
        snapped, delta_val = self.layers['betting'].snap(bet_val)
        if not snapped:
            deltas.append(('betting', delta_val))
            attended.append('betting')
        else:
            self.layers['betting'].baseline = 0.7 * self.layers['betting'].baseline + 0.3 * bet_val
        
        # Layer 4: Emotional state (combinatorial)
        emo_val = game_state.get('emotional_delta', 0.5)
        snapped, delta_val = self.layers['emotion'].snap(emo_val)
        if not snapped:
            deltas.append(('emotion', delta_val))
            attended.append('emotion')
        else:
            self.layers['emotion'].baseline = 0.7 * self.layers['emotion'].baseline + 0.3 * emo_val
        
        return deltas, attended
    
    def decide_action(self, game_state: dict, call_amount: int) -> Tuple[str, int]:
        """Decide fold/call/raise based on deltas and hand strength."""
        deltas, attended = self.total_deltas(game_state)
        
        # Base decision on hand strength
        strength = hand_strength(self.hand)
        
        # Weight deltas by layer importance for this player profile
        action_score = strength
        
        for layer_name, delta_val in deltas:
            if layer_name == 'behavior':
                # Attending to behavior gives info about opponent's hand
                action_score += 0.1 * delta_val * (1 if game_state.get('opponent_behavior') == 'tight' else -0.5)
            elif layer_name == 'emotion':
                # Emotional delta in opponent = weakness signal
                action_score += 0.08 * delta_val
            elif layer_name == 'betting':
                # Aggressive betting delta = opponent strength OR bluff
                action_score -= 0.05 * delta_val
            elif layer_name == 'cards':
                # Card probability delta — novice overweights this
                action_score += 0.03 * delta_val
        
        # Decision
        if action_score > 0.65 and self.chips > call_amount * 2:
            raise_amt = min(int(call_amount * (1 + action_score)), self.chips)
            return 'raise', raise_amt
        elif action_score > 0.35:
            return 'call', call_amount
        else:
            return 'fold', 0


def create_profile(name: str, profile_type: str) -> Player:
    """Create a player with a tolerance profile."""
    if profile_type == 'novice':
        # Loose on cards (attends to wrong things), tight on behavior (misses reads)
        layers = {
            'cards': InfoLayer('cards', 'cubic', tolerance=0.05),      # very tight → lots of card deltas
            'behavior': InfoLayer('behavior', 'categorical', tolerance=0.9),  # very loose → misses behavior
            'betting': InfoLayer('betting', 'directional', tolerance=0.6),
            'emotion': InfoLayer('emotion', 'combinatorial', tolerance=0.8),   # loose → misses emotion
        }
    elif profile_type == 'intermediate':
        layers = {
            'cards': InfoLayer('cards', 'cubic', tolerance=0.3),
            'behavior': InfoLayer('behavior', 'categorical', tolerance=0.3),
            'betting': InfoLayer('betting', 'directional', tolerance=0.3),
            'emotion': InfoLayer('emotion', 'combinatorial', tolerance=0.3),
        }
    elif profile_type == 'expert':
        # Tight on behavior/emotion (reads people), loose on cards (doesn't obsess)
        layers = {
            'cards': InfoLayer('cards', 'cubic', tolerance=0.8),       # loose → ignores most card noise
            'behavior': InfoLayer('behavior', 'categorical', tolerance=0.08),  # tight → catches every tell
            'betting': InfoLayer('betting', 'directional', tolerance=0.15),
            'emotion': InfoLayer('emotion', 'combinatorial', tolerance=0.05),  # very tight → reads micro-deltas
        }
    else:  # baseline — no snap (everything gets attention equally)
        layers = {
            'cards': InfoLayer('cards', 'cubic', tolerance=0.01),
            'behavior': InfoLayer('behavior', 'categorical', tolerance=0.01),
            'betting': InfoLayer('betting', 'directional', tolerance=0.01),
            'emotion': InfoLayer('emotion', 'combinatorial', tolerance=0.01),
        }
    
    return Player(name=name, layers=layers)


def play_hand(players: List[Player], deck: List[Card]) -> dict:
    """Simulate one hand of poker."""
    idx = 0
    for p in players:
        p.hand = [deck[idx], deck[idx+1]]
        idx += 2
    
    # Flop
    community = [deck[idx], deck[idx+1], deck[idx+2]]
    idx += 3
    
    # Turn
    community.append(deck[idx])
    idx += 1
    
    # River
    community.append(deck[idx])
    
    # Simulate opponent behavior signals (random but correlated to hand)
    behaviors = ['tight', 'loose', 'tilting', 'neutral']
    
    # Play rounds
    pot = 0
    active = list(range(len(players)))
    results = {p.name: {'deltas_per_round': defaultdict(int), 'layers_attended': defaultdict(int),
                         'total_deltas': 0, 'actions': []} for p in players}
    
    for round_name in ['preflop', 'flop', 'turn', 'river']:
        # Generate game state signals
        for i, p in enumerate(players):
            if i not in active:
                continue
            
            opponent_idx = [j for j in active if j != i]
            if not opponent_idx:
                continue
            
            opp = players[opponent_idx[0]]
            opp_strength = hand_strength(opp.hand + community[:{'preflop':0,'flop':3,'turn':4,'river':5}[round_name]])
            
            game_state = {
                'card_probability': hand_strength(p.hand + community[:{'preflop':0,'flop':3,'turn':4,'river':5}[round_name]]),
                'opponent_behavior': random.choice(behaviors[:2]) if opp_strength < 0.4 else random.choice(behaviors[1:]),
                'bet_aggression': min(1.0, opp_strength + random.gauss(0, 0.15)),
                'emotional_delta': abs(random.gauss(0.5, 0.2) - 0.5) + opp_strength * 0.3,
            }
            
            call_amount = 20
            action, amount = p.decide_action(game_state, call_amount)
            
            results[p.name]['actions'].append(action)
            
            # Track deltas
            deltas, attended = p.total_deltas(game_state)
            results[p.name]['deltas_per_round'][round_name] = len(deltas)
            results[p.name]['total_deltas'] += len(deltas)
            for layer in attended:
                results[p.name]['layers_attended'][layer] += 1
            
            if action == 'fold' and i in active:
                active.remove(i)
            elif action == 'call':
                actual = min(amount, p.chips)
                p.chips -= actual
                pot += actual
            elif action == 'raise':
                actual = min(amount, p.chips)
                p.chips -= actual
                pot += actual
    
    # Determine winner
    best_strength = -1
    winner = active[0] if active else 0
    for i in active:
        s = hand_strength(players[i].hand + community)
        if s > best_strength:
            best_strength = s
            winner = i
    
    players[winner].chips += pot
    
    return {
        'winner': players[winner].name,
        'pot': pot,
        'player_results': {p.name: {
            'won': p.name == players[winner].name,
            'final_chips': p.chips,
            'deltas_per_round': dict(results[p.name]['deltas_per_round']),
            'layers_attended': dict(results[p.name]['layers_attended']),
            'total_deltas': results[p.name]['total_deltas'],
        } for p in players}
    }


def run_simulation(num_hands: int = 10000) -> dict:
    """Run the full poker simulation."""
    profiles = ['novice', 'intermediate', 'expert', 'baseline']
    
    cumulative_wins = defaultdict(int)
    cumulative_deltas = defaultdict(list)
    cumulative_layers = defaultdict(lambda: defaultdict(int))
    chip_history = defaultdict(list)
    attention_efficiency = defaultdict(list)  # deltas per win
    
    for hand_num in range(num_hands):
        players = [create_profile(f"{p}_{hand_num%100}", p) for p in profiles]
        deck = make_deck()
        result = play_hand(players, deck)
        
        for p in profiles:
            pname = f"{p}_{hand_num%100}"
            if pname in result['player_results']:
                pr = result['player_results'][pname]
                if pr['won']:
                    cumulative_wins[p] += 1
                cumulative_deltas[p].append(pr['total_deltas'])
                for layer, count in pr['layers_attended'].items():
                    cumulative_layers[p][layer] += count
    
    # Compute results
    results = {
        'num_hands': num_hands,
        'profiles': {},
        'summary': {},
    }
    
    for p in profiles:
        wins = cumulative_wins[p]
        avg_deltas = sum(cumulative_deltas[p]) / len(cumulative_deltas[p]) if cumulative_deltas[p] else 0
        win_rate = wins / num_hands
        
        results['profiles'][p] = {
            'wins': wins,
            'win_rate': round(win_rate, 4),
            'avg_deltas_per_hand': round(avg_deltas, 2),
            'attention_efficiency': round(wins / max(sum(cumulative_deltas[p]), 1) * 100, 4),
            'layers_attended': dict(cumulative_layers[p]),
        }
    
    # Key insight: who attends to what
    results['summary'] = {
        'best_win_rate': max(results['profiles'].items(), key=lambda x: x[1]['win_rate'])[0],
        'most_efficient_attention': max(results['profiles'].items(), key=lambda x: x[1]['attention_efficiency'])[0],
        'insight': (
            "Expert profile (tight on behavior/emotion, loose on cards) should win most because "
            "it attends to the RIGHT deltas — player behavior and emotional micro-deltas — "
            "rather than wasting attention on card probability noise."
        ),
    }
    
    return results


if __name__ == '__main__':
    print("🎰 Poker Attention Engine — Running 10,000 hands...")
    results = run_simulation(10000)
    
    with open('results_poker.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to results_poker.json")
    print(f"\n📊 Win Rates:")
    for profile, data in results['profiles'].items():
        print(f"  {profile:15s}: {data['win_rate']*100:.1f}% wins, {data['avg_deltas_per_hand']:.1f} avg deltas/hand, "
              f"efficiency={data['attention_efficiency']:.4f}")
    print(f"\n🏆 Best: {results['summary']['best_win_rate']}")
    print(f"⚡ Most efficient attention: {results['summary']['most_efficient_attention']}")
