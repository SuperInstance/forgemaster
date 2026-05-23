# Cross-Domain Decomposition Engine Applications

## The Pattern

```
Expensive:   Large model/pattern matching → generates candidate (conjecture)
Cheap:       Local verifier → confirms or rejects candidate at chip speed
Key insight: The verifier O(1) or O(n) in input size, NOT in candidate space
```

The decomposition engine works because the search space is enormous but verification is nearly free. Here are 10 domains with the same structure.

---

## 1. Compiler Optimization

**Conjecture:** `is_correct(original_ir, transformed_ir) → bool`
The large model (or SMT solver) proposes a transformation: dead-code elimination, loop unrolling, instruction reordering. The conjecture is "this transformation preserves semantics for ALL inputs."

**Local verifier:**
```python
def verify_semantic_equivalence(orig_blocks: list[BasicBlock], 
                                 trans_blocks: list[BasicBlock]) -> Verdict:
    # Step 1: Block-level bisimulation
    for ob, tb in zip(orig_blocks, trans_blocks):
        if not diamond_match(ob.defs, tb.uses, ob.uses, tb.defs):
            return Verdict.REFUTED  # O(block size) comparison
    # Step 2: Opcode-level assuming single-static assignment
    for ob, tb in zip(orig_blocks, trans_blocks):
        for oop, top in zip(ob.ops, tb.ops):
            if not commutative_match(oop, top):
                return Verdict.REFUTED  # constant-time opcode lookup
    return Verdict.VERIFIED  # O(n) in program size, no SAT solving
```

- **Verifier speed:** 1-50 µs per block pair
- **Docker sandbox:** Yes — pure computation, no side effects
- **Killer app:** Compile-time optimization without proof burden. Ship aggressive loop transformations, auto-vectorization, and parallelization — the verifier catches unsound transforms instantly. Zero bugs from optimization passes.

**Concrete experiment:** Take LLVM IR from -O2, randomly apply peephole optimizations, use verifier to reject unsound ones. Measure: what % of random transforms pass verification? How many valid optimizations are discovered that -O2 misses?

---

## 2. Physics Simulation (Preservation Laws)

**Conjecture:** `conserves_invariants(state_before, state_after, timestep) → bool`
A learned or adaptive integrator proposes a simplification: coarser grid here, skip particle interaction there. The conjecture is "energy, momentum, and symplectic structure are preserved within tolerance."

**Local verifier:**
```python
def verify_conservation(state: PhysicsState, 
                        proposed: TimestepResult, 
                        tolerances: dict[str, float]) -> Verdict:
    # Energy check: Σ E_kinetic + E_potential ± dissipation
    e_before = total_energy(state)
    e_after  = total_energy(proposed)
    if abs(e_after - e_before) > tolerances["energy"]:
        return Verdict.REFUTED  # O(N_particles), no integration
    
    # Momentum check: Σ mass * velocity
    p_before, p_after = momentum(state), momentum(proposed)
    if norm(p_after - p_before) > tolerances["momentum"]:
        return Verdict.REFUTED
    
    # Symplectic check: phase space volume
    if not symplectic_ratio(state, proposed, 0.99, 1.01):
        return Verdict.REFUTED
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 10-100 µs for 10K particles (O(N), no pairwise force recomputation)
- **Docker sandbox:** Yes
- **Killer app:** Adaptive simulation at scale. Use cheap NN to propose next timestep's integration strategy, verify conservation in <100 µs. Throw away unstable configurations before they diverge. Run years-long climate/plasma simulations with guaranteed invariant bounds.

**Concrete experiment:** N-body gravitational simulation. Use a learned predictor to propose skipping force computation for 30% of pairs. Verifier checks energy/momentum drift. Measure: how many timesteps can be accelerated before the verifier rejects? What's the speedup on 100M particles?

---

## 3. Drug Design (Binding Affinity)

**Conjecture:** `binds(protein_pocket, candidate_ligand) → float`
A generative model (diffusion, GNN) proposes a novel molecule. The conjecture is "this molecule binds with ΔG < -7 kcal/mol."

**Local verifier:**
```python
def verify_binding(protein_residues: list[Residue], 
                   ligand_atoms: list[Atom],
                   pharmacophore_model: Pharmacophore) -> Verdict:
    # Steric clash check — O(N_ligand × N_pocket surface)
    for latom in ligand_atoms:
        for patom in protein_surface(protein_residues, latom.radius * 2):
            if distance(latom.pos, patom.pos) < clash_threshold(latom, patom):
                return Verdict.REFUTED  # 3D distance, ~ns
    
    # Pharmacophore match — O(N_features), precomputed pocket vectors
    if not pharmacophore_model.score(ligand_atoms) > 0.7:
        return Verdict.REFUTED
    
    # Lipinski rule-of-five — O(1), molecular descriptors
    if not lipinski_check(ligand_atoms):
        return Verdict.REFUTED
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 50-500 µs per candidate (vs 1-60 min for full MD simulation)
- **Docker sandbox:** Yes
- **Killer app:** Screen 10M candidates per second instead of 10K. Generative drug design where the model proposes, the verifier filters, and only the top 0.1% go to expensive MD. Discover scaffolds that satisfy all hard constraints simultaneously.

