#!/usr/bin/env python3
"""
Simulator 3: Rubik's Cube Script Engine

Simulate the script-building + mind-freeing cycle.
Three solver types: brute force, script executor, planning solver.
"""

import json
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from collections import defaultdict

# ─── Cube Representation ─────────────────────────────────────────────

# Faces: U(up)=0, D(down)=1, F(front)=2, B(back)=3, L(left)=4, R(right)=5
# Colors: W=0, Y=1, G=2, B=3, O=4, R=5
FACES = 6

class Cube:
    """Simplified 3x3 Rubik's cube representation."""
    
    def __init__(self):
        # 6 faces, each 9 stickers (row-major: 012/345/678)
        self.state = []
        for f in range(6):
            self.state.append([f] * 9)
    
    def copy(self):
        c = Cube()
        c.state = [face[:] for face in self.state]
        return c
    
    def is_solved(self) -> bool:
        return all(len(set(face)) == 1 for face in self.state)
    
    # Moves: each move cycles 4 groups of 3 stickers on adjacent faces
    # + rotates the face itself
    MOVES = ['U', "U'", 'D', "D'", 'F', "F'", 'B', "B'", 'L', "L'", 'R', "R'",
             'U2', 'D2', 'F2', 'B2', 'L2', 'R2']
    
    def rotate_face_cw(self, face: int):
        f = self.state[face]
        self.state[face] = [f[6], f[3], f[0], f[7], f[4], f[1], f[8], f[5], f[2]]
    
    def rotate_face_ccw(self, face: int):
        f = self.state[face]
        self.state[face] = [f[2], f[5], f[8], f[1], f[4], f[7], f[0], f[3], f[6]]
    
    def apply_move(self, move: str):
        s = self.state
        
        if move == 'U':
            self.rotate_face_cw(0)
            temp = s[2][0:3]
            s[2][0:3] = s[4][0:3]
            s[4][0:3] = s[3][0:3]
            s[3][0:3] = s[5][0:3]
            s[5][0:3] = temp
        elif move == "U'":
            self.rotate_face_ccw(0)
            temp = s[2][0:3]
            s[2][0:3] = s[5][0:3]
            s[5][0:3] = s[3][0:3]
            s[3][0:3] = s[4][0:3]
            s[4][0:3] = temp
        elif move == 'D':
            self.rotate_face_cw(1)
            temp = s[2][6:9]
            s[2][6:9] = s[5][6:9]
            s[5][6:9] = s[3][6:9]
            s[3][6:9] = s[4][6:9]
            s[4][6:9] = temp
        elif move == "D'":
            self.rotate_face_ccw(1)
            temp = s[2][6:9]
            s[2][6:9] = s[4][6:9]
            s[4][6:9] = s[3][6:9]
            s[3][6:9] = s[5][6:9]
            s[5][6:9] = temp
        elif move == 'F':
            self.rotate_face_cw(2)
            temp = [s[0][6], s[0][7], s[0][8]]
            s[0][6], s[0][7], s[0][8] = s[4][8], s[4][5], s[4][2]
            s[4][8], s[4][5], s[4][2] = s[1][2], s[1][1], s[1][0]
            s[1][2], s[1][1], s[1][0] = s[5][0], s[5][3], s[5][6]
            s[5][0], s[5][3], s[5][6] = temp[0], temp[1], temp[2]
        elif move == "F'":
            self.rotate_face_ccw(2)
            temp = [s[0][6], s[0][7], s[0][8]]
            s[0][6], s[0][7], s[0][8] = s[5][0], s[5][3], s[5][6]
            s[5][0], s[5][3], s[5][6] = s[1][2], s[1][1], s[1][0]
            s[1][2], s[1][1], s[1][0] = s[4][8], s[4][5], s[4][2]
            s[4][8], s[4][5], s[4][2] = temp[0], temp[1], temp[2]
        elif move == 'B':
            self.rotate_face_cw(3)
            temp = [s[0][0], s[0][1], s[0][2]]
            s[0][0], s[0][1], s[0][2] = s[5][2], s[5][5], s[5][8]
            s[5][2], s[5][5], s[5][8] = s[1][8], s[1][7], s[1][6]
            s[1][8], s[1][7], s[1][6] = s[4][6], s[4][3], s[4][0]
            s[4][6], s[4][3], s[4][0] = temp[0], temp[1], temp[2]
        elif move == "B'":
            self.rotate_face_ccw(3)
            temp = [s[0][0], s[0][1], s[0][2]]
            s[0][0], s[0][1], s[0][2] = s[4][6], s[4][3], s[4][0]
            s[4][6], s[4][3], s[4][0] = s[1][8], s[1][7], s[1][6]
            s[1][8], s[1][7], s[1][6] = s[5][2], s[5][5], s[5][8]
            s[5][2], s[5][5], s[5][8] = temp[0], temp[1], temp[2]
        elif move == 'L':
            self.rotate_face_cw(4)
            temp = [s[0][0], s[0][3], s[0][6]]
            s[0][0], s[0][3], s[0][6] = s[3][8], s[3][5], s[3][2]
            s[3][8], s[3][5], s[3][2] = s[1][0], s[1][3], s[1][6]
            s[1][0], s[1][3], s[1][6] = s[2][0], s[2][3], s[2][6]
            s[2][0], s[2][3], s[2][6] = temp[0], temp[1], temp[2]
        elif move == "L'":
            self.rotate_face_ccw(4)
            temp = [s[0][0], s[0][3], s[0][6]]
            s[0][0], s[0][3], s[0][6] = s[2][0], s[2][3], s[2][6]
            s[2][0], s[2][3], s[2][6] = s[1][0], s[1][3], s[1][6]
            s[1][0], s[1][3], s[1][6] = s[3][8], s[3][5], s[3][2]
            s[3][8], s[3][5], s[3][2] = temp[0], temp[1], temp[2]
        elif move == 'R':
            self.rotate_face_cw(5)
            temp = [s[0][2], s[0][5], s[0][8]]
            s[0][2], s[0][5], s[0][8] = s[2][2], s[2][5], s[2][8]
            s[2][2], s[2][5], s[2][8] = s[1][2], s[1][5], s[1][8]
            s[1][2], s[1][5], s[1][8] = s[3][6], s[3][3], s[3][0]
            s[3][6], s[3][3], s[3][0] = temp[0], temp[1], temp[2]
        elif move == "R'":
            self.rotate_face_ccw(5)
            temp = [s[0][2], s[0][5], s[0][8]]
            s[0][2], s[0][5], s[0][8] = s[3][6], s[3][3], s[3][0]
            s[3][6], s[3][3], s[3][0] = s[1][2], s[1][5], s[1][8]
            s[1][2], s[1][5], s[1][8] = s[2][2], s[2][5], s[2][8]
            s[2][2], s[2][5], s[2][8] = temp[0], temp[1], temp[2]
        elif move == 'U2':
            self.apply_move('U'); self.apply_move('U')
        elif move == 'D2':
            self.apply_move('D'); self.apply_move('D')
        elif move == 'F2':
            self.apply_move('F'); self.apply_move('F')
        elif move == 'B2':
            self.apply_move('B'); self.apply_move('B')
        elif move == 'L2':
            self.apply_move('L'); self.apply_move('L')
        elif move == 'R2':
            self.apply_move('R'); self.apply_move('R')
    
    def apply_sequence(self, moves: List[str]):
        for m in moves:
            self.apply_move(m)
    
    def scramble(self, num_moves: int = 20) -> List[str]:
        """Scramble with random moves, return the scramble sequence."""
        moves = random.choices(Cube.MOVES, k=num_moves)
        for m in moves:
            self.apply_move(m)
        return moves
    
    def state_hash(self) -> str:
        return ''.join(str(s) for face in self.state for s in face)
    
    def count_solved_stickers(self) -> int:
        """Count stickers in correct position."""
        solved = 0
        for f in range(6):
            target = f
            for s in self.state[f]:
                if s == target:
                    solved += 1
        return solved
    
    def heuristic(self) -> float:
        """Lower = closer to solved. Based on sticker correctness."""
        return 54 - self.count_solved_stickers()


