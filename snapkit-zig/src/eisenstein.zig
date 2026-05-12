//! Eisenstein integer snap — naive and Voronoï 9-candidate algorithms.
//!
//! Covering radius ≤ 1/√3 guaranteed by the A₂ lattice structure.
//! The Voronoï cell of the Eisenstein integer lattice (A₂) is a regular hexagon
//! with circumradius 1/√3, so rounding to the nearest lattice point never exceeds
//! this distance.

const std = @import("std");
const types = @import("types.zig");
const EisensteinInteger = types.EisensteinInteger;
const SnapResult = types.SnapResult;
const sqrt3 = types.sqrt3;
const inv_sqrt3 = types.inv_sqrt3;
const half_sqrt3 = types.half_sqrt3;

// ── comptime constraint checking ──

/// Verify at compile time that (a, b) is a valid Eisenstein integer.
/// This is trivially always true since a, b ∈ Z by construction,
/// but we can verify that the point lies on the lattice (i.e., has integer
/// coordinates in the Eisenstein basis). More usefully, we can check that
/// a given floating-point pair corresponds exactly to an Eisenstein integer.
pub fn comptimeValid(comptime a: i64, comptime b: i64) void {
    // All integer pairs (a, b) are valid Eisenstein integers.
    // This function serves as a comptime assertion point — if you need
    // additional constraints (e.g., norm_squared == specific value), add them here.
    _ = a;
    _ = b;
}

/// Compile-time verification that a floating-point (x, y) pair lies exactly
/// on an Eisenstein lattice point. Causes a compile error if not.
pub fn comptimeAssertLatticePoint(comptime x: f64, comptime y: f64) EisensteinInteger {
    const result = comptime blk: {
        const b_float: f64 = 2.0 * y / sqrt3;
        const a_float: f64 = x + b_float * 0.5;
        const a_rounded: f64 = @round(a_float);
        const b_rounded: f64 = @round(b_float);
        if (a_float != a_rounded or b_float != b_rounded) {
            @compileError("supplied coordinates do not lie on the Eisenstein lattice");
        }
        const a: i64 = @intFromFloat(a_rounded);
        const b: i64 = @intFromFloat(b_rounded);
        const rx: f64 = @as(f64, @floatFromInt(a)) - 0.5 * @as(f64, @floatFromInt(b));
        const ry: f64 = half_sqrt3 * @as(f64, @floatFromInt(b));
        if (rx != x or ry != y) {
            @compileError("round-trip verification failed — not a lattice point");
        }
        break :blk .{ .a = a, .b = b };
    };
    return result;
}

/// Compile-time snap: given comptime-known (x, y), compute the nearest
/// Eisenstein integer at compile time. The result is a comptime constant.
pub fn comptimeSnap(comptime x: f64, comptime y: f64) EisensteinInteger {
    return comptime blk: {
        const b0: f64 = @round(2.0 * y * inv_sqrt3);
        const a0: f64 = @round(x + b0 * 0.5);
        var best_dist: f64 = 1e30;
        var best_a: i64 = @intFromFloat(a0);
        var best_b: i64 = @intFromFloat(b0);
        for (&[_]i64{ -1, 0, 1 }) |da| {
            for (&[_]i64{ -1, 0, 1 }) |db| {
                const a = @as(i64, @intFromFloat(a0)) + da;
                const b = @as(i64, @intFromFloat(b0)) + db;
                const cx: f64 = @as(f64, @floatFromInt(a)) - 0.5 * @as(f64, @floatFromInt(b));
                const cy: f64 = half_sqrt3 * @as(f64, @floatFromInt(b));
                const dx = x - cx;
                const dy = y - cy;
                const d2 = dx * dx + dy * dy;
                if (d2 < best_dist - 1e-24) {
                    best_dist = d2;
                    best_a = a;
                    best_b = b;
                } else if (@abs(d2 - best_dist) < 1e-24) {
                    if (@abs(a) + @abs(b) < @abs(best_a) + @abs(best_b)) {
                        best_a = a;
                        best_b = b;
                    }
                }
            }
        }
        break :blk .{ .a = best_a, .b = best_b };
    };
}

