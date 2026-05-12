//! snapkit-zig — constraint geometry snap toolkit for Zig.
//!
//! Zero dependencies. Compile-time constraint checking. Cross-compilation.
//! C-compatible exports. SIMD batch operations. No hidden control flow.
//!
//! Quick start:
//!   const snapkit = @import("snapkit-zig");
//!   const nearest = snapkit.eisenstein.snapVoronoi(1.3, 0.7);
//!   const result = snapkit.eisenstein.snap(1.3, 0.7, 0.5);

pub const types = @import("types.zig");
pub const eisenstein = @import("eisenstein.zig");
pub const voronoi = @import("voronoi.zig");
pub const temporal = @import("temporal.zig");
pub const spectral = @import("spectral.zig");

// Re-export key types at the root level
pub const EisensteinInteger = types.EisensteinInteger;
pub const SnapResult = types.SnapResult;
pub const TemporalResult = types.TemporalResult;
pub const BeatGrid = types.BeatGrid;
pub const SpectralSummary = types.SpectralSummary;

// ── Root-level integration test ──

test "integration — snap pipeline" {
    // Snap a point, verify covering radius, compute spectral features
    const x: f64 = 1.37;
    const y: f64 = 0.82;

    // 1. Snap to lattice
    const result = eisenstein.snap(x, y, 0.5);
    try @import("std").testing.expect(result.distance <= types.covering_radius + 1e-10);

    // 2. Verify covering radius
    const max_dist = voronoi.verifyCoveringRadiusGrid(-1.0, 1.0, -1.0, 1.0, 0.1);
    try @import("std").testing.expect(max_dist <= types.covering_radius + 1e-10);

    // 3. Temporal snap
    const grid = try temporal.beatGridInit(1.0, 0.0, 0.0);
    const ts = temporal.beatGridSnap(&grid, 2.05, 0.1);
    try @import("std").testing.expect(ts.is_on_beat);

    // 4. Spectral analysis
    var data: [50]f64 = undefined;
    for (&data, 0..) |*d, i| {
        d.* = @sin(@as(f64, @floatFromInt(i)) * 0.2);
    }
    var acf_buf: [25]f64 = undefined;
    var counts: [10]usize = undefined;
    const summary = spectral.spectralSummary(&data, 10, 12, &acf_buf, &counts);
    try @import("std").testing.expect(summary.hurst >= 0.0 and summary.hurst <= 1.0);
}

test "integration — comptime constraint pipeline" {
    // The compile-time snap runs entirely during compilation
    const ct_snap = eisenstein.comptimeSnap(0.5, 0.3);
    // Verify at runtime that comptime result matches runtime
    const rt_snap = eisenstein.snapVoronoi(0.5, 0.3);
    try @import("std").testing.expectEqual(ct_snap.a, rt_snap.a);
    try @import("std").testing.expectEqual(ct_snap.b, rt_snap.b);
}

test {
    _ = types;
    _ = eisenstein;
    _ = voronoi;
    _ = temporal;
    _ = spectral;
}