**Concrete experiment:** Use a VAE or diffusion model to generate 100K novel ligands for a target pocket. Verifier filters to ~500 passing steric+pharmacophore checks. Send those 500 to full MD. Measure: what fraction of verifier-passing candidates actually bind in MD? What's the enrichment factor over random screening?

---

## 4. Financial Modeling (Strategy Validation)

**Conjecture:** `profitable(strategy_params, historical_slice) → (return, risk)`
An ML model proposes a trading strategy: buy when X < threshold, sell when Y > threshold. The conjecture is "this strategy produces Sharpe > 2.0 out of sample."

**Local verifier:**
```python
def verify_strategy(strategy: Strategy,
                    price_data: np.ndarray,      # [T, N_assets]
                    volume_data: np.ndarray,
                    lookback: int = 252) -> Verdict:
    # O(T) vectorized — this is FAST (~100µs for 10 years of daily data)
    signals = strategy.generate(price_data, lookback)
    portfolio = simulate_portfolio(signals, price_data, volume_data)
    
    sharpe = portfolio.sharpe_ratio()
    max_dd = portfolio.max_drawdown()
    turnover = portfolio.annual_turnover()
    hit_rate = portfolio.win_rate()
    
    # Literally three scalar comparisons
    if sharpe < 2.0:
        return Verdict.REFUTED
    if max_dd > 0.3:
        return Verdict.REFUTED
    if turnover > 5.0:
        return Verdict.REFUTED  # unrealistic transaction costs
    
    # Chow test for structural breaks in returns
    if chow_test(portfolio.daily_returns, breakpoints=[lookback//2]) < 0.01:
        return Verdict.REFUTED  # strategy is data-mined
        
    return Verdict.VERIFIED
```

- **Verifier speed:** 100-500 µs for 10 years of daily data (vectorized numpy)
- **Docker sandbox:** Yes
- **Killer app:** Evolutionary strategy discovery. Generate 10M candidate strategies per hour, verify against random historical slices, keep the top 0.1%. Discover non-obvious regime-specific strategies. The verifier prevents overfitting by requiring consistent performance across slices.

**Concrete experiment:** Use a genetic algorithm to evolve trading strategies on 20 years of S&P 500 data. Verifier checks every candidate against 5 random 2-year slices. Track: how many generations until a strategy passes verification? What's its out-of-sample Sharpe vs the best single strategy?

---

## 5. Security (Code Vulnerability Detection)

**Conjecture:** `vulnerable(code_snippet, vulnerability_pattern) → bool`
A large language model proposes that a code path contains a specific vulnerability: buffer overflow, SQL injection, use-after-free. The conjecture is "this specific execution path produces undefined behavior."