# ─── Scripts (Algorithms) ───────────────────────────────────────────

# Some simple scripts: sequences that accomplish known transformations
SCRIPTS = {
    'sexy_move': ['R', 'U', "R'", "U'"],
    'sledgehammer': ["R'", 'F', 'R', "F'"],
    'h_perm': ['R2', 'U2', 'R', 'U2', 'R2', 'U2', 'R2', 'U2', 'R', 'U2', 'R2'],
    't_perm': ['R', 'U', "R'", "U'", "R'", 'F', 'R2', "U'", "R'", "U'", 'R', 'U', "R'", "F'"],
    'y_perm': ['F', 'R', "U'", "R'", "U'", 'R', 'U', "R'", "F'", 'R', 'U', "R'", "U'", "R'", 'F', 'R', "F'"],
    'sune': ['R', 'U', 'R', 'U', 'R', 'U2', "R'"],  # 7 moves
    'anti_sune': ["R'", 'U2', 'R', 'U', "R'", 'U', 'R'],
    'corner_insert': ["R'", "D'", 'R', 'D'],  # repeat to insert corner
    'edge_insert': ['U', 'R', "U'", "R'", "U'", "F'", 'U', 'F'],
    'cross_solve_d': ['F', 'R', 'D'],  # partial cross
}


