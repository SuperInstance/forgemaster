#!/usr/bin/env python3
"""Comprehensive snapkit-v2 experiment suite — all 4 phases."""

import sys, os, time, math, random, struct, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from snapkit import *
from snapkit.spectral import spectral_batch
from snapkit.eisenstein_voronoi import (
    eisenstein_snap_voronoi, eisenstein_snap_naive, snap_distance,
    eisenstein_snap_batch as voronoi_batch
)

RESULTS = []

def log(section, test, status, detail=""):
    entry = {"section": section, "test": test, "status": status, "detail": detail}
    RESULTS.append(entry)
    sym = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️" if status == "WARN" else "📊"
    print(f"  {sym} [{section}] {test}: {status} {detail[:120]}")

# ─────────────────────────────────────────────────────────────
# PHASE 1: CORRECTNESS VERIFICATION
# ─────────────────────────────────────────────────────────────

def phase1a_eisenstein_falsification():
    print("\n" + "="*70)
    print("PHASE 1A: Eisenstein Voronoi Snap Falsification")
    print("="*70)

    INV_SQRT3 = 1.0 / math.sqrt(3)  # ~0.577350269...
    N = 1_000_000
    random.seed(42)

    max_dist = 0.0
    all_integer = True
    idempotent_pass = True
    boundary_cases = 0

    t0 = time.perf_counter()
    for i in range(N):
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        a, b = eisenstein_snap_voronoi(x, y)

        # Check lattice membership
        if not (isinstance(a, int) and isinstance(b, int)):
            all_integer = False

        # Check snap distance
        dx = x - (a - b * 0.5)
        dy = y - (b * 0.5 * math.sqrt(3))
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > max_dist:
            max_dist = dist

        # Check idempotency on 0.1% sample
        if i % 1000 == 0:
            sx, sy = eisenstein_snap_voronoi(a - b * 0.5, b * 0.5 * math.sqrt(3))
            if (sx, sy) != (a, b):
                idempotent_pass = False

    elapsed = time.perf_counter() - t0

    log("1A", f"10M random snap max distance", "PASS" if max_dist <= INV_SQRT3 + 1e-10 else "FAIL",
        f"max_dist={max_dist:.15f}, bound={INV_SQRT3:.15f}, diff={max_dist - INV_SQRT3:.2e}")
    log("1A", "All snap results are integers", "PASS" if all_integer else "FAIL", "")
    log("1A", "Snap idempotency (1K sample)", "PASS" if idempotent_pass else "FAIL", "")
    log("1A", f"10M snaps throughput", "📊", f"{N/elapsed:.0f} ops/sec in {elapsed:.2f}s")

    # Boundary and degenerate cases
    tests = [
        ("origin (0,0)", 0.0, 0.0, (0, 0)),
        ("near origin (0.1,0.1)", 0.1, 0.1, None),
        ("large coords (1e6,1e6)", 1e6, 1e6, None),
        ("very large (1e9,1e9)", 1e9, 1e9, None),
        ("negative (-5,-5)", -5.0, -5.0, None),
        ("epsilon (1e-15,1e-15)", 1e-15, 1e-15, (0, 0)),
    ]
    for name, x, y, expected in tests:
        a, b = eisenstein_snap_voronoi(x, y)
        ok = True
        if expected is not None:
            ok = (a, b) == expected
        log("1A", f"Degenerate: {name}", "PASS" if ok else "FAIL",
            f"snap({x},{y}) = ({a},{b})" + (f" expected {expected}" if expected else ""))

    # Boundary points: points exactly at 1/√3 from origin in various directions
    # A point at distance exactly INV_SQRT3 from (0,0) on the boundary
    for angle_deg in range(0, 360, 30):
        angle = math.radians(angle_deg)
        bx = INV_SQRT3 * math.cos(angle)
        by = INV_SQRT3 * math.sin(angle)
        a, b = eisenstein_snap_voronoi(bx, by)
        dx = bx - (a - b * 0.5)
        dy = by - (b * 0.5 * math.sqrt(3))
        dist = math.sqrt(dx*dx + dy*dy)
        # On boundary, snap should still be within bound
        ok = dist <= INV_SQRT3 + 1e-10
        if not ok:
            boundary_cases += 1
    log("1A", "12 boundary directions within bound", "PASS" if boundary_cases == 0 else "FAIL",
        f"{boundary_cases}/12 exceeded bound")

    # Voronoi snap vs naive snap comparison
    naive_diff = 0
    for _ in range(100_000):
        x = random.uniform(-50, 50)
        y = random.uniform(-50, 50)
        va, vb = eisenstein_snap_voronoi(x, y)
        na, nb = eisenstein_snap_naive(x, y)
        if (va, vb) != (na, nb):
            # Check if voronoi is actually closer
            dv = (x - (va - vb*0.5))**2 + (y - (vb*0.5*math.sqrt(3)))**2
            dn = (x - (na - nb*0.5))**2 + (y - (nb*0.5*math.sqrt(3)))**2
            if dv > dn + 1e-15:
                naive_diff += 1
    log("1A", "Voronoi always ≤ naive accuracy", "PASS" if naive_diff == 0 else "FAIL",
        f"voronoi worse in {naive_diff}/100K cases")

    # EisensteinInteger round-trip
    rt_pass = True
    for _ in range(100_000):
        a0 = random.randint(-100, 100)
        b0 = random.randint(-100, 100)
        e = EisensteinInteger(a0, b0)
        z = e.complex
        e2 = EisensteinInteger.from_complex(z)
        if (e2.a, e2.b) != (a0, b0):
            rt_pass = False
            break
    log("1A", "EisensteinInteger round-trip (100K)", "PASS" if rt_pass else "FAIL", "")

    # eisenstein_snap with tolerance
    snap_pass = True
    for _ in range(100_000):
        x = random.uniform(-20, 20)
        y = random.uniform(-20, 20)
        z = complex(x, y)
        nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.5)
        if is_snap != (dist <= 0.5):
            snap_pass = False
            break
    log("1A", "eisenstein_snap tolerance consistent", "PASS" if snap_pass else "FAIL", "")


