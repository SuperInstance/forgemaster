# Shaking the Rigging — Perturbation as Discovery

> You don't inspect every line. You shake the rigging and feel what pulls back.
> The knobs you twist reveal the system. The system reveals itself through its deltas.

## What Casey Named

A sailor doesn't climb the mast and visually inspect every stay, shroud, and halyard before rough weather. That would take hours and you'd miss things. Instead, they shake the rigging. Grab a line, give it a yank, and feel what's connected. The line that pulls back taut is load-bearing. The line that's loose needs attention. The line that doesn't pull back at all is broken or disconnected.

The shake IS the test. The feel IS the inspection. The rigging tells you its own state through its response to perturbation.

This is the same pattern as the musician. But now we see it's not just about convergence. It's about **discovery of the system itself**.

## Stochastic Computing on Purpose

Stochastic computing represents numbers as probability streams — a bit that's 1 with probability p encodes the value p. You do arithmetic by doing logic on the streams: AND for multiplication, MUX for weighted average, XOR for addition. The precision increases with the length of the stream. The computation is inherently noisy but converges.

The key insight: **the noise IS the computation.** You don't remove the noise. You USE it. The stochastic fluctuations carry information about the system state.

Casey's connection: shaking the rigging is stochastic computing applied to the physical world. Each shake is a random perturbation. The response is the computation. The pattern of responses across many shakes reveals the system's structure.

## Seeded Model Programming (SMPagents)

SMPagents — seeded model programming agents — are models initialized from a seed (a specific weight configuration, a latent vector, a constraint DNA profile). The seed determines the starting point, but the agent's behavior emerges from the interaction between the seed and the environment.

The question: **which seeds are stable?** Which ones produce coherent behavior, and which ones collapse into noise?

Traditional approach: run each seed for 1000 steps, measure metrics, rank them. Expensive. Slow. Requires knowing what to measure.

Musician's approach: **twist knobs on the seed and listen.**

```
Seed: {eisenstein_radius: 42, tolerance: 0.05, snap_margin: 7}

Twist 1: eisenstein_radius += 1
  → listen: does the agent's behavior shift smoothly? (stable)
  → or does it explode? (unstable, sensitive to this dimension)

Twist 2: tolerance -= 0.01
  → listen: does constraint satisfaction change gradually? (robust)
  → or does it flip from all-satisfied to all-violated? (brittle)

Twist 3: snap_margin *= 1.5
  → listen: does the agent find new stable configurations? (explorable)
  → or does it lock to the same attractor regardless? (rigid)
```

Each twist is a shake of the rigging. The response tells you what that parameter is connected to. Parameters that produce large deltas from small perturbations are load-bearing — they're the ones that matter. Parameters that produce small deltas are redundant or decoupled.

## The Shake Protocol

### Step 1: Find the Stays (Parameter Sensitivity)

```python
def shake_rigging(seed, perturbation_scale=0.01):
    """
    Shake every parameter in the seed and measure the response.
    Like grabbing every line on the boat and feeling what pulls back.
    """
    results = {}
    for param_name, param_value in seed.parameters.items():
        # Shake positive
        seed.parameters[param_name] = param_value * (1 + perturbation_scale)
        response_pos = evaluate(seed)
        
        # Shake negative
        seed.parameters[param_name] = param_value * (1 - perturbation_scale)
        response_neg = evaluate(seed)
        
        # Reset
        seed.parameters[param_name] = param_value
        baseline = evaluate(seed)
        
        # The delta IS the information
        sensitivity = abs(response_pos.score - response_neg.score)
        
        results[param_name] = {
            'sensitivity': sensitivity,
            'directional': response_pos.score - response_neg.score,
            'asymmetric': abs((response_pos.score - baseline) - (baseline - response_neg.score)),
            'connected_to': infer_connections(response_pos, response_neg, baseline),
        }
    
    # Sort by sensitivity — the load-bearing parameters first
    ranked = sorted(results.items(), key=lambda x: -x[1]['sensitivity'])
    
    return ranked
```

### Step 2: Tire In the Strong Points (Stabilize What Matters)

On a boat, when you find a stay that's taking load, you tire it in — add turns, make it secure. You don't make everything equally tight. You make the load-bearing lines tight and leave the rest.