// ── Runtime algorithms ──

/// Naive 4-candidate snap: floor (a, b) then check 2×2 neighborhood.
pub fn snapNaive(x: f64, y: f64) EisensteinInteger {
    const b_float = 2.0 * y / sqrt3;
    const a_float = x + b_float * 0.5;
    const a_floor: i64 = @intFromFloat(@floor(a_float));
    const b_floor: i64 = @intFromFloat(@floor(b_float));

    var best: EisensteinInteger = .{ .a = a_floor, .b = b_floor };
    var best_dist: f64 = 1e30;

    const offsets = [_]i64{ 0, 1 };
    for (offsets) |da| {
        for (offsets) |db| {
            const a = a_floor + da;
            const b = b_floor + db;
            const cx = @as(f64, @floatFromInt(a)) - 0.5 * @as(f64, @floatFromInt(b));
            const cy = half_sqrt3 * @as(f64, @floatFromInt(b));
            const dx = x - cx;
            const dy = y - cy;
            const d2 = dx * dx + dy * dy;
            if (d2 < best_dist - 1e-18) {
                best_dist = d2;
                best = .{ .a = a, .b = b };
            } else if (@abs(d2 - best_dist) < 1e-18) {
                if (@abs(a) + @abs(b) < @abs(best.a) + @abs(best.b)) {
                    best = .{ .a = a, .b = b };
                }
            }
        }
    }
    return best;
}

/// Voronoï 9-candidate snap: exact nearest-neighbor on the A₂ lattice.
///
/// The A₂ lattice's Voronoï cell is a regular hexagon. By rounding to the
/// nearest candidate and searching the 3×3 neighborhood, we guarantee finding
/// the true nearest neighbor. Covering radius ≤ 1/√3.
pub fn snapVoronoi(x: f64, y: f64) EisensteinInteger {
    const b0: f64 = @round(2.0 * y * inv_sqrt3);
    const a0: f64 = @round(x + b0 * 0.5);
    const ia0: i64 = @intFromFloat(a0);
    const ib0: i64 = @intFromFloat(b0);

    var best_dist: f64 = 1e30;
    var best_a: i64 = ia0;
    var best_b: i64 = ib0;

    const offsets = [_]i64{ -1, 0, 1 };
    for (offsets) |da| {
        for (offsets) |db| {
            const a = ia0 + da;
            const b = ib0 + db;
            const dx = x - (@as(f64, @floatFromInt(a)) - 0.5 * @as(f64, @floatFromInt(b)));
            const dy = y - (half_sqrt3 * @as(f64, @floatFromInt(b)));
            const d2 = dx * dx + dy * dy;
            if (d2 < best_dist - 1e-24) {
                best_dist = d2;
                best_a = a;
                best_b = b;
            } else if (@abs(d2 - best_dist) < 1e-24) {
                if (@abs(a) + @abs(b) < @abs(best_a) + @abs(best_b)) {
                    best_a = a;
                    best_b = b;
                }
            }
        }
    }
    return .{ .a = best_a, .b = best_b };
}

/// Snap with tolerance check.
pub fn snap(x: f64, y: f64, tolerance: f64) SnapResult {
    const nearest = snapVoronoi(x, y);
    const cx = nearest.x();
    const cy = nearest.y();
    const dx = x - cx;
    const dy = y - cy;
    const dist = @sqrt(dx * dx + dy * dy);
    return .{
        .nearest = nearest,
        .distance = dist,
        .is_snap = dist <= tolerance,
    };
}

/// Eisenstein lattice distance between two points.
pub fn eisensteinDistance(x1: f64, y1: f64, x2: f64, y2: f64) f64 {
    const dx = x1 - x2;
    const dy = y1 - y2;
    const n = snapVoronoi(dx, dy);
    const cx = n.x();
    const cy = n.y();
    const rx = dx - cx;
    const ry = dy - cy;
    const residual = @sqrt(rx * rx + ry * ry);
    return @sqrt(@as(f64, @floatFromInt(n.normSquared()))) + residual;
}