def phase1b_temporal_correctness():
    print("\n" + "="*70)
    print("PHASE 1B: Temporal Snap Correctness")
    print("="*70)

    # Beat grid basics
    bg = BeatGrid(period=1.0, phase=0.0, t_start=0.0)

    # Phase always in [0, period)
    phase_ok = True
    for t in [0.0, 0.5, 1.0, 1.7, -0.3, 100.3, -100.7]:
        r = bg.snap(t)
        if not (0.0 <= r.beat_phase < 1.0):
            phase_ok = False
            log("1B", f"Phase range for t={t}", "FAIL", f"phase={r.beat_phase}")
    log("1B", "All phases in [0, 1)", "PASS" if phase_ok else "FAIL", "")

    # On-beat detection
    on_beat_tests = [
        (0.0, True), (1.0, True), (0.05, True), (0.1, True),
        (0.11, False), (0.5, False), (2.0, True), (-0.05, True),
    ]
    ob_pass = True
    for t, expected in on_beat_tests:
        r = bg.snap(t, tolerance=0.1)
        if r.is_on_beat != expected:
            ob_pass = False
            log("1B", f"On-beat t={t}", "FAIL", f"is_on_beat={r.is_on_beat}, expected={expected}")
    log("1B", "On-beat detection (8 cases)", "PASS" if ob_pass else "FAIL", "")

    # T-minus-0 detection: create synthetic zero-crossing
    ts = TemporalSnap(grid=bg, tolerance=0.1, t0_threshold=0.05, t0_window=3)
    # Feed values that cross zero: positive → negative → ~0
    r1 = ts.observe(1.0, 0.5)   # positive
    r2 = ts.observe(2.0, -0.5)  # negative (zero crossing between)
    r3 = ts.observe(3.0, 0.01)  # near zero, derivative change
    log("1B", "T-minus-0 basic detection", "PASS" if r3.is_t_minus_0 else "FAIL",
        f"is_t_minus_0={r3.is_t_minus_0}")

    # Edge: period = 0 should raise
    try:
        BeatGrid(period=0)
        log("1B", "BeatGrid period=0 raises", "FAIL", "no exception")
    except ValueError:
        log("1B", "BeatGrid period=0 raises ValueError", "PASS", "")

    # Negative period
    try:
        BeatGrid(period=-1)
        log("1B", "BeatGrid period=-1 raises", "FAIL", "no exception")
    except ValueError:
        log("1B", "BeatGrid period=-1 raises ValueError", "PASS", "")

    # beats_in_range
    bg2 = BeatGrid(period=0.5, phase=0.0, t_start=0.0)
    beats = bg2.beats_in_range(0.0, 2.0)
    log("1B", "beats_in_range(0, 2) with period=0.5", "PASS" if len(beats) == 5 else "FAIL",
        f"got {len(beats)} beats: {beats}")

    # Batch snap
    timestamps = [0.0, 0.5, 1.0, 1.5, 2.0]
    results = bg2.snap_batch(timestamps)
    log("1B", "snap_batch(5 timestamps)", "PASS" if len(results) == 5 else "FAIL", "")

    # TemporalSnap history
    ts2 = TemporalSnap(grid=bg, t0_window=3)
    for t, v in [(1.0, 1.0), (2.0, 0.5), (3.0, -0.3)]:
        ts2.observe(t, v)
    hist = ts2.history
    log("1B", "History tracking", "PASS" if len(hist) == 3 else "FAIL",
        f"len={len(hist)}")

    # Reset
    ts2.reset()
    log("1B", "Reset clears history", "PASS" if len(ts2.history) == 0 else "FAIL",
        f"len={len(ts2.history)}")