class SnapDetector:
    """Pattern recognition: snap current cube state to nearest known pattern."""
    
    def __init__(self, scripts: Dict[str, List[str]]):
        self.scripts = scripts
        # Pre-compute what each script does to a solved cube
        self.script_effects = {}
        for name, moves in scripts.items():
            c = Cube()
            c.apply_sequence(moves)
            self.script_effects[name] = c.state_hash()
    
    def snap(self, cube: Cube) -> Optional[Tuple[str, List[str]]]:
        """Try to snap to a known pattern. Returns script name and moves, or None."""
        # Simple snap: try each script's INVERSE to see if it simplifies state
        best_script = None
        best_improvement = 0
        
        for name, moves in self.scripts.items():
            test = cube.copy()
            test.apply_sequence(moves)
            new_h = test.heuristic()
            old_h = cube.heuristic()
            improvement = old_h - new_h
            if improvement > best_improvement:
                best_improvement = improvement
                best_script = (name, moves)
        
        if best_improvement > 0:
            return best_script
        return None


# ─── Solvers ─────────────────────────────────────────────────────────

def brute_force_solve(cube: Cube, max_moves: int = 500) -> dict:
    """Random moves, no scripts."""
    c = cube.copy()
    moves_used = []
    for i in range(max_moves):
        if c.is_solved():
            return {'moves': len(moves_used), 'solved': True, 'cognitive_load': len(moves_used),
                    'script_moves': 0, 'novel_decisions': len(moves_used)}
        move = random.choice(Cube.MOVES)
        c.apply_move(move)
        moves_used.append(move)
    return {'moves': max_moves, 'solved': False, 'cognitive_load': max_moves,
            'script_moves': 0, 'novel_decisions': max_moves}


def script_executor_solve(cube: Cube, snap: SnapDetector, max_moves: int = 300) -> dict:
    """Has scripts but no planning. React-snap-execute."""
    c = cube.copy()
    moves_used = []
    script_moves = 0
    novel_decisions = 0
    
    for i in range(max_moves):
        if c.is_solved():
            return {'moves': len(moves_used), 'solved': True, 
                    'cognitive_load': novel_decisions, 'script_moves': script_moves,
                    'novel_decisions': novel_decisions}
        
        # Try to snap to a script
        result = snap.snap(c)
        if result:
            name, script_moves_list = result
            c.apply_sequence(script_moves_list)
            moves_used.extend(script_moves_list)
            script_moves += len(script_moves_list)
            # Script execution is free (low cognitive load) — just 1 snap decision
            novel_decisions += 1
        else:
            # No script match — random move (high cognitive load)
            move = random.choice(Cube.MOVES)
            c.apply_move(move)
            moves_used.append(move)
            novel_decisions += 1
    
    return {'moves': max_moves, 'solved': c.is_solved(),
            'cognitive_load': novel_decisions, 'script_moves': script_moves,
            'novel_decisions': novel_decisions}


def planning_solver_solve(cube: Cube, snap: SnapDetector, max_moves: int = 300) -> dict:
    """Has scripts + plans 2-3 scripts ahead. Uses freed cognition."""
    c = cube.copy()
    moves_used = []
    script_moves = 0
    novel_decisions = 0
    plans_executed = 0
    
    for i in range(max_moves):
        if c.is_solved():
            return {'moves': len(moves_used), 'solved': True,
                    'cognitive_load': novel_decisions, 'script_moves': script_moves,
                    'novel_decisions': novel_decisions, 'plans_executed': plans_executed}
        
        # Planning: evaluate each script individually, then pick top 2 to chain
        # This is O(S) not O(S²) — much faster
        script_scores = []
        for name, moves in snap.scripts.items():
            test = c.copy()
            test.apply_sequence(moves)
            if test.is_solved():
                # Found a direct solution
                c.apply_sequence(moves)
                moves_used.extend(moves)
                script_moves += len(moves)
                novel_decisions += 1
                plans_executed += 1
                break
            improvement = c.heuristic() - test.heuristic()
            script_scores.append((improvement, name, moves))
        else:
            # Didn't break (no direct solution found)
            script_scores.sort(reverse=True)  # best first
            
            # Pick top script if it improves
            if script_scores and script_scores[0][0] > 0:
                _, name, moves = script_scores[0]
                c.apply_sequence(moves)
                moves_used.extend(moves)
                script_moves += len(moves)
                novel_decisions += 1
                plans_executed += 1
            else:
                # Semi-guided random: sample 5 moves, pick best
                best_move = random.choice(Cube.MOVES)
                best_h = c.heuristic()
                for m in random.sample(Cube.MOVES, min(5, len(Cube.MOVES))):
                    test = c.copy()
                    test.apply_move(m)
                    h = test.heuristic()
                    if h < best_h:
                        best_h = h
                        best_move = m
                c.apply_move(best_move)
                moves_used.append(best_move)
                novel_decisions += 1
            continue
        continue  # after direct solve break
    
    return {'moves': len(moves_used), 'solved': c.is_solved(),
            'cognitive_load': novel_decisions, 'script_moves': script_moves,
            'novel_decisions': novel_decisions, 'plans_executed': plans_executed}