// ── SIMD batch snap using @Vector ──

/// Batch Voronoï snap using SIMD @Vector operations.
/// Processes points in chunks of `vec_len` for SIMD acceleration.
pub fn snapBatchSimd(x_coords: []const f64, y_coords: []const f64, out: []EisensteinInteger) void {
    const vec_len = 4; // f64 vectors of length 4 = 256-bit SIMD
    const Vec = @Vector(vec_len, f64);
    const IVec = @Vector(vec_len, i64);
    const len = @min(x_coords.len, y_coords.len, out.len);
    const remainder = len % vec_len;
    const simd_len = len - remainder;

    // Process SIMD chunks
    var i: usize = 0;
    while (i < simd_len) : (i += vec_len) {
        const vx: Vec = x_coords[i..][0..vec_len].*;
        const vy: Vec = y_coords[i..][0..vec_len].*;

        const two: Vec = @splat(2.0);
        const b0: Vec = @round(two * vy * @as(Vec, @splat(inv_sqrt3)));
        const a0: Vec = @round(vx + b0 * @as(Vec, @splat(0.5)));

        // For each of 9 candidates, compute squared distance vectorized
        const a0_int: IVec = @intFromFloat(a0);
        const b0_int: IVec = @intFromFloat(b0);
        var best_dist: Vec = @splat(1e30);
        var best_a: IVec = a0_int;
        var best_b: IVec = b0_int;

        const da_vals: [3]i64 = .{ -1, 0, 1 };
        const db_vals: [3]i64 = .{ -1, 0, 1 };
        for (da_vals) |da| {
            for (db_vals) |db| {
                const a_vec: IVec = a0_int + @as(IVec, @splat(@as(i64, da)));
                const b_vec: IVec = b0_int + @as(IVec, @splat(@as(i64, db)));
                const a_f: Vec = @floatFromInt(a_vec);
                const b_f: Vec = @floatFromInt(b_vec);
                const cx: Vec = a_f - b_f * @as(Vec, @splat(0.5));
                const cy: Vec = b_f * @as(Vec, @splat(half_sqrt3));
                const dx: Vec = vx - cx;
                const dy: Vec = vy - cy;
                const d2: Vec = dx * dx + dy * dy;

                const better = d2 < best_dist - @as(Vec, @splat(1e-24));
                best_dist = @select(f64, better, d2, best_dist);
                best_a = @select(i64, better, a_vec, best_a);
                best_b = @select(i64, better, b_vec, best_b);
            }
        }

        out[i] = .{ .a = best_a[0], .b = best_b[0] };
        out[i + 1] = .{ .a = best_a[1], .b = best_b[1] };
        out[i + 2] = .{ .a = best_a[2], .b = best_b[2] };
        out[i + 3] = .{ .a = best_a[3], .b = best_b[3] };
    }

    // Process remainder with scalar
    for (simd_len..len) |j| {
        out[j] = snapVoronoi(x_coords[j], y_coords[j]);
    }
}

/// Simple scalar batch snap (fallback, also used by the SIMD path for remainders).
pub fn snapBatch(x_coords: []const f64, y_coords: []const f64, out: []EisensteinInteger) void {
    const len = @min(x_coords.len, y_coords.len, out.len);
    for (x_coords[0..len], y_coords[0..len], out[0..len]) |x_val, y_val, *o| {
        o.* = snapVoronoi(x_val, y_val);
    }
}

/// Batch snap with tolerance — fills SnapResult array.
pub fn snapBatchFull(
    x_coords: []const f64,
    y_coords: []const f64,
    tolerance: f64,
    out: []SnapResult,
) void {
    const len = @min(x_coords.len, y_coords.len, out.len);
    for (x_coords[0..len], y_coords[0..len], out[0..len]) |x_val, y_val, *o| {
        o.* = snap(x_val, y_val, tolerance);
    }
}

// ── C-compatible exports ──

export fn sk_eisenstein_snap_naive(x: f64, y: f64) EisensteinInteger {
    return snapNaive(x, y);
}