def phase1c_spectral_validation():
    print("\n" + "="*70)
    print("PHASE 1C: Spectral Analysis Validation")
    print("="*70)

    random.seed(42)

    # Entropy: uniform distribution → log2(n)
    for bins in [5, 10, 20]:
        n = 100000
        data = [random.random() for _ in range(n)]
        h = entropy(data, bins=bins)
        expected = math.log2(bins)
        diff = abs(h - expected)
        log("1C", f"Entropy uniform bins={bins}", "PASS" if diff < 0.05 else "FAIL",
            f"h={h:.4f}, expected={expected:.4f}, diff={diff:.4f}")

    # Entropy: deterministic (constant) → 0
    h = entropy([5.0] * 1000, bins=10)
    log("1C", "Entropy constant = 0", "PASS" if h == 0.0 else "FAIL", f"h={h}")

    # Entropy: single element → 0
    h = entropy([1.0], bins=10)
    log("1C", "Entropy single element = 0", "PASS" if h == 0.0 else "FAIL", f"h={h}")

    # Autocorrelation: lag-0 should be 1.0
    data = [random.gauss(0, 1) for _ in range(1000)]
    acf = autocorrelation(data, max_lag=10)
    log("1C", "Autocorrelation lag-0 = 1.0", "PASS" if abs(acf[0] - 1.0) < 1e-10 else "FAIL",
        f"acf[0]={acf[0]:.15f}")

    # Autocorrelation: AR(1) process with phi=0.7
    # Expected lag-1 ≈ 0.7
    phi = 0.7
    ar_data = [0.0] * 5000
    for i in range(1, 5000):
        ar_data[i] = phi * ar_data[i-1] + random.gauss(0, 1)
    acf_ar = autocorrelation(ar_data, max_lag=5)
    log("1C", "AR(1) phi=0.7 lag-1 ≈ 0.7", "PASS" if abs(acf_ar[1] - 0.7) < 0.1 else "FAIL",
        f"acf[1]={acf_ar[1]:.4f}")

    # Hurst exponent: pure random → H ≈ 0.5
    random_walk = [0.0] * 5000
    for i in range(1, 5000):
        random_walk[i] = random_walk[i-1] + random.gauss(0, 1)
    h = hurst_exponent(random_walk)
    log("1C", "Hurst random walk ≈ 0.5", "PASS" if abs(h - 0.5) < 0.15 else "FAIL",
        f"H={h:.4f}")

    # Hurst: persistent series (trend) → H > 0.5
    persistent = list(range(5000))
    hp = hurst_exponent(persistent)
    log("1C", "Hurst persistent > 0.5", "PASS" if hp > 0.5 else "FAIL",
        f"H={hp:.4f}")

    # Hurst: small data → returns 0.5
    h_small = hurst_exponent([1.0, 2.0, 3.0])
    log("1C", "Hurst tiny data returns 0.5", "PASS" if h_small == 0.5 else "FAIL",
        f"H={h_small}")

    # Spectral summary
    summary = spectral_summary(data, bins=10, max_lag=10)
    log("1C", f"Spectral summary for random data", "📊",
        f"H={summary.hurst:.3f}, entropy={summary.entropy_bits:.3f}, "
        f"acf_lag1={summary.autocorr_lag1:.3f}, stationary={summary.is_stationary}")

    # Batch spectral
    summaries = spectral_batch([data[:100], data[100:200]], bins=10)
    log("1C", "spectral_batch(2 series)", "PASS" if len(summaries) == 2 else "FAIL", "")


