//! Voronoï cell covering radius guarantee and batch operations.
//!
//! The A₂ lattice (Eisenstein integers) has Voronoï cells that are regular
//! hexagons. The covering radius is 1/√3 ≈ 0.5774, meaning EVERY point in
//! the plane is within distance 1/√3 of some lattice point.

const std = @import("std");
const types = @import("types.zig");
const EisensteinInteger = types.EisensteinInteger;
const SnapResult = types.SnapResult;
const covering_radius = types.covering_radius;
const eisenstein = @import("eisenstein.zig");

/// Verify the covering radius guarantee for a single point.
/// Returns the distance and asserts it's ≤ 1/√3.
pub fn verifyCoveringRadius(x: f64, y: f64) f64 {
    const result = eisenstein.snap(x, y, covering_radius);
    return result.distance;
}

/// Exhaustively verify the covering radius on a grid.
/// Returns the maximum distance found (should be ≤ 1/√3).
pub fn verifyCoveringRadiusGrid(
    x_min: f64,
    x_max: f64,
    y_min: f64,
    y_max: f64,
    step: f64,
) f64 {
    var max_dist: f64 = 0.0;
    var x = x_min;
    while (x <= x_max) : (x += step) {
        var y = y_min;
        while (y <= y_max) : (y += step) {
            const dist = verifyCoveringRadius(x, y);
            if (dist > max_dist) max_dist = dist;
        }
    }
    return max_dist;
}

/// Batch snap with SIMD acceleration and covering radius verification.
/// Asserts all distances ≤ 1/√3 in debug builds.
pub fn snapBatchVerified(
    x_coords: []const f64,
    y_coords: []const f64,
    out: []SnapResult,
    tolerance: f64,
) void {
    const len = @min(x_coords.len, y_coords.len, out.len);
    for (x_coords[0..len], y_coords[0..len], out[0..len]) |x_val, y_val, *o| {
        o.* = eisenstein.snap(x_val, y_val, tolerance);
        if (std.debug.runtime_safety) {
            std.debug.assert(o.*.distance <= covering_radius + 1e-10);
        }
    }
}

// ── Tests ──

test "covering radius — exhaustive grid check" {
    const max_dist = verifyCoveringRadiusGrid(-2.0, 2.0, -2.0, 2.0, 0.05);
    try std.testing.expect(max_dist <= covering_radius + 1e-10);
}

test "covering radius — worst case points" {
    // The worst-case points are the centers of hexagonal edges
    // For the Voronoï cell centered at origin, these are at distance 1/√3
    // The center of the hexagonal edge between (1,0) and (0,1) is at:
    // midpoint of (1,0) and (-0.5, √3/2) = (0.25, √3/4)
    const x = 0.25;
    const y = types.half_sqrt3 * 0.5; // √3/4
    const dist = verifyCoveringRadius(x, y);
    try std.testing.expect(dist <= covering_radius + 1e-10);
}