**Local verifier:**
```python
def verify_vulnerability(cfg: ControlFlowGraph,
                         vulnerability: VulnerabilityType,
                         taint_sources: set[str],
                         taint_sinks: set[str]) -> Verdict:
    if vulnerability == VulnerabilityType.BUFFER_OVERFLOW:
        # Check all array accesses along the path — O(path_length)
        for block in cfg.path:
            for instr in block.instructions:
                if instr.op == "LOAD" or instr.op == "STORE":
                    if instr.base in taint_sources:
                        offset_range = range_analysis(instr.offset)
                        bounds = allocation_bounds(instr.base)
                        if offset_range.lower < 0 or offset_range.upper > bounds:
                            return Verdict.CONFIRMED  # O(1) range check
        return Verdict.UNCONFIRMED
    
    elif vulnerability == VulnerabilityType.SQL_INJECTION:
        # String-taint tracking — O(expression_tree_depth)
        for block in cfg.path:
            for instr in block.instructions:
                if instr.is_sink(taint_sinks):
                    taint_chain = collect_taint_path(instr, cfg)
                    for arg in taint_chain:
                        if not sanitized(arg):
                            return Verdict.CONFIRMED
        return Verdict.UNCONFIRMED
```

- **Verifier speed:** 1-50 µs per path (static analysis, no execution)
- **Docker sandbox:** Yes
- **Killer app:** Real-time vulnerability discovery during code review. GitHub pushes a PR, model proposes 100 candidate vulnerabilities, verifier checks each in a few ms. Surface only confirmed vulnerabilities. Catch SQL injection before the reviewer finishes reading the diff.

**Concrete experiment:** Take 1000 CVEs with known root causes. For each CVE, use an LLM to generate 50 candidate vulnerability hypotheses (mixing true and false). Run the verifier on all 50K candidates. Measure: precision, recall, and average verification time. Can we hit 95% accuracy?

---

## 6. Networking (Routing Optimality)

**Conjecture:** `optimal(proposed_route, topology, constraints) → bool`
An ML model or heuristic proposes a new routing table or traffic engineering strategy. The conjecture is "this routing minimizes latency under the given capacity constraints."

**Local verifier:**
```python
def verify_routing(topology: Graph,
                   routing: dict[Node, dict[Node, Path]],
                   demands: dict[tuple[Node, Node], float],
                   capacities: dict[Edge, float]) -> Verdict:
    # Flow feasibility — O(V × E) with precomputed paths
    edge_loads = defaultdict(float)
    for (src, dst), demand in demands.items():
        path = routing[src][dst]
        for edge in path.edges:
            edge_loads[edge] += demand
            if edge_loads[edge] > capacities[edge]:
                return Verdict.REFUTED  # Literally: compare float to float
    
    # Hop-by-hop latency check
    for (src, dst), path in routing[src].items():
        actual_latency = sum(edge.latency for edge in path.edges)
        # Check against precomputed all-pairs shortest path bound
        if actual_latency > 2.0 * asp_bounds[src][dst]:
            return Verdict.REFUTED  # Too far from optimal
    return Verdict.VERIFIED
```

- **Verifier speed:** 1-10 µs per route (O(path_length))
- **Docker sandbox:** Yes
- **Killer app:** Self-optimizing networks. Deploy a controller that continuously proposes routing updates, verifies them in µs against current topology, and deploys only safe ones. Achieve near-optimal throughput without centralized optimization.

**Concrete experiment:** Mininet emulation with 100 nodes and dynamic traffic. Controller proposes routing changes every 100ms. Verifier checks feasibility in <100µs. Measure: throughput vs OSPF, and how many proposed routes are rejected?

---

## 7. Machine Learning (Architecture Validation)

**Conjecture:** `viable(architecture_dict, hyperparams) → bool`
A meta-learning system proposes a neural architecture: layer types, widths, connections, regularization. The conjecture is "this architecture can converge on the target task."