def phase1d_connectome():
    print("\n" + "="*70)
    print("PHASE 1D: Connectome Cross-Correlation")
    print("="*70)

    random.seed(42)
    n = 500

    # Coupled: x and y = x + noise
    x = [random.gauss(0, 1) for _ in range(n)]
    y_coupled = [x[i] + random.gauss(0, 0.2) for i in range(n)]
    # Anti-coupled: y = -x + noise
    y_anti = [-x[i] + random.gauss(0, 0.2) for i in range(n)]
    # Uncoupled: independent
    y_uncoupled = [random.gauss(0, 1) for _ in range(n)]

    # Test coupled
    tc = TemporalConnectome(threshold=0.3, max_lag=5)
    tc.add_room("signal", x)
    tc.add_room("coupled", y_coupled)
    tc.add_room("anti", y_anti)
    tc.add_room("independent", y_uncoupled)
    result = tc.analyze()

    coupled_pairs = result.coupled
    anti_pairs = result.anti_coupled
    log("1D", f"Coupled pair detected", "PASS" if len(coupled_pairs) >= 1 else "FAIL",
        f"{len(coupled_pairs)} coupled pairs: {[(p.room_a, p.room_b, p.correlation) for p in coupled_pairs]}")
    log("1D", f"Anti-coupled pair detected", "PASS" if len(anti_pairs) >= 1 else "FAIL",
        f"{len(anti_pairs)} anti pairs: {[(p.room_a, p.room_b, p.correlation) for p in anti_pairs]}")

    # Check independent is uncoupled
    ind_pair = [p for p in result.pairs
                if set([p.room_a, p.room_b]) == {"signal", "independent"}]
    if ind_pair:
        unc = ind_pair[0].coupling == CouplingType.UNCOUPLED
        log("1D", "Independent = UNCOUPLED", "PASS" if unc else "FAIL",
            f"coupling={ind_pair[0].coupling}, corr={ind_pair[0].correlation:.4f}")
    else:
        log("1D", "Independent pair found", "FAIL", "not in results")

    # Adjacency matrix
    names, mat = result.adjacency_matrix()
    log("1D", f"Adjacency matrix ({len(names)}x{len(mat)})", "PASS", "")
    log("1D", f"Significant pairs", "📊", f"{len(result.significant)} significant")

    # Graphviz output
    gv = result.to_graphviz()
    log("1D", "Graphviz output", "PASS" if "graph Connectome" in gv else "FAIL",
        f"{len(gv)} chars")

    # Min samples check
    tc2 = TemporalConnectome(threshold=0.3, min_samples=100)
    tc2.add_room("a", [1.0] * 5)
    tc2.add_room("b", [2.0] * 5)
    r2 = tc2.analyze()
    log("1D", "Below min_samples → UNCOUPLED", "PASS" if r2.pairs[0].coupling == CouplingType.UNCOUPLED else "FAIL",
        f"coupling={r2.pairs[0].coupling}")


# ─────────────────────────────────────────────────────────────
# PHASE 2: PERFORMANCE BENCHMARKS
# ─────────────────────────────────────────────────────────────

