# clock-sync-probe

Test your network's clock synchronization capability in 30 seconds.

## What it does

Clock sync is the foundation of distributed systems. If your clocks can't agree, your distributed locks, event ordering, and consensus protocols are built on sand. This tool tells you how good your sync can get, and which algorithm to use.

It simulates a fleet of peers, measures offset, jitter, and convergence time, and ranks four sync strategies against each other.

## Install

```bash
pip install clock-sync-probe
```

Or from source:

```bash
cd clock-sync-probe
pip install -e .
```

## Usage

### Quick test (30 seconds)

```bash
clock-sync-probe test --duration 30
```

This simulates a 2-peer fleet and compares all four strategies.

### Test with specific peers

```bash
clock-sync-probe test --peers node1:19840,node2:19841,node3:19842 --duration 30
```

### Benchmark strategies

```bash
clock-sync-probe benchmark --strategies naive,cristian,ptp --ticks 1000
```

Runs 1000 simulation ticks and compares only the strategies you care about.

### Generate report from saved results

```bash
clock-sync-probe test --json-out results.json
clock-sync-probe report --input results.json
```

## The four strategies

| Strategy | How it works | Best for |
|---|---|---|
| **Naive** | Average all peer offsets, equal weight | Baseline comparison |
| **Cristian** | Use lowest-RTT peer for estimate | Low-jitter networks |
| **PTP** | Best-master selection + PI controller | Production precision timing |
| **Exponential** | Aggressive early correction, decayed over time | Fast convergence needs |

## Output

For each strategy you get:

- **Residual offset** — how far off you are after sync
- **Jitter** — variance in the offset (your uncertainty)
- **δ (delta)** — recommended uncertainty bound (3σ of jitter)
- **Convergence ticks** — how many rounds until stable

The tool ranks all strategies and recommends the best one for your network conditions.

## Why this matters

If you're building anything distributed — distributed locks, event sourcing, consensus — clock sync quality determines your correctness ceiling. This tool gives you the numbers in 30 seconds instead of finding out in production.

## License

MIT
