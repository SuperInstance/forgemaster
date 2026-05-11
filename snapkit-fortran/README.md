# SnapKit Fortran ⚒️ — Tolerance-Compressed Attention Allocation

**Everything within tolerance is compressed away. Only the deltas survive.**

SnapKit Fortran is a modern Fortran 2008 implementation of **Snaps as Attention** theory — a mathematical framework for allocating finite cognitive resources using tolerance-compressed snap functions over ADE-classified lattices.

## Features

- **SnapFunction** — Tolerance gatekeeper with configurable topology
- **DeltaDetector** — Multi-stream delta monitoring with prioritization
- **AttentionBudget** — Finite cognition allocation (actionability, reactive, uniform)
- **ScriptLibrary** — Pattern matching for automated responses
- **LearningCycle** — Full expertise lifecycle
- **Eisenstein Lattice** — A₂ hexagonal snap
- **SnapTopology** — ADE classification (A₁, A₂, D₄, E₆, E₇, E₈)

## Build

### Requirements
- Fortran 2008 compiler (gfortran ≥ 9, ifx, nvfortran)
- fpm (Fortran Package Manager) — recommended

### Using fpm

```bash
fpm build
fpm test
fpm run --example demo_poker
fpm run --example demo_learning
```

### Using make

```bash
make         # Build library and demo programs
make test    # Build and run tests
make clean   # Remove build artifacts
```

## Quick Start

```fortran
program quickstart
    use snapkit
    implicit none

    type(SnapFunction) :: snap
    type(SnapResult) :: result

    ! Create a snap with hexagonal topology
    snap = SnapFunction(tolerance=0.1_dp, topology=SNAP_TOPOLOGY_HEXAGONAL)

    ! Within tolerance — compressed
    result = snap%snap(0.05_dp)
    print *, "Within tolerance:", result%within_tolerance
    print *, "Delta:", result%delta

    ! Exceeds tolerance — delta
    result = snap%snap(0.3_dp)
    print *, "Within tolerance:", result%within_tolerance
    print *, "Delta:", result%delta
end program quickstart
```

### Full Pipeline

```fortran
program pipeline_demo
    use snapkit
    use snapkit_delta
    use snapkit_attention
    implicit none

    type(SnapFunction) :: snap
    type(DeltaDetector) :: detector
    type(AttentionBudget) :: budget
    type(Delta) :: deltas(10)
    type(AttentionAllocation) :: allocations(10)
    integer :: n_deltas, n_alloc

    ! 1. Configure snap
    snap = SnapFunction(tolerance=0.1_dp)

    ! 2. Set up detector
    detector = DeltaDetector()
    call detector%add_stream(snap, "market_data")

    ! 3. Create budget
    budget = AttentionBudget(total_budget=100.0_dp, strategy="actionability")

    ! 4. Observe and allocate
    call detector%observe("market_data", 0.27_dp, deltas, n_deltas)
    call budget%allocate(deltas(1:n_deltas), allocations, n_alloc)

    print *, "Allocations:", n_alloc
end program pipeline_demo
```

## Module Reference

| Module | Description |
|--------|-------------|
| `snapkit` | Core snap function types and procedures |
| `snapkit_delta` | Multi-stream delta detection |
| `snapkit_attention` | Attention budget allocation |
| `snapkit_scripts` | Script library for pattern matching |
| `snapkit_learning` | Learning cycle (DeltaFlood → Rebuilding) |
| `snapkit_topology` | ADE topology classification |
| `snapkit_eisenstein` | A₂ Eisenstein lattice snap |
| `snapkit_visualization` | Terminal visualization utilities |

## Examples

```bash
# Poker attention engine
fpm run --example demo_poker

# Learning cycle simulation
fpm run --example demo_learning

# Performance benchmarks
fpm run --example benchmark
```

## Topology Types

| Enum Member | Name | Root System | ADE |
|-------------|------|-------------|-----|
| `SNAP_TOPOLOGY_BINARY` | Binary | A₁ | ✓ |
| `SNAP_TOPOLOGY_HEXAGONAL` | Hexagonal | A₂ | ✓ |
| `SNAP_TOPOLOGY_OCTAHEDRAL` | Octahedral | A₃ | ✓ |
| `SNAP_TOPOLOGY_CUBIC` | Cubic | A₁³ | — |
| `SNAP_TOPOLOGY_TRIALITY` | Triality | D₄ | ✓ |
| `SNAP_TOPOLOGY_EXCEPTIONAL_E6` | Exceptional E₆ | E₆ | ✓ |
| `SNAP_TOPOLOGY_EXCEPTIONAL_E7` | Exceptional E₇ | E₇ | ✓ |
| `SNAP_TOPOLOGY_EXCEPTIONAL_E8` | Exceptional E₈ | E₈ | ✓ |

## License

MIT — use freely, give credit.

---

*Built for the Cocapn fleet. Fortran 2008 — because scientific computing deserves attention allocation too.*

*"The snap is the gatekeeper of attention. The delta is the compass. The lattice is the infrastructure. Attention is the thirst."*