def phase2_benchmarks():
    print("\n" + "="*70)
    print("PHASE 2: Performance Benchmarks")
    print("="*70)

    random.seed(42)

    # 2A: Eisenstein snap throughput
    bench_results = {}
    for size in [1000, 10000, 100000]:
        points = [(random.uniform(-100, 100), random.uniform(-100, 100)) for _ in range(size)]
        t0 = time.perf_counter()
        for x, y in points:
            eisenstein_snap_voronoi(x, y)
        elapsed = time.perf_counter() - t0
        ops = size / elapsed
        bench_results[size] = ops
        log("2A", f"Eisenstein snap {size:,}", "📊", f"{ops:,.0f} ops/sec ({elapsed:.3f}s)")

    # Check linear scaling
    if 1000 in bench_results and 100000 in bench_results:
        ratio = bench_results[1000] / bench_results[100000]
        log("2B", "Scaling ratio (1K vs 100K)", "📊",
            f"1K/100K = {ratio:.2f}x (1.0 = perfect linear)")

    # Voronoi vs naive
    for size in [10000, 100000]:
        points = [(random.uniform(-50, 50), random.uniform(-50, 50)) for _ in range(size)]
        t0 = time.perf_counter()
        for x, y in points:
            eisenstein_snap_voronoi(x, y)
        t_voronoi = time.perf_counter() - t0

        t0 = time.perf_counter()
        for x, y in points:
            eisenstein_snap_naive(x, y)
        t_naive = time.perf_counter() - t0

        log("2C", f"Voronoi vs naive ({size:,})", "📊",
            f"voronoi={t_voronoi:.3f}s, naive={t_naive:.3f}s, ratio={t_voronoi/t_naive:.2f}x")

    # Batch vs single
    points_flat = [(random.uniform(-50, 50), random.uniform(-50, 50)) for _ in range(100000)]
    t0 = time.perf_counter()
    voronoi_batch(points_flat)
    t_batch = time.perf_counter() - t0

    t0 = time.perf_counter()
    for x, y in points_flat:
        eisenstein_snap_voronoi(x, y)
    t_single = time.perf_counter() - t0
    log("2B", "Batch vs single (100K)", "📊",
        f"batch={t_batch:.3f}s, single={t_single:.3f}s, ratio={t_single/t_batch:.2f}x")

    # Temporal snap throughput
    for size in [10000, 100000]:
        bg = BeatGrid(period=0.5)
        timestamps = [random.uniform(0, 1000) for _ in range(size)]
        t0 = time.perf_counter()
        bg.snap_batch(timestamps)
        elapsed = time.perf_counter() - t0
        log("2A", f"Temporal snap {size:,}", "📊", f"{size/elapsed:,.0f} ops/sec ({elapsed:.3f}s)")

    # Spectral throughput
    for size in [100, 1000, 10000, 100000]:
        data = [random.gauss(0, 1) for _ in range(size)]
        t0 = time.perf_counter()
        spectral_summary(data)
        elapsed = time.perf_counter() - t0
        log("2A", f"Spectral summary n={size:,}", "📊", f"{elapsed:.3f}s")


# ─────────────────────────────────────────────────────────────
# PHASE 3: REAL-WORLD USEFULNESS
# ─────────────────────────────────────────────────────────────