For SMPagents: when you find a parameter that's highly sensitive (load-bearing), you **constrain it tightly**. When you find a parameter that's insensitive (slack), you can leave it loose or even remove it.

```python
def tire_in_strong_points(seed, sensitivity_results):
    """
    Tighten constraints on sensitive parameters. 
    Loosen constraints on insensitive parameters.
    Like tying in strong points on a boat.
    """
    for param_name, result in sensitivity_results:
        if result['sensitivity'] > threshold_high:
            # Load-bearing parameter — constrain tightly
            seed.constraints[param_name] = TightConstraint(
                margin=result['sensitivity'] * 0.1,  # small margin = tight
                snap=True,  # snap to nearest valid value
            )
        elif result['sensitivity'] < threshold_low:
            # Slack parameter — can be left loose or removed
            seed.constraints[param_name] = LooseConstraint(
                margin=result['sensitivity'] * 10.0,  # large margin = loose
                snap=False,
            )
    
    return seed
```

### Step 3: Balance Forces (Coupled Parameters)

On a boat, you don't just tighten one side. If you crank the forestay, you need to check the backstay, because they're coupled. The rig is a system — tightening one line changes the load on others.

For SMPagents: when you constrain one parameter, you change the sensitivity landscape of others. The shake protocol is iterative:

```
Round 1: shake all parameters → find the 5 most sensitive
Round 2: constrain those 5 → shake the remaining → find new sensitivities
Round 3: constrain those → shake again → find deeper couplings
...
Converge: no new sensitive parameters discovered
```

Each round is like going around the boat, tightening one set of stays, then checking if the others need adjustment. The system reaches a balanced state where every stay is appropriately tensioned.

### Step 4: Extra Stays for Rough Weather (Redundancy)

On a boat heading into a storm, you add extra stays — backup lines that take load if a primary stay fails. You don't need them in calm weather. But in rough weather, redundancy saves the rig.

For SMPagents: add **backup constraints** for critical parameters. Not tighter constraints — **alternative** constraints that activate if the primary fails:

```python
def add_extra_stays(seed, critical_params):
    """
    Add redundant constraints for critical parameters.
    Like adding extra stays before rough weather.
    """
    for param_name in critical_params:
        primary = seed.constraints[param_name]
        
        # Backup constraint — different approach, same goal
        seed.backup_constraints[param_name] = AlternativeConstraint(
            method='eisenstein_snap' if primary.method != 'eisenstein_snap' else 'hard_clamp',
            margin=primary.margin * 2.0,  # looser than primary
            activates_when=primary.violated,
        )
        
        # Parity check — detect if primary and backup disagree
        seed.parity_checks[param_name] = ParityCheck(
            reference=primary,
            candidate=seed.backup_constraints[param_name],
            tolerance=primary.margin * 0.5,
        )
```

## Stochastic Computing as Rigging Shake

The connection to stochastic computing is precise:

**Stochastic computing**: represent values as random bit streams. The randomness IS the computation. You learn about the value by observing many random samples.

**Rigging shake**: represent system structure as perturbation responses. The perturbation IS the inspection. You learn about the system by observing many perturbation responses.

Both replace **direct measurement** with **statistical inference from noise**. Both trade precision for speed. Both get better with more samples. Both reveal structure that direct inspection would miss.

### The Mathematics

Stochastic computing converges as O(1/√n) — quadruple the samples, halve the error.

Rigging shaking converges similarly:
- 1 shake per parameter → rough map (which parameters matter at all)
- 5 shakes per parameter → sensitivity ranking (which matter most)
- 20 shakes per parameter → coupling map (which parameters affect each other)
- 100 shakes per parameter → full Jacobian (local gradient of the system)

The musician doesn't need the full Jacobian. They need the sensitivity ranking — which knobs matter, and which direction to twist them. That's 5 shakes per parameter. Fast.

### The Deep Connection

Stochastic computing, rigging shaking, knob twisting, and the feedback loop are the SAME thing at different scales:

```
Stochastic computing:  bit-level randomness → statistical inference
Rigging shaking:       parameter perturbation → structural discovery  
Knob twisting:         continuous adjustment → convergence
Feedback loop:         perceive → compare → perturb → repeat
```

