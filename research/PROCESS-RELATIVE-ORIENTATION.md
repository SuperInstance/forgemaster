# Process-Relative Orientation — The Real Keel

> Not "what time is it."
> "Should that be done by now?"

## The Wrong Question

The atomic clock asks: "What time is it?"
The self-centered keel asks: "Where am I relative to myself?"

Both miss the point. The real question is:

**"Given what I know about process A's dynamics, and given where I am in my own process, should process A have reached its expected state by now?"**

This is not self-referential. This is not external. This is **inter-process mathematical expectation**.

## The Ship Analogy

A sailor doesn't need a clock. The sailor needs to know:

- The helmsman started turning 30° to port. The rudder is this size, the boat is this speed, the turn should complete in roughly 3 boat-lengths. We've traveled 4 boat-lengths. The turn should be done. Is it done?

- The deckhand was sent to reef the mainsail. The sail is that size, the wind is this strong, a reef takes about 2 minutes of steady work. The deckhand has been up there longer than it takes to reef. Is the sail reefed?

- The engine was started at idle. It should reach operating temperature after 5 minutes at idle RPM, or equivalently, after the cooling system has cycled twice. Has the cooling system cycled?

Each of these is: **given the mathematical model of process X, and given the observable state of process Y that should constrain X, has X reached its expected completion point?**

No clock. No "what time is it." Just: **does the math say this should be done?**

## The Fleet Analogy

Agent A is running a constraint evaluation. Given the dimensionality (N=200), the coupling topology (4 agents, 0.25 coupling), and the gain (0.95), the evaluation should converge in:

```
convergence_steps ≈ f(N, coupling, gain, topology)
```

From our 42 experiments, we KNOW this function. The phase diagram IS the convergence model.

If agent A's process should converge in ~50 steps at these parameters, and agent B (which depends on A's output) has been waiting 200 steps, something is wrong. Not because a clock says so. Because the MATH of A's convergence says it should have finished at step 50.

Agent B doesn't need to know "what time is it." Agent B needs to know: "given A's parameters and my model of A's dynamics, should A be done?"

## The Mathematical Framework

Each process has a **trajectory envelope** — the set of states it should occupy at each point in its execution, given its parameters.

```
Process P with parameters θ:
  trajectory(t) ∈ envelope(t, θ)
  
  For each step t:
    expected_state(t) = attractor(θ)
    expected_deviation(t) = δ(θ) × exp(-t/τ(θ))
    expected_convergence(t) = 1 - exp(-t/τ(θ))
```

Agent A running process P doesn't need a clock. It just asks:

```
am_I_converged() = |current_state - expected_state| < tolerance
```

Agent B watching Agent A doesn't need a clock either. It asks:

```
should_A_be_done() = steps_elapsed > convergence_time(A's θ)
is_A_actually_done() = A's output_state within A's expected envelope
```

If `should_A_be_done()` and NOT `is_A_actually_done()`: **A is late.**

"Lateness" is not measured in seconds. It's measured in **deviation from mathematical expectation**.

## What This Means for Keel Orientation

The keel doesn't just orient the agent against its own attractor. The keel orients the agent against OTHER agents' expected trajectories.

The keel reads:
1. **My position** relative to my attractor (self-orientation)
2. **My convergence** relative to my expected trajectory (am I done?)
3. **My neighbors' convergence** relative to THEIR expected trajectories (should they be done?)
4. **The fleet's convergence** relative to the fleet phase diagram (are we in the living zone?)
5. **The discrepancy** between expected and actual states across all visible processes (is anything late?)

This is process-relative time. Not wall clock. Not self-referential. **Mathematical expectation of other processes.**

## Concrete Example

Agent 0 runs a constraint cascade. The cascade has depth D=5, each level processes N=200 constraints, and the coupling between levels follows the fleet dynamics we measured.

From our experiments:
- Each level converges in τ ≈ 1/(1-0.95) ≈ 20 steps (from the gain dynamics)
- Total cascade convergence: D × τ ≈ 100 steps
- With coupling to 3 other agents: convergence faster (from E1 scaling law)

So Agent 1, which needs Agent 0's cascade output, knows:
- Agent 0's cascade should converge in ~100 steps (from the math)
- I've been running for 150 steps since Agent 0 started
- Agent 0 should be done
- Is Agent 0's output stable? Check: output deviation < tolerance?

If Agent 0's output is still changing at step 150, Agent 1 doesn't think "it's been 150 seconds." Agent 1 thinks "the math says this should have converged at step 100. It hasn't. Something is wrong with Agent 0's process."

This is not a clock. This is a **process model used as a temporal reference**.

## Why This Is Different From Clocks

| Clock-Based | Process-Relative |
|------------|-----------------|
| "It has been 5 seconds" | "Process X should be done by now" |
| Time is external, uniform | Time is internal, process-specific |
| All processes share one clock | Each process has its own convergence model |
| Lateness = wall_time - expected_wall_time | Lateness = steps_elapsed - expected_convergence_steps |
| Requires sync (NTP) | Requires knowledge of other processes' dynamics |
| Fails when clock drifts | Fails when process model is wrong |
| Precision = clock quality | Precision = model quality |

Process-relative time is **stronger** than clock time because it carries semantic information. "Process X is late" is more informative than "5 seconds have passed." The lateness tells you about the PROCESS, not just the DURATION.

## The Keel's True Function

The keel doesn't just feel the boat's motion. The keel feels the boat's motion RELATIVE TO WHAT THE WATER AND WIND SHOULD BE PRODUCING.

If the boat should be turning at 3°/second given the current rudder angle and speed, and the boat is only turning at 1°/second, the keel doesn't say "you've been turning for 5 seconds." The keel says "you're turning slower than you should be." The keel compares ACTUAL dynamics to EXPECTED dynamics.

The expected dynamics come from the mathematical model. The actual dynamics come from observation. The discrepancy IS the temporal signal.

The keel reads the gap between math and reality. That gap IS time.

## The Deepest Point

Time is not a dimension. Time is the gap between mathematical expectation and observed reality.

When every process is exactly where the math says it should be — no discrepancy — there IS no time. Everything is "on schedule." Time only appears when things deviate from expectation. The larger the deviation, the more "time" has passed (or been lost).

This is why the keel is process-relative. The keel doesn't measure duration. The keel measures discrepancy. And discrepancy between expected and actual states IS the only kind of time that matters for a fleet of coupled processes.

Atomic clocks measure duration. Keels measure discrepancy. Duration is meaningless for a fleet. Discrepancy is everything.