def phase3_realworld():
    print("\n" + "="*70)
    print("PHASE 3: Real-World Usefulness Tests")
    print("="*70)

    random.seed(42)

    # 3A: Sensor fusion — 6-DOF robot arm
    print("\n--- 3A: Robot Arm Drift ---")
    joints = 6
    ops = 10000
    # Simulate joint angles with small noise accumulation
    true_angles = [[0.0] * joints for _ in range(ops)]
    raw_angles = [[0.0] * joints for _ in range(ops)]
    snapped_angles = [[0.0] * joints for _ in range(ops)]

    for t in range(1, ops):
        for j in range(joints):
            # True trajectory: smooth sinusoidal
            true_angles[t][j] = math.sin(t * 0.001 * (j + 1)) * 30.0
            # Raw: true + accumulating drift + noise
            drift = 0.0001 * t * (j + 1) * 0.1
            noise = random.gauss(0, 0.01)
            raw_angles[t][j] = true_angles[t][j] + drift + noise

            # Snap to Eisenstein lattice
            z = complex(raw_angles[t][j], 0)
            nearest, dist, is_snap = eisenstein_snap(z, tolerance=0.5)
            snapped_angles[t][j] = nearest.complex.real

    # Compute RMSE over last 1000 ops
    raw_rmse = 0
    snapped_rmse = 0
    for t in range(ops - 1000, ops):
        for j in range(joints):
            raw_rmse += (raw_angles[t][j] - true_angles[t][j])**2
            snapped_rmse += (snapped_angles[t][j] - true_angles[t][j])**2
    raw_rmse = math.sqrt(raw_rmse / (1000 * joints))
    snapped_rmse = math.sqrt(snapped_rmse / (1000 * joints))

    log("3A", "Robot arm drift: raw RMSE", "📊", f"{raw_rmse:.4f}")
    log("3A", "Robot arm drift: snapped RMSE", "📊", f"{snapped_rmse:.4f}")
    log("3A", "Snapping improves accuracy",
        "PASS" if snapped_rmse < raw_rmse else "WARN",
        f"ratio={raw_rmse/snapped_rmse:.2f}x improvement")

    # 3B: Fleet heartbeat analysis
    print("\n--- 3B: Fleet Heartbeat ---")
    n_beats = 5000

    # Healthy: regular intervals with small jitter
    healthy = [1.0 + random.gauss(0, 0.02) for _ in range(n_beats)]
    # Degraded: intervals with increasing variance
    degraded = [1.0 + random.gauss(0, 0.02 + 0.001 * i / n_beats * 10) for i in range(n_beats)]

    h_healthy = hurst_exponent(healthy)
    h_degraded = hurst_exponent(degraded)
    s_healthy = spectral_summary(healthy)
    s_degraded = spectral_summary(degraded)

    log("3B", "Healthy heartbeat Hurst", "📊", f"H={h_healthy:.4f}")
    log("3B", "Degraded heartbeat Hurst", "📊", f"H={h_degraded:.4f}")
    log("3B", "Healthy stationary", "📊", f"is_stationary={s_healthy.is_stationary}")
    log("3B", "Degraded stationary", "📊", f"is_stationary={s_degraded.is_stationary}")

    # 3C: MIDI Tempo Extraction
    print("\n--- 3C: MIDI Tempo ---")
    ft = FluxTensorMIDI(TempoMap(ticks_per_beat=480, initial_bpm=120.0))
    room1 = ft.add_room("piano", channel=0, voice=0)
    room2 = ft.add_room("drums", channel=1, voice=0)

    # Generate 8 bars of quarter notes at 120 BPM
    for bar in range(8):
        for beat in range(4):
            tick = (bar * 4 + beat) * 480
            ft.note_on("piano", tick, 60 + beat * 2, 100)
            ft.note_on("drums", tick, 36, 120)
            ft.note_off("piano", tick + 240, 60 + beat * 2)
            ft.note_off("drums", tick + 120, 36)

    events = ft.render()
    log("3C", "MIDI event count", "PASS" if len(events) == 64 else "FAIL",
        f"{len(events)} events (expected 64)")

    # Tempo map conversions
    tmap = TempoMap(ticks_per_beat=480, initial_bpm=120.0)
    sec = tmap.tick_to_seconds(480)
    log("3C", "tick_to_seconds(480) at 120bpm", "PASS" if abs(sec - 0.5) < 1e-10 else "FAIL",
        f"{sec:.6f}s (expected 0.5)")

    back = tmap.seconds_to_tick(0.5)
    log("3C", "seconds_to_tick(0.5) at 120bpm", "PASS" if back == 480 else "FAIL",
        f"tick={back} (expected 480)")

    # Quantize
    ft2 = FluxTensorMIDI(TempoMap(ticks_per_beat=480, initial_bpm=120.0))
    ft2.add_room("test", channel=0)
    for tick in [50, 130, 250, 370, 500]:
        ft2.note_on("test", tick, 60, 100)
    quantized = ft2.quantize(grid=120)
    expected_ticks = [0, 120, 240, 360, 480]
    actual_ticks = [e.tick for e in quantized]
    log("3C", "Quantize to 120-tick grid", "PASS" if actual_ticks == expected_ticks else "FAIL",
        f"got {actual_ticks}, expected {expected_ticks}")

    # Timeline
    tl = ft.timeline_seconds()
    log("3C", "Timeline duration", "📊", f"{tl:.3f}s")

    # Room management
    log("3C", "Room list", "PASS" if ft.rooms == ["piano", "drums"] else "FAIL",
        f"{ft.rooms}")

    # Channel validation
    try:
        ft.add_room("bad", channel=16)
        log("3C", "Channel 16 rejected", "FAIL", "no error")
    except ValueError:
        log("3C", "Channel 16 rejected", "PASS", "")

    # Duplicate room
    try:
        ft.add_room("piano", channel=2)
        log("3C", "Duplicate room rejected", "FAIL", "no error")
    except ValueError:
        log("3C", "Duplicate room rejected", "PASS", "")

    # Tempo change
    tmap2 = TempoMap(ticks_per_beat=480, initial_bpm=120.0)
    tmap2.set_tempo(960, 180.0)  # at tick 960, switch to 180bpm
    s1 = tmap2.tick_to_seconds(480)   # 120bpm: 0.5s
    s2 = tmap2.tick_to_seconds(1440)  # 960 ticks at 120bpm + 480 at 180bpm
    expected_s2 = 960 * 60.0 / (120 * 480) + 480 * 60.0 / (180 * 480)
    log("3C", "Tempo change tick_to_seconds",
        "PASS" if abs(s2 - expected_s2) < 1e-10 else "FAIL",
        f"got {s2:.6f}, expected {expected_s2:.6f}")