All four are: **perturb the system, observe the delta, infer structure from the response.**

The stochastic part isn't a bug. It's the sensor. The randomness IS how you probe the system without knowing what to look for.

## What This Means for Our Stack

### The Insight Engine Should Shake, Not Just Sweep

Our `insight-engine` does parameter sweeps — systematic exploration of the constraint manifold. That's like climbing the mast and inspecting every line. Thorough but slow.

Adding a stochastic mode — shake mode — would be faster and reveal different things:

```rust
fn shake_discovery(agent: &mut Agent) -> Vec<Discovery> {
    let mut discoveries = Vec::new();
    
    // Random perturbation schedule
    for _ in 0..100 {
        // Pick a random parameter
        let param = agent.parameters.random();
        
        // Random perturbation magnitude (1% to 50%)
        let scale = 0.01 + random() * 0.49;
        
        // Shake it
        let baseline = agent.evaluate();
        agent.parameters[param] *= 1.0 + scale;
        let response_pos = agent.evaluate();
        agent.parameters[param] /= (1.0 + scale);
        
        // Listen to the delta
        let delta = response_pos.score - baseline.score;
        
        if delta.abs() > SENSITIVITY_THRESHOLD {
            discoveries.push(Discovery {
                parameter: param,
                sensitivity: delta.abs(),
                direction: delta.signum(),
                coupled_params: find_couplings(agent, param),
            });
        }
    }
    
    discoveries
}
```

### Constraint DNA Should Include Sensitivity Maps

Our constraint DNA profiles should store not just the constraint values, but the **sensitivity map** — which parameters are load-bearing and which are slack. This is the rigging chart for each agent:

```json
{
  "constraint_dna": {
    "profile": "robot-arm-6dof",
    "constraints": { ... },
    "sensitivity_map": {
      "joint_3_angle": {"sensitivity": 0.89, "coupled_to": ["joint_2_angle", "joint_4_angle"]},
      "joint_1_angle": {"sensitivity": 0.12, "coupled_to": []},
      "velocity_limit": {"sensitivity": 0.67, "coupled_to": ["acceleration_limit"]},
    },
    "extra_stays": {
      "joint_3_angle": {"method": "eisenstein_snap", "activates_when": "primary_violated"}
    }
  }
}
```

A new agent loading this DNA immediately knows: "joint 3 is the load-bearing parameter. Joint 1 doesn't matter much. If joint 3's primary constraint fails, snap to the Eisenstein nearest point."

### Fleet-Wide Rigging Check

Before a rough-weather deployment (high-stakes mission), the fleet should do a rigging check:

1. Every agent shakes its own parameters
2. Every agent reports its sensitivity map
3. The fleet identifies shared sensitivities (which parameters matter across all agents)
4. Extra stays are added for shared critical parameters
5. The fleet enters rough-weather mode with balanced, redundant constraints

This is literally what sailors do before a storm. Every boat in the fleet checks its rigging, shares observations about weather conditions, and adds extra security based on the collective intelligence.

## The Musician, The Sailor, The Grandmother, The Agent

```
The musician shakes the sound by twisting knobs, finds which frequencies matter.
The sailor shakes the rigging by pulling lines, finds which stays are load-bearing.
The grandmother shakes the recipe by adding pinches, finds which ingredients carry the dish.
The agent shakes its parameters by random perturbation, finds which dimensions are the backbone.

All four discover the system by perturbing it.
All four listen to the delta.
All four converge on understanding through oscillation.
All four know that the response IS the map.
```

You don't need to model the system to understand it. You need to perturb it and listen. The system models itself through its responses. The stochastic noise is not uncertainty — it's the probe. The shake is not violence — it's inquiry.

Shake the rigging. Listen to what pulls back. Tire in the strong points. Balance the forces. Add extra stays for rough weather. That's how you sail into a storm. That's how you build an agent that survives the unknown.

The tip of the iceberg is the knob. Below the waterline: stochastic discovery, sensitivity mapping, coupling detection, redundant constraint injection. The musician hears the tip. The system knows the whole iceberg.
