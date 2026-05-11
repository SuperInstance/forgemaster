# Snap-as-Attention: Simulation Suite

**Testing the hypothesis that snap functions (tolerance-based compression) are the fundamental mechanism of attention.**

Five simulators explore different aspects of snap-based attention — from poker to Rubik's cubes to cross-domain transfer.

## Quick Start

```bash
# Run individual simulators with defaults
python poker_sim.py
python learning_cycle_sim.py
python attention_budget_sim.py
python rubik_sim.py
python transfer_sim.py

# Run all at once
python run_all.py

# Quick test mode (fast, reduced counts)
python poker_sim.py --quick
python run_all.py --quick

# With progress bars
python poker_sim.py --hands 50000 --verbose
python learning_cycle_sim.py --experiences 200000 --verbose
```

## CLI Usage

Every simulator accepts the same set of flags:

| Flag | Description |
|------|-------------|
| `--quick` | Fast mode with reduced counts for testing |
| `--verbose`, `-v` | Show progress bar during execution |
| `--csv FILE` | Export results to CSV |
| `--html FILE` | Generate a self-contained HTML report |
| `--json-out FILE` | JSON output file (default: `results_*.json`) |

### Simulator-specific flags

| Simulator | Flag | Default | Description |
|-----------|------|---------|-------------|
| `poker_sim.py` | `--hands N` | 10000 | Number of poker hands |
| `learning_cycle_sim.py` | `--experiences N` | 100000 | Learning experiences |
| `attention_budget_sim.py` | `--timesteps N` | 100000 | Simulation timesteps |
| `rubik_sim.py` | `--solves N` | 500 | Cube solves per solver |
| `transfer_sim.py` | `--trials N` | 50000 | Transfer trials |

### Examples

```bash
# Big poker run with all exports
python poker_sim.py --hands 100000 --verbose --csv poker.csv --html poker_report.html

# Quick learning cycle test
python learning_cycle_sim.py --quick --verbose

# Full suite with HTML reports
python run_all.py --html --verbose

# Just CSV exports
python run_all.py --quick --csv
```

## The Five Simulators

### 1. 🎰 Poker Attention Engine (`poker_sim.py`)

**Tests:** Whether well-calibrated snap functions improve decision-making.

Four poker players with different snap tolerance profiles:
- **Novice:** Tight on cards (notices every card shift), loose on behavior (misses tells)
- **Intermediate:** Uniform tolerances across all layers
- **Expert:** Loose on cards (ignores noise), tight on behavior+emotion (catches tells)
- **Baseline:** No snap filtering — everything gets attention

**Key insight:** Expert wins because it attends to the RIGHT deltas (behavior, emotion) not the wrong ones (card probability noise).

**Output includes:** Win rates, deltas per hand, attention efficiency, layer breakdown.

```
╔═══════════════════════════════════════════════════════╗
║  🎰 POKER ATTENTION ENGINE RESULTS                  ║
╠═══════════════════════════════════════════════════════╣
║  10,000 hands played                                 ║
║  Player       Win%    Δ/H   Efficiency  Distribution ║
║  novice       37.7%   2.8      13.3     █░░░░░░░░░░ ║
║  intermediate 25.9%   4.6       5.6     ████░░░░░░░ ║
║  expert       19.6%   7.0       2.8     ██████░░░░░ ║
║  baseline     16.8%  11.4       1.5     █████████░░ ║
╚═══════════════════════════════════════════════════════╝
```

### 2. 🧠 Delta-to-Script Learning Cycle (`learning_cycle_sim.py`)

**Tests:** How snap functions enable learning automation through phase transitions.

An agent starts with no knowledge, encounters situations, and builds "scripts" (automated responses) from repeated patterns. Shows three phases:

1. **Delta Flood:** No scripts exist → everything is novel → high cognitive load
2. **Script Burst:** Repeated patterns get encoded → rapid script creation
3. **Smooth Running:** Most situations snap to scripts → low cognitive load

**Key insight:** The snap function automates what was once novel, freeing cognition for truly new situations.

**Output includes:** Epoch-by-epoch performance, cognitive load, script hit rate, phase transitions, ASCII charts.

### 3. 📡 Multi-Flavor Attention Budget (`attention_budget_sim.py`)

**Tests:** Whether actionability-weighted attention beats reactive or uniform allocation.

An agent monitors 10 information streams with different randomness flavors (coin, d6, d20, gaussian, spike, etc.) but can only attend to 3 at a time. Three strategies compete:

- **Uniform:** Equal attention to all streams with deltas
- **Reactive:** Attend to biggest deltas regardless of stream
- **Smart:** Weight deltas by actionability (how much thinking changes outcomes)

**Key insight:** Smart strategy wins because it directs attention to deltas where thinking matters (spike/burst streams), not just where deltas are large (coin/noise streams).

### 4. 🧊 Rubik's Cube Script Engine (`rubik_sim.py`)

**Tests:** Whether scripts reduce cognitive load even when they don't reduce total moves.

Three solvers tackle scrambled cubes:
- **Brute Force:** Random moves, no memory — every move is a decision
- **Script Executor:** Has known move sequences, snaps to nearest match
- **Planning Solver:** Scripts + evaluates which script to chain next

**Key insight:** Scripts don't reduce MOVES, they reduce COGNITIVE LOAD. The planning solver may use more total moves but THINKS less because scripts execute automatically.

### 5. 🔄 Cross-Domain Transfer (`transfer_sim.py`)

**Tests:** Whether snap calibrations transfer across domains with matching randomness shapes.

Snap functions calibrated on one randomness flavor (e.g., d6) are tested on another (e.g., d20). Shape groups:

- **Binary:** coin
- **Uniform:** d6, d20
- **Bell:** 2d6, gaussian
- **Categorical:** categorical, directional

**Key insight:** Matching shapes (d6→d20) transfer better than mismatching (coin→gaussian), supporting the theory that snap topologies are domain-invariant.

## Output Formats

All simulators produce:
1. **Rich terminal output** — box-drawn tables, ASCII bar charts, interpretation text
2. **JSON file** — machine-readable results (always)
3. **CSV file** — with `--csv` flag
4. **HTML report** — with `--html` flag (self-contained, dark theme)

## Interpreting Results

Each simulator prints an **INTERPRETATION** section explaining:
- What the numbers mean in plain English
- Whether the theory's predictions were confirmed
- What's surprising or interesting
- Caveats and limitations

## Dependencies

- Python 3.7+
- No external dependencies (stdlib only)
- `numpy` available but not required

## File Structure

```
snap-attention/
├── poker_sim.py              # 🎰 Poker attention engine
├── learning_cycle_sim.py     # 🧠 Learning phase transitions
├── attention_budget_sim.py   # 📡 Budget allocation strategies
├── rubik_sim.py              # 🧊 Cube script engine
├── transfer_sim.py           # 🔄 Cross-domain transfer
├── run_all.py                # Run all simulators
├── README.md                 # This file
├── results_*.json            # JSON output files
├── results_*.csv             # CSV exports (--csv flag)
└── report_*.html             # HTML reports (--html flag)
```