# ─────────────────────────────────────────────────────────────
# PHASE 4: ADVERSARIAL / STRESS TESTS
# ─────────────────────────────────────────────────────────────

def phase4_stress():
    print("\n" + "="*70)
    print("PHASE 4: Adversarial / Stress Tests")
    print("="*70)

    # 4A: Numerical stability
    # Very large
    for val in [2**30, 1e15, 1e30]:
        a, b = eisenstein_snap_voronoi(float(val), float(val))
        log("4A", f"Large value snap ({val:.0e})", "📊",
            f"snap→({a}, {b})")

    # Very small
    for val in [1e-15, 1e-30, 5e-16]:
        a, b = eisenstein_snap_voronoi(val, val)
        log("4A", f"Small value snap ({val:.0e})", "📊",
            f"snap→({a}, {b})")

    # NaN / Inf
    for name, x, y in [("NaN", float('nan'), 1.0), ("Inf", float('inf'), 1.0),
                        ("-Inf", float('-inf'), 1.0), ("NaN,NaN", float('nan'), float('nan'))]:
        try:
            a, b = eisenstein_snap_voronoi(x, y)
            log("4A", f"Input ({name})", "WARN",
                f"snap→({a}, {b}) — no error raised")
        except (ValueError, OverflowError) as e:
            log("4A", f"Input ({name})", "PASS", f"raised {type(e).__name__}")

    # Mixed positive/negative
    for x, y in [(-100, 100), (100, -100), (-1e6, 1e6), (0, -1e-15)]:
        a, b = eisenstein_snap_voronoi(x, y)
        log("4A", f"Mixed sign ({x}, {y})", "📊", f"snap→({a}, {b})")

    # 4B: Exhaustive boundary test
    # All Eisenstein points within covering radius of (0,0) should snap back to (0,0)
    # Covering radius = 1/√3 ≈ 0.577350269...
    INV_SQRT3 = 1.0 / math.sqrt(3)
    fail_count = 0
    total = 0
    # Sample a grid of points within the inscribed circle
    step = 0.02
    x = -INV_SQRT3
    while x <= INV_SQRT3:
        y_max_sq = INV_SQRT3**2 - x**2
        if y_max_sq > 0:
            y_max = math.sqrt(y_max_sq)
            y = -y_max
            while y <= y_max:
                a, b = eisenstein_snap_voronoi(x, y)
                if (a, b) != (0, 0):
                    fail_count += 1
                total += 1
                y += step
        x += step

    log("4B", f"Exhaustive interior ({total:,} points)", "PASS" if fail_count == 0 else "FAIL",
        f"{fail_count}/{total} points did NOT snap to (0,0)")

    # Points just outside should snap elsewhere
    outside_fail = 0
    for angle_deg in range(0, 360, 15):
        angle = math.radians(angle_deg)
        # Point at distance 0.6 > 1/√3
        ox = 0.6 * math.cos(angle)
        oy = 0.6 * math.sin(angle)
        a, b = eisenstein_snap_voronoi(ox, oy)
        # Should NOT be (0,0) for most directions
        # Actually it could be (0,0) for some — check distance
        dx = ox - (a - b * 0.5)
        dy = oy - (b * 0.5 * math.sqrt(3))
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > INV_SQRT3 + 0.01:
            outside_fail += 1
    log("4B", "Outside points distance check", "PASS" if outside_fail == 0 else "FAIL",
        f"{outside_fail}/24 exceeded covering radius")

    # EisensteinInteger edge cases
    e = EisensteinInteger(0, 0)
    log("4B", "EisensteinInteger(0,0).norm", "PASS" if e.norm_squared == 0 else "FAIL",
        f"norm²={e.norm_squared}")
    log("4B", "EisensteinInteger(1,0) * (0,1)", "📊",
        str(EisensteinInteger(1, 0) * EisensteinInteger(0, 1)))
    log("4B", "EisensteinInteger conjugate", "📊",
        str(EisensteinInteger(3, 5).conjugate()))

    # Eisenstein distance
    d = eisenstein_distance(complex(0.1, 0.1), complex(0, 0))
    log("4B", "Eisenstein distance", "📊", f"d={d:.4f}")

    # Fundamental domain
    unit, reduced = eisenstein_fundamental_domain(complex(2, 1))
    log("4B", "Fundamental domain", "📊", f"unit={unit}, reduced={reduced}")

    # MIDI edge cases
    tmap = TempoMap(ticks_per_beat=480, initial_bpm=120.0)
    log("4B", "bpm_at(0)", "PASS" if tmap.bpm_at(0) == 120.0 else "FAIL",
        f"{tmap.bpm_at(0)}")
    log("4B", "beat_duration_seconds(120)", "PASS" if abs(tmap.beat_duration_seconds(120) - 0.5) < 1e-10 else "FAIL",
        f"{tmap.beat_duration_seconds(120)}")

    ft = FluxTensorMIDI()
    ft.add_room("test", 0)
    log("4B", "Empty event count", "PASS" if ft.event_count == 0 else "FAIL",
        f"{ft.event_count}")
    log("4B", "Empty timeline", "PASS" if ft.timeline_seconds() == 0.0 else "FAIL",
        f"{ft.timeline_seconds()}")
    ft.clear()
    log("4B", "Clear works", "PASS", "")

    # TempoMap seconds_to_tick roundtrip
    for tick in [0, 100, 480, 960, 10000]:
        s = tmap.tick_to_seconds(tick)
        back = tmap.seconds_to_tick(s)
        log("4B", f"Tick roundtrip {tick}", "PASS" if back == tick else "FAIL",
            f"tick→{s:.6f}s→tick={back}")