export fn sk_eisenstein_snap_voronoi(x: f64, y: f64) EisensteinInteger {
    return snapVoronoi(x, y);
}

export fn sk_eisenstein_snap(x: f64, y: f64, tolerance: f64) SnapResult {
    return snap(x, y, tolerance);
}

export fn sk_eisenstein_snap_batch(
    x: [*]const f64,
    y: [*]const f64,
    n: usize,
    out: [*]EisensteinInteger,
) void {
    snapBatchSimd(x[0..n], y[0..n], out[0..n]);
}

export fn sk_eisenstein_snap_batch_full(
    x: [*]const f64,
    y: [*]const f64,
    n: usize,
    tolerance: f64,
    out: [*]SnapResult,
) void {
    snapBatchFull(x[0..n], y[0..n], tolerance, out[0..n]);
}

export fn sk_eisenstein_distance(x1: f64, y1: f64, x2: f64, y2: f64) f64 {
    return eisensteinDistance(x1, y1, x2, y2);
}

// ── Tests ──

test "EisensteinInteger basic operations" {
    const e = EisensteinInteger.init(3, 1);
    try std.testing.expectEqual(@as(i64, 3), e.a);
    try std.testing.expectEqual(@as(i64, 1), e.b);
    try std.testing.expectEqual(@as(i64, 7), e.normSquared()); // 9 - 3 + 1 = 7
}

test "EisensteinInteger arithmetic" {
    const e1 = EisensteinInteger.init(2, 3);
    const e2 = EisensteinInteger.init(1, 1);
    const sum = e1.add(e2);
    try std.testing.expectEqual(@as(i64, 3), sum.a);
    try std.testing.expectEqual(@as(i64, 4), sum.b);

    const diff = e1.sub(e2);
    try std.testing.expectEqual(@as(i64, 1), diff.a);
    try std.testing.expectEqual(@as(i64, 2), diff.b);
}

test "EisensteinInteger conjugate" {
    const e = EisensteinInteger.init(3, 2);
    const conj = e.conjugate();
    try std.testing.expectEqual(@as(i64, 5), conj.a); // a + b = 5
    try std.testing.expectEqual(@as(i64, -2), conj.b); // -b = -2
}

test "EisensteinInteger multiply" {
    const e1 = EisensteinInteger.init(2, 1);
    const e2 = EisensteinInteger.init(1, 1);
    const prod = e1.mul(e2);
    // (a*c - b*d, a*d + b*c - b*d) = (2*1-1*1, 2*1+1*1-1*1) = (1, 2)
    try std.testing.expectEqual(@as(i64, 1), prod.a);
    try std.testing.expectEqual(@as(i64, 2), prod.b);
}

test "snapNaive — origin" {
    const result = snapNaive(0.0, 0.0);
    try std.testing.expectEqual(@as(i64, 0), result.a);
    try std.testing.expectEqual(@as(i64, 0), result.b);
}

test "snapVoronoi — origin" {
    const result = snapVoronoi(0.0, 0.0);
    try std.testing.expectEqual(@as(i64, 0), result.a);
    try std.testing.expectEqual(@as(i64, 0), result.b);
}

test "snapVoronoi — unit basis vector e1" {
    const result = snapVoronoi(1.0, 0.0);
    try std.testing.expectEqual(@as(i64, 1), result.a);
    try std.testing.expectEqual(@as(i64, 0), result.b);
}

test "snapVoronoi — unit basis vector ω" {
    const result = snapVoronoi(-0.5, half_sqrt3);
    try std.testing.expectEqual(@as(i64, 0), result.a);
    try std.testing.expectEqual(@as(i64, 1), result.b);
}

test "snapVoronoi — small offset snaps back" {
    // Point near (1, 0) with small offset should snap to (1, 0)
    const result = snapVoronoi(1.05, 0.02);
    try std.testing.expectEqual(@as(i64, 1), result.a);
    try std.testing.expectEqual(@as(i64, 0), result.b);
}

test "snap with tolerance — on lattice" {
    const result = snap(1.0, 0.0, 0.5);
    try std.testing.expect(result.is_snap);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), result.distance, 1e-10);
}