**Local verifier:**
```python
def verify_architecture(arch: Architecture, 
                        sample_input: torch.Tensor,
                        expected_shape: torch.Size) -> Verdict:
    # Forward shape propagation — O(L), L = number of layers
    x = sample_input
    for layer in arch.layers:
        try:
            x = layer.forward_shape(x)
        except ShapeMismatch:
            return Verdict.REFUTED  # Incompatible dimensions
    
    if x.shape != expected_shape:
        return Verdict.REFUTED  # Output shape wrong
    
    # Gradient flow sanity — one forward+backward pass, no learning
    params = arch.init_params()
    out = arch.forward(sample_input)
    loss = dummy_loss(out, expected_shape)
    try:
        loss.backward()
    except RuntimeError:
        return Verdict.REFUTED  # Gradient explosion or NaN
    
    # Check gradient norms are finite
    for p in params:
        if p.grad is None or not torch.isfinite(p.grad).all():
            return Verdict.REFUTED
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 1-10 ms per architecture (single forward+backward on CPU)
- **Docker sandbox:** Yes
- **Killer app:** Neural architecture search at scale. Generate 1M architectures per hour, verify each in ~1ms, train only the top 0.1%. Discover architectures that satisfy gradient flow constraints automatically.

**Concrete experiment:** Use random search over NAS-Bench-201 space. Verifier checks shape compatibility and gradient health on a tiny batch. Measure: how many architectures would fail training due to shape errors, gradient explosions, or NaN? What % of verifier-passing architectures can train to >90% test accuracy?

---

## 8. Robotics (Trajectory Safety)

**Conjecture:** `safe(proposed_trajectory, environment_model) → bool`
A learned planner proposes a robot trajectory through a dynamic environment. The conjecture is "this trajectory has zero collision probability and satisfies joint limits."

**Local verifier:**
```python
def verify_trajectory(trajectory: Trajectory,
                      occupancy: DistanceField,
                      joint_limits: JointLimits,
                      dt: float = 0.01) -> Verdict:
    # Swept-volume collision check — O(K × log(N)), K = waypoints
    for t in range(len(trajectory.waypoints)):
        config = trajectory.waypoints[t]
        # Joint limit check — O(DOF), 6-7 for arm, ~20 for humanoid
        for joint in range(trajectory.dof):
            if config[joint] < joint_limits.lower[joint]:
                return Verdict.REFUTED
            if config[joint] > joint_limits.upper[joint]:
                return Verdict.REFUTED
        
        # Distance field lookup — O(1) for grid, O(log N) for KD-tree
        dist = occupancy.signed_distance(config.position)
        if dist < safety_margin:
            return Verdict.REFUTED
        
        # Velocity/acceleration bounds — O(DOF), finite difference
        if t > 0:
            vel = (config - trajectory.waypoints[t-1]) / dt
            if norm(vel) > velocity_limit:
                return Verdict.REFUTED
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 10-100 µs per 100-waypoint trajectory
- **Docker sandbox:** Yes (with simulated environment)
- **Killer app:** Real-time replanning in dynamic environments. Robot generates 1000 candidate trajectories per second, verifier filters to safe ones, controller picks the best safe candidate. React to obstacles at human reaction speed with formal safety guarantees.

**Concrete experiment:** 7-DOF robot arm in a cluttered environment with moving obstacles. Planner proposes random trajectories. Verifier checks collision + joint limits. Measure: verifier throughput (trajectories/second), false positive rate (verified-safe but actually collides), and false negative rate.

---

## 9. Game Design (Level Balance)

**Conjecture:** `balanced(level_layout, game_rules) → bool`
A procedural content generator proposes a game level. The conjecture is "this level is solvable, winnable, and has appropriate difficulty."