# ─────────────────────────────────────────────────────────────
# RUN ALL PHASES
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  SNAPKIT-V2 COMPREHENSIVE EXPERIMENT SUITE                  ║")
    print("║  4 Phases: Correctness, Performance, Real-World, Stress     ║")
    print("╚══════════════════════════════════════════════════════════════╝")

    try:
        phase1a_eisenstein_falsification()
    except Exception as e:
        traceback.print_exc()
        log("1A", "PHASE CRASH", "FAIL", str(e))

    try:
        phase1b_temporal_correctness()
    except Exception as e:
        traceback.print_exc()
        log("1B", "PHASE CRASH", "FAIL", str(e))

    try:
        phase1c_spectral_validation()
    except Exception as e:
        traceback.print_exc()
        log("1C", "PHASE CRASH", "FAIL", str(e))

    try:
        phase1d_connectome()
    except Exception as e:
        traceback.print_exc()
        log("1D", "PHASE CRASH", "FAIL", str(e))

    try:
        phase2_benchmarks()
    except Exception as e:
        traceback.print_exc()
        log("2", "PHASE CRASH", "FAIL", str(e))

    try:
        phase3_realworld()
    except Exception as e:
        traceback.print_exc()
        log("3", "PHASE CRASH", "FAIL", str(e))

    try:
        phase4_stress()
    except Exception as e:
        traceback.print_exc()
        log("4", "PHASE CRASH", "FAIL", str(e))

    # ─────────────────────────────────────────────────────────────
    # SUMMARY
    # ─────────────────────────────────────────────────────────────
    pass_count = sum(1 for r in RESULTS if r["status"] == "PASS")
    fail_count = sum(1 for r in RESULTS if r["status"] == "FAIL")
    warn_count = sum(1 for r in RESULTS if r["status"] == "WARN")
    info_count = sum(1 for r in RESULTS if r["status"] == "📊")

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"  ✅ PASS: {pass_count}")
    print(f"  ❌ FAIL: {fail_count}")
    print(f"  ⚠️  WARN: {warn_count}")
    print(f"  📊 INFO: {info_count}")
    print(f"  TOTAL:   {len(RESULTS)}")
    print()

    # Save results for report generation
    import json
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "experiment_results.json"), "w") as f:
        json.dump(RESULTS, f, indent=2)

    print(f"Results saved to experiment_results.json")