def run_simulation(num_solves: int = 1000) -> dict:
    """Run all three solver types."""
    
    snap = SnapDetector(SCRIPTS)
    
    results = {
        'brute_force': {'moves': [], 'solved': 0, 'cognitive_load': [], 'times': []},
        'script_executor': {'moves': [], 'solved': 0, 'cognitive_load': [], 'script_ratio': []},
        'planning': {'moves': [], 'solved': 0, 'cognitive_load': [], 'script_ratio': [], 'plans': []},
    }
    
    for solve_num in range(num_solves):
        scramble_moves = random.randint(5, 20)
        
        # Brute force
        cube1 = Cube()
        cube1.scramble(scramble_moves)
        r1 = brute_force_solve(cube1)
        results['brute_force']['moves'].append(r1['moves'])
        results['brute_force']['cognitive_load'].append(r1['cognitive_load'])
        if r1['solved']:
            results['brute_force']['solved'] += 1
        
        # Script executor
        cube2 = Cube()
        cube2.scramble(scramble_moves)
        r2 = script_executor_solve(cube2, snap)
        results['script_executor']['moves'].append(r2['moves'])
        results['script_executor']['cognitive_load'].append(r2['cognitive_load'])
        if r2['solved']:
            results['script_executor']['solved'] += 1
        total_m = max(r2['moves'], 1)
        results['script_executor']['script_ratio'].append(r2['script_moves'] / total_m)
        
        # Planning solver
        cube3 = Cube()
        cube3.scramble(scramble_moves)
        r3 = planning_solver_solve(cube3, snap)
        results['planning']['moves'].append(r3['moves'])
        results['planning']['cognitive_load'].append(r3['cognitive_load'])
        if r3['solved']:
            results['planning']['solved'] += 1
        total_m = max(r3['moves'], 1)
        results['planning']['script_ratio'].append(r3['script_moves'] / total_m)
        results['planning']['plans'].append(r3.get('plans_executed', 0))
    
    # Aggregate
    def avg(lst): return sum(lst) / len(lst) if lst else 0
    
    output = {
        'num_solves': num_solves,
        'solvers': {
            'brute_force': {
                'avg_moves': round(avg(results['brute_force']['moves']), 1),
                'solve_rate': round(results['brute_force']['solved'] / num_solves, 4),
                'avg_cognitive_load': round(avg(results['brute_force']['cognitive_load']), 1),
            },
            'script_executor': {
                'avg_moves': round(avg(results['script_executor']['moves']), 1),
                'solve_rate': round(results['script_executor']['solved'] / num_solves, 4),
                'avg_cognitive_load': round(avg(results['script_executor']['cognitive_load']), 1),
                'avg_script_ratio': round(avg(results['script_executor']['script_ratio']), 4),
            },
            'planning': {
                'avg_moves': round(avg(results['planning']['moves']), 1),
                'solve_rate': round(results['planning']['solved'] / num_solves, 4),
                'avg_cognitive_load': round(avg(results['planning']['cognitive_load']), 1),
                'avg_script_ratio': round(avg(results['planning']['script_ratio']), 4),
                'avg_plans': round(avg(results['planning']['plans']), 1),
            },
        },
        'insight': (
            "The planning solver should use MORE total moves but LOWER cognitive load, "
            "because scripts execute without thinking while the mind plans ahead. "
            "The planning solver's advantage is not fewer moves but more FREED COGNITION."
        ),
    }
    
    return output


if __name__ == '__main__':
    print("🧊 Rubik's Cube Script Engine — Running 500 solves per type...")
    results = run_simulation(500)
    
    with open('results_rubik.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to results_rubik.json")
    for name, data in results['solvers'].items():
        print(f"\n  {name}:")
        print(f"    Avg moves: {data['avg_moves']}")
        print(f"    Solve rate: {data['solve_rate']*100:.1f}%")
        print(f"    Avg cognitive load: {data['avg_cognitive_load']}")
        if 'avg_script_ratio' in data:
            print(f"    Script ratio: {data['avg_script_ratio']*100:.1f}%")
        if 'avg_plans' in data:
            print(f"    Avg plans: {data['avg_plans']}")