**Local verifier:**
```python
def verify_level(level: Level,
                 player_model: PlayerSimulator,
                 difficulty_target: float) -> Verdict:
    # Solvability check — BFS/DFS through level topology
    reachable = bfs(level, level.start, level.exit)
    if not reachable:
        return Verdict.REFUTED  # Literally: path exists?
    
    # Resource balance — O(N_tiles), static analysis
    resources = count_resources(level)
    if resources.health_pickups < resources.traps * 0.5:
        return Verdict.REFUTED  # Player can't survive
    
    # Difficulty estimation — fast simulation with heuristic AI
    sim = AI_playthrough(level, player_model, max_steps=1000)
    if not sim.completed:
        return Verdict.REFUTED
    if not (difficulty_target * 0.8 < sim.difficulty_score < difficulty_target * 1.2):
        return Verdict.REFUTED
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 50-500 µs per level (BFS + simple AI simulation)
- **Docker sandbox:** Yes
- **Killer app:** Infinite procedural content. A generative model proposes 100K levels, verifier filters to the top 1K, and only those get rendered. Games with unlimited unique, balanced levels that are guaranteed playable.

**Concrete experiment:** Generate levels for a 2D platformer using a VAE. Verifier checks solvability, resource balance, and difficulty. Measure: what % of generated levels pass verification? How does the diversity of verified levels compare to hand-authored ones?

---

## 10. Climate Modeling (Parameterization Trust)

**Conjecture:** `conserves(proposed_parameterization, historical_era) → bool`
An ML emulator proposes a simpler parameterization for cloud microphysics or boundary layer turbulence. The conjecture is "this simplification doesn't introduce systematic bias in the mean state."

**Local verifier:**
```python
def verify_parameterization(param: Parameterization,
                            gridcell: GridCell,
                            historical_stats: Climatology) -> Verdict:
    # Single-column verification — O(vertical_levels)
    # Much cheaper than 3D GCM run (months vs microseconds)
    column_before = gridcell.column_profile
    column_after = param.apply(column_before)
    
    # Mass conservation — O(N_levels)
    mass_before = sum(level.density * level.thickness for level in column_before)
    mass_after = sum(level.density * level.thickness for level in column_after)
    if abs(mass_after - mass_before) / mass_before > 1e-6:
        return Verdict.REFUTED
    
    # Energy conservation — O(N_levels), same check
    energy_before = sum(level.temperature * level.specific_heat for level in column_before)
    energy_after = sum(level.temperature * level.specific_heat for level in column_after)
    if abs(energy_after - energy_before) / energy_before > 1e-6:
        return Verdict.REFUTED
    
    # Statistical consistency — compare against historical ERA5
    if not within_climate_envelope(column_after, historical_stats.at(gridcell.location)):
        return Verdict.REFUTED  # Produces unrealistic profiles
    
    return Verdict.VERIFIED
```

- **Verifier speed:** 10-50 µs per grid cell (single-column, no 3D dynamics)
- **Docker sandbox:** Yes
- **Killer app:** Machine learning parameterizations with physics guarantees. Train ML to emulate expensive cloud microphysics, verify conservation and climatology at every grid cell in every timestep. Run 100-year simulations with confidence that the learned parameterization doesn't drift.

**Concrete experiment:** Use a neural network to emulate a double-moment cloud microphysics scheme. Verifier checks mass/energy conservation per grid cell. Measure: what % of NN proposals pass verification? How much faster is the emulated scheme with verification than the full scheme?

---

## Summary Table

| Domain | Conjecture | Verifier | Speed | Docker |
|--------|-----------|----------|-------|--------|
| Compiler opt | Transform preserves semantics | Block/opcode bisimulation | 1-50 µs | ✅ |
| Physics sim | Conserves invariants | Energy + momentum comparison | 10-100 µs | ✅ |
| Drug design | Molecule binds | Steric + pharmacophore filter | 50-500 µs | ✅ |
| Financial | Strategy profitable | Vectorized backtest (O(T)) | 100-500 µs | ✅ |
| Security | Code path is vulnerable | Taint propagation + range check | 1-50 µs | ✅ |
| Networking | Route is optimal | Capacity + latency check | 1-10 µs | ✅ |
| ML/NAS | Architecture trains | Shape check + gradient health | 1-10 ms | ✅ |
| Robotics | Trajectory is safe | Distance field collision check | 10-100 µs | ✅ |
| Game design | Level is balanced | Solvability + resource check | 50-500 µs | ✅ |
| Climate | Parameterization conservative | Single-column column check | 10-50 µs | ✅ |

## The Common Architecture

Every domain shares this structure:

1. **Explosion of candidates** — The large model/planner samples from a space that's exponentially larger than what verification can cover
2. **Verifier is O(input) or O(1)** — Never O(candidate space). The verifier checks necessary conditions using cheap computation
3. **Verifier is sound but incomplete** — It catches bad candidates but may miss good ones. Perfection costs are pushed to the expensive model
4. **Candidates pass the filter** — The top fraction go to full evaluation, and the verifier's necessary-condition guarantee means you never waste expensive resources on obviously bad candidates

The decomposition engine isn't a single algorithm — it's an architectural pattern that any large-decision-space problem under a cheap-check constraint can exploit.
