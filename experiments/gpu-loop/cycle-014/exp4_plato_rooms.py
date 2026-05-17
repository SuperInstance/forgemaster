"""
Experiment 4 (v4): Multi-Room PLATO Simulation
Use bounded nonlinear dynamics (logistic-map style) that maintain non-trivial steady states.
Track how coupling topology affects information distribution across rooms.
"""
import numpy as np
import json

def plato_rooms_experiment():
    np.random.seed(42)
    
    class PLATORoom:
        """Room with bounded logistic-style dynamics. State ∈ (0, 1)."""
        def __init__(self, room_id, dim=5):
            self.id = room_id
            self.dim = dim
            # Each dimension has its own growth rate (r_i ∈ [2.5, 3.5] — below chaos)
            self.r = 2.5 + np.random.rand(dim) * 1.0
            self.state = 0.1 + 0.8 * np.random.rand(dim)
            
        @property
        def information(self):
            """Shannon-like information: -sum(p * log(p))"""
            s = np.clip(self.state, 1e-10, 1 - 1e-10)
            return -np.sum(s * np.log(s) + (1-s) * np.log(1-s))
        
        def step(self, coupling_signal=None, eta=0.05):
            # Logistic map: x_{n+1} = r * x_n * (1 - x_n)
            self.state = self.r * self.state * (1 - self.state)
            self.state = np.clip(self.state, 1e-10, 1 - 1e-10)
            
            # Coupling: average with neighbors (diffusive)
            if coupling_signal is not None:
                self.state = (1 - eta) * self.state + eta * coupling_signal
                self.state = np.clip(self.state, 1e-10, 1 - 1e-10)
    
    def build_topology(n_rooms, topology):
        if topology == 'star':
            return [(0, i) for i in range(1, n_rooms)]
        elif topology == 'ring':
            return [(i, (i+1) % n_rooms) for i in range(n_rooms)]
        elif topology == 'full':
            return [(i, j) for i in range(n_rooms) for j in range(i+1, n_rooms)]
        elif topology == 'chain':
            return [(i, i+1) for i in range(n_rooms - 1)]
        elif topology == 'tree':
            edges = []
            for i in range(1, n_rooms):
                parent = (i - 1) // 2
                edges.append((parent, i))
            return edges
        return []
    
    topologies = ['star', 'ring', 'full', 'chain', 'tree']
    room_counts = [3, 5, 7, 9]
    n_steps = 1000
    n_trials = 30
    eta = 0.05
    
    all_results = []
    
    for n_rooms in room_counts:
        for topology in topologies:
            edges = build_topology(n_rooms, topology)
            
            conservation_errors = []
            final_cvs = []
            cv_traces_all = []
            I_total_traces = []
            
            for trial in range(n_trials):
                np.random.seed(trial * 137 + n_rooms * 31 + hash(topology) % 997)
                rooms = [PLATORoom(i) for i in range(n_rooms)]
                
                I_initial_total = sum(r.information for r in rooms)
                
                cv_trace = []
                I_total_trace = []
                
                for step in range(n_steps):
                    coupling = {i: [] for i in range(n_rooms)}
                    for (i, j) in edges:
                        coupling[i].append(rooms[j].state.copy())
                        coupling[j].append(rooms[i].state.copy())
                    
                    for room in rooms:
                        signals = coupling.get(room.id, [])
                        if signals:
                            avg_signal = np.mean(signals, axis=0)
                            room.step(avg_signal, eta)
                        else:
                            room.step()
                    
                    Is = [r.information for r in rooms]
                    mean_I = np.mean(Is)
                    cv = np.std(Is) / mean_I if mean_I > 0 else 0
                    cv_trace.append(cv)
                    I_total_trace.append(sum(Is))
                
                I_final_total = I_total_trace[-1]
                # Conservation: how much does total I change?
                cons_err = np.abs(I_final_total - I_initial_total) / I_initial_total
                conservation_errors.append(cons_err)
                
                # Use last 200 steps for steady-state CV
                steady_cv = np.mean(cv_trace[-200:])
                final_cvs.append(steady_cv)
                cv_traces_all.append(cv_trace)
                I_total_traces.append(I_total_trace)
                
            mean_cv_trace = np.mean(cv_traces_all, axis=0)
            mean_I_trace = np.mean(I_total_traces, axis=0)
            
            # CV reduction: compare transient (steps 0-50) to steady state (last 200)
            cv_transient = np.mean(mean_cv_trace[:50])
            cv_steady = np.mean(mean_cv_trace[-200:])
            cv_reduction = (cv_transient - cv_steady) / cv_transient * 100 if cv_transient > 0 else 0
            
            # I conservation over time
            I_std_relative = np.std(mean_I_trace) / np.mean(mean_I_trace) if np.mean(mean_I_trace) > 0 else 0
            
            all_results.append({
                'n_rooms': n_rooms,
                'topology': topology,
                'n_edges': len(edges),
                'mean_conservation_error': float(np.mean(conservation_errors)),
                'mean_steady_CV': float(np.mean(final_cvs)),
                'std_steady_CV': float(np.std(final_cvs)),
                'cv_reduction_pct': float(cv_reduction),
                'cv_transient': float(cv_transient),
                'cv_steady': float(cv_steady),
                'I_relative_std': float(I_std_relative),
            })
    
    print("=" * 70)
    print("EXPERIMENT 4 (v4): Multi-Room PLATO Simulation")
    print("=" * 70)
    
    print(f"\n{'Rooms':>5} | {'Topo':>6} | {'Edges':>5} | {'I_rel_std':>9} | {'CV_trans':>8} | {'CV_stdy':>8} | {'CV Red%':>8}")
    print("-" * 70)
    for r in all_results:
        print(f"{r['n_rooms']:>5} | {r['topology']:>6} | {r['n_edges']:>5} | {r['I_relative_std']:>9.4f} | {r['cv_transient']:>8.4f} | {r['cv_steady']:>8.4f} | {r['cv_reduction_pct']:>7.1f}%")
    
    topo_stats = {}
    for t in topologies:
        entries = [r for r in all_results if r['topology'] == t]
        topo_stats[t] = {
            'mean_steady_CV': float(np.mean([e['mean_steady_CV'] for e in entries])),
            'mean_cv_reduction': float(np.mean([e['cv_reduction_pct'] for e in entries])),
            'mean_I_relative_std': float(np.mean([e['I_relative_std'] for e in entries])),
            'edges_per_room': float(np.mean([e['n_edges'] / e['n_rooms'] for e in entries])),
        }
    
    print("\n\nTopology Rankings (by lowest steady-state CV):")
    print(f"{'Topology':>8} | {'Steady CV':>9} | {'CV Red%':>8} | {'I_rel_std':>9} | {'Edges/Room':>10}")
    print("-" * 55)
    for t in sorted(topo_stats.keys(), key=lambda x: topo_stats[x]['mean_steady_CV']):
        s = topo_stats[t]
        print(f"{t:>8} | {s['mean_steady_CV']:>9.4f} | {s['mean_cv_reduction']:>7.1f}% | {s['mean_I_relative_std']:>9.4f} | {s['edges_per_room']:>10.2f}")
    
    best = min(topo_stats.keys(), key=lambda x: topo_stats[x]['mean_steady_CV'])
    
    # Room count effect
    room_stats = {}
    for n in room_counts:
        entries = [r for r in all_results if r['n_rooms'] == n]
        room_stats[n] = float(np.mean([e['mean_steady_CV'] for e in entries]))
    
    print("\n\nCV vs Room Count:")
    for n in sorted(room_stats.keys()):
        print(f"  N={n}: mean CV = {room_stats[n]:.4f}")
    
    return {
        'all_results': all_results,
        'topology_stats': topo_stats,
        'room_count_stats': room_stats,
        'best_topology': best,
        'conservation_summary': f"Total I fluctuates with relative std {np.mean([r['I_relative_std'] for r in all_results]):.4f}. "
                               f"Coupling distributes information but doesn't conserve total I exactly.",
    }

if __name__ == '__main__':
    data = plato_rooms_experiment()
    with open('/home/phoenix/.openclaw/workspace/experiments/gpu-loop/cycle-014/exp4_results.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("\nResults saved to exp4_results.json")