test "snap with tolerance — off lattice but within tolerance" {
    const result = snap(1.3, 0.1, 0.5);
    try std.testing.expect(result.is_snap);
}

test "covering radius guarantee — distance never exceeds 1/√3" {
    // Test many points to verify covering radius
    var i: i32 = -20;
    while (i <= 20) : (i += 1) {
        var j: i32 = -20;
        while (j <= 20) : (j += 1) {
            const x_val = @as(f64, @floatFromInt(i)) * 0.1;
            const y_val = @as(f64, @floatFromInt(j)) * 0.1;
            const result = snap(x_val, y_val, 1.0);
            try std.testing.expect(result.distance <= types.covering_radius + 1e-10);
        }
    }
}

test "comptimeSnap — compile-time nearest Eisenstein integer" {
    // This snap is computed entirely at compile time
    const ct_result = comptimeSnap(0.7, 0.3);
    // Should snap to (1, 0) since that's the nearest lattice point
    try std.testing.expectEqual(@as(i64, 1), ct_result.a);
    try std.testing.expectEqual(@as(i64, 0), ct_result.b);

    // Compile-time snap of origin
    const ct_origin = comptimeSnap(0.0, 0.0);
    try std.testing.expectEqual(@as(i64, 0), ct_origin.a);
    try std.testing.expectEqual(@as(i64, 0), ct_origin.b);
}

test "comptimeAssertLatticePoint — valid point compiles" {
    // (1.0, 0.0) is a lattice point: a=1, b=0
    const e = comptimeAssertLatticePoint(1.0, 0.0);
    try std.testing.expectEqual(@as(i64, 1), e.a);
    try std.testing.expectEqual(@as(i64, 0), e.b);
}

test "comptimeAssertLatticePoint — ω point" {
    // (-0.5, √3/2) = ω = a=0, b=1
    const e = comptimeAssertLatticePoint(-0.5, half_sqrt3);
    try std.testing.expectEqual(@as(i64, 0), e.a);
    try std.testing.expectEqual(@as(i64, 1), e.b);
}

test "batch snap — scalar" {
    const xs = [_]f64{ 0.0, 1.0, -0.5, 2.0 };
    const ys = [_]f64{ 0.0, 0.0, half_sqrt3, 0.0 };
    var results: [4]EisensteinInteger = undefined;
    snapBatch(&xs, &ys, &results);

    try std.testing.expectEqual(@as(i64, 0), results[0].a);
    try std.testing.expectEqual(@as(i64, 0), results[0].b);
    try std.testing.expectEqual(@as(i64, 1), results[1].a);
    try std.testing.expectEqual(@as(i64, 0), results[1].b);
    try std.testing.expectEqual(@as(i64, 0), results[2].a);
    try std.testing.expectEqual(@as(i64, 1), results[2].b);
    try std.testing.expectEqual(@as(i64, 2), results[3].a);
    try std.testing.expectEqual(@as(i64, 0), results[3].b);
}

test "batch snap — SIMD" {
    const xs = [_]f64{ 0.0, 1.0, -0.5, 2.0, 0.3 };
    const ys = [_]f64{ 0.0, 0.0, half_sqrt3, 0.0, 0.1 };
    var results: [5]EisensteinInteger = undefined;
    snapBatchSimd(&xs, &ys, &results);

    try std.testing.expectEqual(@as(i64, 0), results[0].a);
    try std.testing.expectEqual(@as(i64, 0), results[0].b);
    try std.testing.expectEqual(@as(i64, 1), results[1].a);
    try std.testing.expectEqual(@as(i64, 0), results[1].b);
    try std.testing.expectEqual(@as(i64, 0), results[2].a);
    try std.testing.expectEqual(@as(i64, 1), results[2].b);
    try std.testing.expectEqual(@as(i64, 2), results[3].a);
    try std.testing.expectEqual(@as(i64, 0), results[3].b);
}

test "eisenstein distance" {
    const dist = eisensteinDistance(0.0, 0.0, 1.0, 0.0);
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), dist, 1e-10);
}
