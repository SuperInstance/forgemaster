const std = @import("std");

fn eisensteinNorm(a: i64, b: i64) i64 {
    return a * a - a * b + b * b;
}

const IntPair = struct { a: i64, b: i64 };

fn eisensteinSnap(x: f64, y: f64) IntPair {
    const q: f64 = (2.0 / 3.0 * x - 1.0 / 3.0 * y);
    const r: f64 = (2.0 / 3.0 * y);
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
    return IntPair{ .a = @as(i64, @intFromFloat(rq)), .b = @as(i64, @intFromFloat(rr)) };
}

fn constraintCheck(a: i64, b: i64, radius: f64) bool {
    return @as(f64, @floatFromInt(eisensteinNorm(a, b))) <= radius * radius;
}

pub fn main() !void {
    const N: usize = 10_000_000;

    var prng = std.Random.DefaultPrng.init(42);
    const rand = prng.random();

    const allocator = std.heap.page_allocator;

    const norm_a = try allocator.alloc(i64, N);
    const norm_b = try allocator.alloc(i64, N);
    const snap_x = try allocator.alloc(f64, N);
    const snap_y = try allocator.alloc(f64, N);
    const con_a = try allocator.alloc(i64, N);
    const con_b = try allocator.alloc(i64, N);
    const con_r = try allocator.alloc(f64, N);

    for (0..N) |i| {
        norm_a[i] = @as(i64, @intCast(rand.intRangeAtMost(i32, -1000, 1000)));
        norm_b[i] = @as(i64, @intCast(rand.intRangeAtMost(i32, -1000, 1000)));
        snap_x[i] = rand.float(f64) * 200.0 - 100.0;
        snap_y[i] = rand.float(f64) * 200.0 - 100.0;
        con_a[i] = @as(i64, @intCast(rand.intRangeAtMost(i32, -100, 100)));
        con_b[i] = @as(i64, @intCast(rand.intRangeAtMost(i32, -100, 100)));
        con_r[i] = rand.float(f64) * 49.0 + 1.0;
    }

    const stdout = std.io.getStdOut().writer();

    // Benchmark norm
    var norm_sum: i64 = 0;
    var timer = try std.time.Timer.start();
    for (0..N) |i| {
        norm_sum += eisensteinNorm(norm_a[i], norm_b[i]);
    }
    const norm_ns = timer.lap();
    const norm_time = @as(f64, @floatFromInt(norm_ns)) / 1e9;

    // Benchmark snap
    var snap_first: IntPair = undefined;
    timer.reset();
    for (0..N) |i| {
        const s = eisensteinSnap(snap_x[i], snap_y[i]);
        if (i == 0) snap_first = s;
    }
    const snap_ns = timer.lap();
    const snap_time = @as(f64, @floatFromInt(snap_ns)) / 1e9;

    // Benchmark constraint
    var con_pass: i64 = 0;
    timer.reset();
    for (0..N) |i| {
        if (constraintCheck(con_a[i], con_b[i], con_r[i])) con_pass += 1;
    }
    const con_ns = timer.lap();
    const con_time = @as(f64, @floatFromInt(con_ns)) / 1e9;

    try stdout.print("Zig Results (N={}):\n", .{N});
    try stdout.print("  eisenstein_norm:  {d:.3}s  (sum={})\n", .{ norm_time, norm_sum });
    try stdout.print("  eisenstein_snap:  {d:.3}s  (first=({},{})\n", .{ snap_time, snap_first.a, snap_first.b });
    try stdout.print("  constraint_check: {d:.3}s  (pass={})\n", .{ con_time, con_pass });
    try stdout.print("  TOTAL: {d:.3}s\n", .{norm_time + snap_time + con_time});
}
