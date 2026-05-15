//! WASM entry point for constraint theory library.
//! Build: zig build-exe constraint_wasm.zig -target wasm32-freestanding -OReleaseFast -rdynamic
//!
//! Exported functions:
//!   eisenstein_norm_wasm(a, b) → i64
//!   constraint_check_wasm(a, b, radius_bits) → bool
//!   eisenstein_snap_wasm(x_bits, y_bits) → u128 (a in low 64, b in high 64)
//!   lattice_enumerate_wasm(radius_bits) → usize (count)
//!   get_point_a(idx) → i64
//!   get_point_b(idx) → i64

const std = @import("std");

pub fn eisensteinNorm(a: i64, b: i64) i64 {
    return a * a - a * b + b * b;
}

pub fn constraintCheck(a: i64, b: i64, radius: f64) bool {
    return @as(f64, @floatFromInt(eisensteinNorm(a, b))) <= radius * radius;
}

pub fn eisensteinSnap(x: f64, y: f64) struct { a: i64, b: i64 } {
    const q: f64 = 2.0 / 3.0 * x - 1.0 / 3.0 * y;
    const r: f64 = 2.0 / 3.0 * y;
    var rq: f64 = @round(q);
    var rr: f64 = @round(r);
    const rs: f64 = @round(-q - r);
    const diff: f64 = @abs(rq + rr + rs);
    if (diff == 2.0) {
        if (@abs(rq - q) > @abs(rr - r)) {
            rq = -rr - rs;
        } else {
            rr = -rq - rs;
        }
    }
    return .{ .a = @as(i64, @intFromFloat(rq)), .b = @as(i64, @intFromFloat(rr)) };
}

const IntPair = struct { a: i64, b: i64 };
var wasm_points: [8192]IntPair = undefined;
var wasm_count: usize = 0;

export fn eisenstein_norm_wasm(a: i64, b: i64) i64 {
    return eisensteinNorm(a, b);
}

export fn constraint_check_wasm(a: i64, b: i64, radius_bits: u64) bool {
    const radius = @as(f64, @bitCast(radius_bits));
    return constraintCheck(a, b, radius);
}

export fn eisenstein_snap_wasm(x_bits: u64, y_bits: u64) u128 {
    const x = @as(f64, @bitCast(x_bits));
    const y = @as(f64, @bitCast(y_bits));
    const result = eisensteinSnap(x, y);
    return @as(u128, @bitCast(@as(i128, result.a))) | (@as(u128, @bitCast(@as(i128, result.b))) << 64);
}

export fn lattice_enumerate_wasm(radius_bits: u64) usize {
    const radius = @as(f64, @bitCast(radius_bits));
    wasm_count = 0;
    const r2 = radius * radius;
    const bmax = @as(i64, @intFromFloat(@ceil(radius * 1.155)));
    var b: i64 = -bmax;
    while (b <= bmax) : (b += 1) {
        const amax = @as(i64, @intFromFloat(@ceil(radius + @as(f64, @floatFromInt(@abs(b))) * 0.5)));
        var a: i64 = -amax;
        while (a <= amax) : (a += 1) {
            if (@as(f64, @floatFromInt(eisensteinNorm(a, b))) <= r2) {
                if (wasm_count < wasm_points.len) {
                    wasm_points[wasm_count] = .{ .a = a, .b = b };
                    wasm_count += 1;
                }
            }
        }
    }
    return wasm_count;
}

export fn get_point_a(idx: usize) i64 {
    if (idx >= wasm_count) return 0;
    return wasm_points[idx].a;
}

export fn get_point_b(idx: usize) i64 {
    if (idx >= wasm_count) return 0;
    return wasm_points[idx].b;
}

// Required for freestanding WASM — no std.os.exit
pub fn panic(msg: []const u8, _: ?*std.builtin.StackTrace, _: ?usize) noreturn {
    _ = msg;
    while (true) {}
}
