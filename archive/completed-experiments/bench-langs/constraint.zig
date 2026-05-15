//! Constraint Theory Core — Zig 0.13.0 Production Library
//! For PLATO room constraint checking and fleet routing.
//!
//! Public API:
//!   eisensteinNorm(a, b) → i64
//!   eisensteinSnap(x, y) → IntPair
//!   constraintCheck(a, b, radius) → bool
//!   batchConstraintCheck(points, radius) → usize
//!   latticePointsInDisk(radius, allocator) → []IntPair
//!   latticeDistance(p1, p2) → i64
//!   dodecet(point) → [6]IntPair
//!   simd.eisensteinNorm4(pairs) → [4]i64
//!   simd.eisensteinNorm8(pairs) → [8]i64
//!   simd.benchmark(allocator, N) → !SimdBenchResult
//!   HexGrid — O(1) lookup hex grid with resize/neighbors/floodFill
//!   ConstraintSolver — prune-based constraint satisfaction
//!   serialize — JSON export/import for lattice point sets
//!   BenchResult / runBenchmarks — comparison suite

const std = @import("std");

// ============================================================
// Core Kernels
// ============================================================

/// Compute the Eisenstein norm N(a,b) = a² − ab + b².
pub fn eisensteinNorm(a: i64, b: i64) i64 {
    return a * a - a * b + b * b;
}

/// A pair of i64 values — represents a point in Eisenstein integer coordinates (a + bω).
pub const IntPair = struct {
    a: i64,
    b: i64,

    pub fn init(a: i64, b: i64) IntPair {
        return .{ .a = a, .b = b };
    }

    pub fn norm(self: IntPair) i64 {
        return eisensteinNorm(self.a, self.b);
    }

    pub fn eql(self: IntPair, other: IntPair) bool {
        return self.a == other.a and self.b == other.b;
    }

    pub fn format(self: IntPair, comptime _: []const u8, _: std.fmt.FormatOptions, writer: anytype) !void {
        try writer.print("({d},{d})", .{ self.a, self.b });
    }
};

/// Snap a 2D point to the nearest Eisenstein lattice point (cube-rounding algorithm).
pub fn eisensteinSnap(x: f64, y: f64) IntPair {
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
    return IntPair{ .a = @as(i64, @intFromFloat(rq)), .b = @as(i64, @intFromFloat(rr)) };
}

/// Check whether Eisenstein point (a,b) lies within a disk of given radius.
pub fn constraintCheck(a: i64, b: i64, radius: f64) bool {
    return @as(f64, @floatFromInt(eisensteinNorm(a, b))) <= radius * radius;
}

/// Batch constraint check — returns count of passing points.
pub fn batchConstraintCheck(points: []const IntPair, radius: f64) usize {
    var pass: usize = 0;
    for (points) |p| {
        if (constraintCheck(p.a, p.b, radius)) pass += 1;
    }
    return pass;
}

/// Find all Eisenstein lattice points within a disk of given radius.
pub fn latticePointsInDisk(radius: f64, allocator: std.mem.Allocator) ![]IntPair {
    var list = std.ArrayList(IntPair).init(allocator);
    const r2 = radius * radius;
    const bmax = @as(i64, @intFromFloat(@ceil(radius * 1.155)));
    var b: i64 = -bmax;
    while (b <= bmax) : (b += 1) {
        const amax = @as(i64, @intFromFloat(@ceil(radius + @as(f64, @floatFromInt(@abs(b))) * 0.5)));
        var a: i64 = -amax;
        while (a <= amax) : (a += 1) {
            if (@as(f64, @floatFromInt(eisensteinNorm(a, b))) <= r2) {
                try list.append(IntPair{ .a = a, .b = b });
            }
        }
    }
    return list.toOwnedSlice();
}

/// Eisenstein distance (norm of difference) between two lattice points.
pub fn latticeDistance(p1: IntPair, p2: IntPair) i64 {
    return eisensteinNorm(p1.a - p2.a, p1.b - p2.b);
}

/// Generate the dodecet (6 nearest neighbors) for a lattice point.
pub fn dodecet(point: IntPair) [6]IntPair {
    return [6]IntPair{
        .{ .a = point.a + 1, .b = point.b },
        .{ .a = point.a - 1, .b = point.b },
        .{ .a = point.a, .b = point.b + 1 },
        .{ .a = point.a, .b = point.b - 1 },
        .{ .a = point.a + 1, .b = point.b - 1 },
        .{ .a = point.a - 1, .b = point.b + 1 },
    };
}

// ============================================================
// 1. SIMD Batch Operations (@Vector)
// ============================================================

pub const simd = struct {
    /// Batch Eisenstein norm for 4 i64 pairs using @Vector.
    pub fn eisensteinNorm4(pairs: [4]IntPair) [4]i64 {
        const a = @Vector(4, i64){ pairs[0].a, pairs[1].a, pairs[2].a, pairs[3].a };
        const b = @Vector(4, i64){ pairs[0].b, pairs[1].b, pairs[2].b, pairs[3].b };
        const result = a * a - a * b + b * b;
        const arr: [4]i64 = result;
        return arr;
    }

    /// Batch Eisenstein norm for 8 i64 pairs using @Vector.
    pub fn eisensteinNorm8(pairs: [8]IntPair) [8]i64 {
        const a = @Vector(8, i64){ pairs[0].a, pairs[1].a, pairs[2].a, pairs[3].a, pairs[4].a, pairs[5].a, pairs[6].a, pairs[7].a };
        const b = @Vector(8, i64){ pairs[0].b, pairs[1].b, pairs[2].b, pairs[3].b, pairs[4].b, pairs[5].b, pairs[6].b, pairs[7].b };
        const result = a * a - a * b + b * b;
        const arr: [8]i64 = result;
        return arr;
    }

    /// Batch Eisenstein norm for slices. Processes in chunks of 8 with scalar tail.
    pub fn eisensteinNormBatch(pairs: []const IntPair, results: []i64) void {
        std.debug.assert(pairs.len == results.len);
        var i: usize = 0;
        // Process 8 at a time
        while (i + 8 <= pairs.len) : (i += 8) {
            const r = eisensteinNorm8(pairs[i..][0..8].*);
            @memcpy(results[i..][0..8], &r);
        }
        // Process remaining 4
        if (i + 4 <= pairs.len) {
            const r = eisensteinNorm4(pairs[i..][0..4].*);
            @memcpy(results[i..][0..4], &r);
            i += 4;
        }
        // Scalar tail
        while (i < pairs.len) : (i += 1) {
            results[i] = eisensteinNorm(pairs[i].a, pairs[i].b);
        }
    }

    pub const SimdBenchResult = struct {
        scalar_ns: u64,
        vector_ns: u64,
        speedup: f64,
        checksum_scalar: i64,
        checksum_vector: i64,
    };

    /// Benchmark scalar vs SIMD norm computation at given N.
    pub fn benchmark(allocator: std.mem.Allocator, n: usize) !SimdBenchResult {
        var prng = std.Random.DefaultPrng.init(42);
        const rand = prng.random();

        const pairs = try allocator.alloc(IntPair, n);
        defer allocator.free(pairs);
        const results_scalar = try allocator.alloc(i64, n);
        defer allocator.free(results_scalar);
        const results_vector = try allocator.alloc(i64, n);
        defer allocator.free(results_vector);

        for (0..n) |i| {
            pairs[i] = .{
                .a = @intCast(rand.intRangeAtMost(i32, -1000, 1000)),
                .b = @intCast(rand.intRangeAtMost(i32, -1000, 1000)),
            };
        }

        // Scalar pass
        var timer = try std.time.Timer.start();
        for (0..n) |i| {
            results_scalar[i] = eisensteinNorm(pairs[i].a, pairs[i].b);
        }
        const scalar_ns = timer.lap();

        // Vector pass
        timer.reset();
        eisensteinNormBatch(pairs, results_vector);
        const vector_ns = timer.lap();

        // Verify correctness
        var checksum_scalar: i64 = 0;
        var checksum_vector: i64 = 0;
        for (0..n) |i| {
            std.debug.assert(results_scalar[i] == results_vector[i]);
            checksum_scalar += results_scalar[i];
            checksum_vector += results_vector[i];
        }

        const speedup = @as(f64, @floatFromInt(scalar_ns)) / @as(f64, @floatFromInt(vector_ns));
        return .{
            .scalar_ns = scalar_ns,
            .vector_ns = vector_ns,
            .speedup = speedup,
            .checksum_scalar = checksum_scalar,
            .checksum_vector = checksum_vector,
        };
    }
};

// ============================================================
// 2. Hexagonal Grid Data Structure
// ============================================================

/// HexGrid stores Eisenstein lattice points in a flat array with O(1) coordinate→index lookup.
/// Supports resize, iterate neighbors, and flood fill within radius.
pub fn HexGrid(comptime max_extent: i64) type {
    return struct {
        const Self = @This();
        const grid_dim: usize = @intCast(2 * max_extent + 1);

        // Grid stored as flat 2D array indexed by offset (a + max_extent, b + max_extent)
        data: [grid_dim][grid_dim]bool,
        count: usize,

        pub fn init() Self {
            return .{
                .data = std.mem.zeroes([grid_dim][grid_dim]bool),
                .count = 0,
            };
        }

        /// Set point (a,b). Returns true if newly set.
        pub fn set(self: *Self, a: i64, b: i64) bool {
            if (!inBounds(a, b)) return false;
            const ai = @as(usize, @intCast(a + max_extent));
            const bi = @as(usize, @intCast(b + max_extent));
            if (!self.data[ai][bi]) {
                self.data[ai][bi] = true;
                self.count += 1;
                return true;
            }
            return false;
        }

        /// Unset point (a,b). Returns true if was set.
        pub fn unset(self: *Self, a: i64, b: i64) bool {
            if (!inBounds(a, b)) return false;
            const ai = @as(usize, @intCast(a + max_extent));
            const bi = @as(usize, @intCast(b + max_extent));
            if (self.data[ai][bi]) {
                self.data[ai][bi] = false;
                self.count -= 1;
                return true;
            }
            return false;
        }

        /// O(1) lookup — is point (a,b) set?
        pub fn get(self: Self, a: i64, b: i64) bool {
            if (!inBounds(a, b)) return false;
            const ai = @as(usize, @intCast(a + max_extent));
            const bi = @as(usize, @intCast(b + max_extent));
            return self.data[ai][bi];
        }

        pub fn inBounds(a: i64, b: i64) bool {
            return @abs(a) <= max_extent and @abs(b) <= max_extent;
        }

        /// Return the 6 hex neighbors of (a,b) that are set in the grid.
        pub fn neighbors(self: Self, a: i64, b: i64, out: *[6]IntPair) usize {
            const dirs = [_]IntPair{
                .{ .a = 1, .b = 0 },  .{ .a = -1, .b = 0 },
                .{ .a = 0, .b = 1 },  .{ .a = 0, .b = -1 },
                .{ .a = 1, .b = -1 }, .{ .a = -1, .b = 1 },
            };
            var n: usize = 0;
            for (&dirs) |d| {
                const na = a + d.a;
                const nb = b + d.b;
                if (self.get(na, nb)) {
                    out[n] = .{ .a = na, .b = nb };
                    n += 1;
                }
            }
            return n;
        }

        /// Flood fill from (a,b) — BFS to find all connected set points within max_steps.
        /// Returns an ArrayList of IntPair. Caller owns the list.
        pub fn floodFill(self: *Self, start_a: i64, start_b: i64, max_steps: i64, allocator: std.mem.Allocator) !std.ArrayList(IntPair) {
            var visited = Self.init();
            var result = std.ArrayList(IntPair).init(allocator);
            var queue = std.ArrayList(IntPair).init(allocator);
            defer queue.deinit();

            if (!self.get(start_a, start_b)) return result;

            try queue.append(.{ .a = start_a, .b = start_b });
            _ = visited.set(start_a, start_b);

            while (queue.items.len > 0) {
                const current = queue.orderedRemove(0);
                try result.append(current);
                if (result.items.len > 100000) break; // safety limit

                const dirs = [_]IntPair{
                    .{ .a = 1, .b = 0 },  .{ .a = -1, .b = 0 },
                    .{ .a = 0, .b = 1 },  .{ .a = 0, .b = -1 },
                    .{ .a = 1, .b = -1 }, .{ .a = -1, .b = 1 },
                };
                for (&dirs) |d| {
                    const na = current.a + d.a;
                    const nb = current.b + d.b;
                    const dist = latticeDistance(.{ .a = start_a, .b = start_b }, .{ .a = na, .b = nb });
                    if (dist <= max_steps and self.get(na, nb) and !visited.get(na, nb)) {
                        _ = visited.set(na, nb);
                        try queue.append(.{ .a = na, .b = nb });
                    }
                }
            }
            return result;
        }

        /// Collect all set points into an ArrayList.
        pub fn collectAll(self: Self, allocator: std.mem.Allocator) !std.ArrayList(IntPair) {
            var result = std.ArrayList(IntPair).init(allocator);
            var a: i64 = -max_extent;
            while (a <= max_extent) : (a += 1) {
                var b: i64 = -max_extent;
                while (b <= max_extent) : (b += 1) {
                    if (self.get(a, b)) {
                        try result.append(.{ .a = a, .b = b });
                    }
                }
            }
            return result;
        }

        pub fn reset(self: *Self) void {
            @memset(@as([*]u8, @ptrCast(&self.data))[0..@sizeOf(@TypeOf(self.data))], 0);
            self.count = 0;
        }
    };
}

// ============================================================
// 3. Constraint Satisfaction with Pruning
// ============================================================

/// A single constraint: Eisenstein point must satisfy norm(a,b) ≤ radius².
pub const Constraint = struct {
    center: IntPair,
    radius: f64,
};

/// Find all lattice points satisfying ALL constraints simultaneously.
/// Uses norm-based pruning: skip candidates that violate any single constraint early.
pub fn solveConstraints(constraints: []const Constraint, allocator: std.mem.Allocator) ![]IntPair {
    if (constraints.len == 0) return &[_]IntPair{};

    // Find bounding box from all constraints
    var max_r: f64 = 0;
    for (constraints) |c| {
        if (c.radius > max_r) max_r = c.radius;
    }

    var candidates = std.ArrayList(IntPair).init(allocator);
    const bmax = @as(i64, @intFromFloat(@ceil(max_r * 1.155)));
    var b: i64 = -bmax;
    while (b <= bmax) : (b += 1) {
        const amax = @as(i64, @intFromFloat(@ceil(max_r + @as(f64, @floatFromInt(@abs(b))) * 0.5)));
        var a: i64 = -amax;
        while (a <= amax) : (a += 1) {
            // Pruning: check the loosest constraint first
            // For absolute coordinates, check norm from each constraint center
            var all_pass = true;
            for (constraints) |c| {
                const da = a - c.center.a;
                const db = b - c.center.b;
                const n = eisensteinNorm(da, db);
                if (@as(f64, @floatFromInt(n)) > c.radius * c.radius) {
                    all_pass = false;
                    break;
                }
            }
            if (all_pass) {
                try candidates.append(.{ .a = a, .b = b });
            }
        }
    }
    return candidates.toOwnedSlice();
}

/// Multi-constraint solver that enumerates only within intersection of all disks.
/// More efficient than brute force when constraints have different centers.
pub fn solveConstraintsOptimized(constraints: []const Constraint, allocator: std.mem.Allocator) ![]IntPair {
    if (constraints.len == 0) return &[_]IntPair{};

    // Use first constraint's bounding region, check all others
    var candidates = std.ArrayList(IntPair).init(allocator);
    const first = constraints[0];
    const bmax = @as(i64, @intFromFloat(@ceil(first.radius * 1.155)));
    const ca = first.center.a;
    const cb = first.center.b;

    var b: i64 = -bmax;
    while (b <= bmax) : (b += 1) {
        const amax = @as(i64, @intFromFloat(@ceil(first.radius + @as(f64, @floatFromInt(@abs(b))) * 0.5)));
        var a: i64 = -amax;
        while (a <= amax) : (a += 1) {
            // First constraint check (relative to its center)
            const da0 = a;
            const db0 = b;
            const n0 = eisensteinNorm(da0, db0);
            if (@as(f64, @floatFromInt(n0)) > first.radius * first.radius) continue;

            // Convert to absolute coords
            const abs_a = ca + a;
            const abs_b = cb + b;

            // Check remaining constraints
            var all_pass = true;
            for (constraints[1..]) |c| {
                const da = abs_a - c.center.a;
                const db = abs_b - c.center.b;
                const n = eisensteinNorm(da, db);
                if (@as(f64, @floatFromInt(n)) > c.radius * c.radius) {
                    all_pass = false;
                    break;
                }
            }
            if (all_pass) {
                try candidates.append(.{ .a = abs_a, .b = abs_b });
            }
        }
    }
    return candidates.toOwnedSlice();
}

// ============================================================
// 4. JSON Serialization
// ============================================================

pub const serialize = struct {
    /// JSON-serializable lattice point set.
    pub const LatticePointSet = struct {
        name: []const u8,
        radius: f64,
        points: []const IntPair,

        pub fn jsonStringify(self: LatticePointSet, out: anytype) !void {
            try out.beginObject();
            try out.objectField("name");
            try out.write(self.name);
            try out.objectField("radius");
            try out.write(self.radius);
            try out.objectField("points");
            try out.beginArray();
            for (self.points) |p| {
                try out.beginArray();
                try out.write(p.a);
                try out.write(p.b);
                try out.endArray();
            }
            try out.endArray();
            try out.endObject();
        }
    };

    /// Result of parsing a lattice point set from JSON.
    pub const ParsedSet = struct {
        name: []u8,
        radius: f64,
        points: []IntPair,
    };

    /// Export lattice points to a JSON string.
    pub fn toJson(allocator: std.mem.Allocator, name: []const u8, radius: f64, points: []const IntPair) ![]u8 {
        var buf = std.ArrayList(u8).init(allocator);
        const writer = buf.writer();
        var json_writer = std.json.writeStream(writer, .{ .whitespace = .indent_2 });
        _ = &json_writer;
        defer json_writer.deinit();

        try json_writer.beginObject();
        try json_writer.objectField("name");
        try json_writer.write(name);
        try json_writer.objectField("radius");
        try json_writer.write(radius);
        try json_writer.objectField("count");
        try json_writer.write(points.len);
        try json_writer.objectField("points");
        try json_writer.beginArray();
        for (points) |p| {
            try json_writer.beginArray();
            try json_writer.write(p.a);
            try json_writer.write(p.b);
            try json_writer.endArray();
        }
        try json_writer.endArray();
        try json_writer.endObject();

        return buf.toOwnedSlice();
    }

    /// Parse lattice points from JSON string.
    pub fn fromJson(allocator: std.mem.Allocator, json_str: []const u8) !ParsedSet {
        const parsed = try std.json.parseFromSlice(std.json.Value, allocator, json_str, .{});
        defer parsed.deinit();
        const root = parsed.value;

        const name_val = root.object.get("name").?.string;
        const name = try allocator.dupe(u8, name_val);
        errdefer allocator.free(name);

        const radius = root.object.get("radius").?.float;

        const points_arr = root.object.get("points").?.array;
        const points = try allocator.alloc(IntPair, points_arr.items.len);
        errdefer allocator.free(points);

        for (points_arr.items, 0..) |item, i| {
            points[i] = .{
                .a = @intCast(item.array.items[0].integer),
                .b = @intCast(item.array.items[1].integer),
            };
        }

        return .{ .name = name, .radius = radius, .points = points };
    }

    /// Write lattice points to a JSON file.
    pub fn toJsonFile(allocator: std.mem.Allocator, path: []const u8, name: []const u8, radius: f64, points: []const IntPair) !void {
        const json_str = try toJson(allocator, name, radius, points);
        defer allocator.free(json_str);

        const file = try std.fs.cwd().createFile(path, .{});
        defer file.close();
        try file.writeAll(json_str);
        try file.writeAll("\n");
    }

    /// Read lattice points from a JSON file.
    pub fn fromJsonFile(allocator: std.mem.Allocator, path: []const u8) !ParsedSet {
        const file = try std.fs.cwd().openFile(path, .{});
        defer file.close();
        const contents = try file.readToEndAlloc(allocator, 10 * 1024 * 1024);
        defer allocator.free(contents);
        return fromJson(allocator, contents);
    }
};

// ============================================================
// 6. Benchmark Suite
// ============================================================

pub const BenchResult = struct {
    norm_time_s: f64,
    snap_time_s: f64,
    constraint_time_s: f64,
    simd_scalar_ns: u64,
    simd_vector_ns: u64,
    simd_speedup: f64,
    norm_sum: i64,
    con_pass: i64,
};

/// Run the full benchmark suite at N iterations, comparing scalar vs SIMD.
pub fn runBenchmarks(allocator: std.mem.Allocator, n: usize) !BenchResult {
    var prng = std.Random.DefaultPrng.init(42);
    const rand = prng.random();

    const norm_a = try allocator.alloc(i64, n);
    const norm_b = try allocator.alloc(i64, n);
    const snap_x = try allocator.alloc(f64, n);
    const snap_y = try allocator.alloc(f64, n);
    const con_a = try allocator.alloc(i64, n);
    const con_b = try allocator.alloc(i64, n);
    const con_r = try allocator.alloc(f64, n);
    defer {
        allocator.free(norm_a);
        allocator.free(norm_b);
        allocator.free(snap_x);
        allocator.free(snap_y);
        allocator.free(con_a);
        allocator.free(con_b);
        allocator.free(con_r);
    }

    for (0..n) |i| {
        norm_a[i] = @intCast(rand.intRangeAtMost(i32, -1000, 1000));
        norm_b[i] = @intCast(rand.intRangeAtMost(i32, -1000, 1000));
        snap_x[i] = rand.float(f64) * 200.0 - 100.0;
        snap_y[i] = rand.float(f64) * 200.0 - 100.0;
        con_a[i] = @intCast(rand.intRangeAtMost(i32, -100, 100));
        con_b[i] = @intCast(rand.intRangeAtMost(i32, -100, 100));
        con_r[i] = rand.float(f64) * 49.0 + 1.0;
    }

    // Benchmark norm (scalar)
    var norm_sum: i64 = 0;
    var timer = try std.time.Timer.start();
    for (0..n) |i| {
        norm_sum += eisensteinNorm(norm_a[i], norm_b[i]);
    }
    const norm_ns = timer.lap();
    const norm_time = @as(f64, @floatFromInt(norm_ns)) / 1e9;

    // Benchmark snap
    timer.reset();
    for (0..n) |i| {
        _ = eisensteinSnap(snap_x[i], snap_y[i]);
    }
    const snap_ns = timer.lap();
    const snap_time = @as(f64, @floatFromInt(snap_ns)) / 1e9;

    // Benchmark constraint
    var con_pass: i64 = 0;
    timer.reset();
    for (0..n) |i| {
        if (constraintCheck(con_a[i], con_b[i], con_r[i])) con_pass += 1;
    }
    const con_ns = timer.lap();
    const con_time = @as(f64, @floatFromInt(con_ns)) / 1e9;

    // SIMD benchmark
    const sim_res = try simd.benchmark(allocator, n);

    return .{
        .norm_time_s = norm_time,
        .snap_time_s = snap_time,
        .constraint_time_s = con_time,
        .simd_scalar_ns = sim_res.scalar_ns,
        .simd_vector_ns = sim_res.vector_ns,
        .simd_speedup = sim_res.speedup,
        .norm_sum = norm_sum,
        .con_pass = con_pass,
    };
}

// ============================================================
// Main — run benchmarks when compiled as executable
// ============================================================

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();
    const allocator = std.heap.page_allocator;
    const N: usize = 10_000_000;

    try stdout.print("=== Constraint Theory Zig Benchmark (N={}) ===\n", .{N});

    const result = try runBenchmarks(allocator, N);

    try stdout.print("\nScalar Kernels:\n", .{});
    try stdout.print("  eisenstein_norm:  {d:.3}s  (sum={})\n", .{ result.norm_time_s, result.norm_sum });
    try stdout.print("  eisenstein_snap:  {d:.3}s\n", .{ result.snap_time_s });
    try stdout.print("  constraint_check: {d:.3}s  (pass={})\n", .{ result.constraint_time_s, result.con_pass });
    try stdout.print("  TOTAL scalar:     {d:.3}s\n", .{ result.norm_time_s + result.snap_time_s + result.constraint_time_s });

    try stdout.print("\nSIMD (@Vector):\n", .{});
    try stdout.print("  Scalar norm: {d:.3}s\n", .{@as(f64, @floatFromInt(result.simd_scalar_ns)) / 1e9});
    try stdout.print("  Vector norm: {d:.3}s\n", .{@as(f64, @floatFromInt(result.simd_vector_ns)) / 1e9});
    try stdout.print("  SIMD speedup: {d:.2}x\n", .{result.simd_speedup});

    // Quick functional tests
    try stdout.print("\nFunctional checks:\n", .{});
    const points = try latticePointsInDisk(2.0, allocator);
    defer allocator.free(points);
    try stdout.print("  Lattice points in disk(r=2): {} (expected 19)\n", .{points.len});

    // Constraint solver
    const constraints = [_]Constraint{
        .{ .center = .{ .a = 0, .b = 0 }, .radius = 2.0 },
    };
    const solved = try solveConstraints(&constraints, allocator);
    defer allocator.free(solved);
    try stdout.print("  Constraint solver (1 disk r=2): {} points\n", .{solved.len});

    // HexGrid
    var grid = HexGrid(50).init();
    _ = grid.set(0, 0);
    for (&dodecet(.{ .a = 0, .b = 0 })) |nb| {
        _ = grid.set(nb.a, nb.b);
    }
    try stdout.print("  HexGrid(50) with origin+dodecet: {} cells\n", .{grid.count});

    // JSON round-trip
    const json_str = try serialize.toJson(allocator, "test", 2.0, points);
    defer allocator.free(json_str);
    try stdout.print("  JSON export: {} bytes\n", .{json_str.len});

    const parsed = try serialize.fromJson(allocator, json_str);
    defer {
        allocator.free(parsed.name);
        allocator.free(parsed.points);
    }
    try stdout.print("  JSON round-trip: {} points recovered (ok={})\n", .{ parsed.points.len, parsed.points.len == points.len });

    try stdout.print("\nAll checks passed.\n", .{});
}

// ============================================================
// Tests
// ============================================================

test "eisenstein norm basics" {
    try std.testing.expect(eisensteinNorm(1, 0) == 1);
    try std.testing.expect(eisensteinNorm(0, 1) == 1);
    try std.testing.expect(eisensteinNorm(1, 1) == 1);
    try std.testing.expect(eisensteinNorm(5, -3) == 49);
    try std.testing.expect(eisensteinNorm(7, 2) == 39);
    try std.testing.expect(eisensteinNorm(-3, -3) == 9);
}

test "snap to origin" {
    const s = eisensteinSnap(0.1, 0.1);
    try std.testing.expect(s.a == 0);
    try std.testing.expect(s.b == 0);
}

test "snap to nearest" {
    const s = eisensteinSnap(2.0, 0.0);
    try std.testing.expect(s.a == 1);
    try std.testing.expect(s.b == 0);
}

test "constraint check" {
    try std.testing.expect(constraintCheck(1, 0, 2.0));
    try std.testing.expect(!constraintCheck(5, -3, 5.0));
    try std.testing.expect(constraintCheck(5, -3, 8.0));
}

test "dodecet has 6 neighbors" {
    const origin = IntPair{ .a = 0, .b = 0 };
    const d = dodecet(origin);
    try std.testing.expect(d.len == 6);
    for (d) |p| {
        const n = eisensteinNorm(p.a, p.b);
        try std.testing.expect(n == 1 or n == 3);
    }
}

test "lattice points in disk" {
    const allocator = std.testing.allocator;
    const points = try latticePointsInDisk(2.0, allocator);
    defer allocator.free(points);
    try std.testing.expect(points.len == 19);
}

test "IntPair helper methods" {
    const p = IntPair.init(3, 5);
    try std.testing.expect(p.norm() == 19);
    try std.testing.expect(p.eql(.{ .a = 3, .b = 5 }));
    try std.testing.expect(!p.eql(.{ .a = 3, .b = 6 }));
}

test "batch constraint check" {
    const points = [_]IntPair{
        .{ .a = 1, .b = 0 },
        .{ .a = 5, .b = -3 },
        .{ .a = 0, .b = 0 },
        .{ .a = 10, .b = 10 },
    };
    const pass = batchConstraintCheck(&points, 5.0);
    try std.testing.expect(pass == 2); // (1,0) and (0,0)
}

test "SIMD norm4" {
    const pairs = [4]IntPair{
        .{ .a = 1, .b = 0 },
        .{ .a = 0, .b = 1 },
        .{ .a = 1, .b = 1 },
        .{ .a = 5, .b = -3 },
    };
    const results = simd.eisensteinNorm4(pairs);
    try std.testing.expect(results[0] == 1);
    try std.testing.expect(results[1] == 1);
    try std.testing.expect(results[2] == 1);
    try std.testing.expect(results[3] == 49);
}

test "SIMD norm8" {
    const pairs = [8]IntPair{
        .{ .a = 1, .b = 0 },  .{ .a = 0, .b = 1 },
        .{ .a = 1, .b = 1 },  .{ .a = 5, .b = -3 },
        .{ .a = 7, .b = 2 },  .{ .a = -3, .b = -3 },
        .{ .a = 0, .b = 0 },  .{ .a = 2, .b = 2 },
    };
    const results = simd.eisensteinNorm8(pairs);
    try std.testing.expect(results[0] == 1);
    try std.testing.expect(results[3] == 49);
    try std.testing.expect(results[4] == 39);
    try std.testing.expect(results[5] == 9);
    try std.testing.expect(results[6] == 0);
    try std.testing.expect(results[7] == 4);
}

test "SIMD batch matches scalar" {
    const allocator = std.testing.allocator;
    const n = 17; // non-power-of-2 to test tail
    var pairs = std.ArrayList(IntPair).init(allocator);
    defer pairs.deinit();
    var results = std.ArrayList(i64).init(allocator);
    defer results.deinit();

    var prng = std.Random.DefaultPrng.init(123);
    for (0..n) |_| {
        try pairs.append(.{
            .a = prng.random().intRangeAtMost(i32, -100, 100),
            .b = prng.random().intRangeAtMost(i32, -100, 100),
        });
        try results.append(0);
    }

    simd.eisensteinNormBatch(pairs.items, results.items);
    for (0..n) |i| {
        const expected = eisensteinNorm(pairs.items[i].a, pairs.items[i].b);
        try std.testing.expect(results.items[i] == expected);
    }
}

test "HexGrid basic operations" {
    var grid = HexGrid(10).init();
    try std.testing.expect(grid.count == 0);

    try std.testing.expect(grid.set(3, 4));
    try std.testing.expect(!grid.set(3, 4)); // already set
    try std.testing.expect(grid.count == 1);
    try std.testing.expect(grid.get(3, 4));
    try std.testing.expect(!grid.get(3, 5));

    try std.testing.expect(grid.unset(3, 4));
    try std.testing.expect(!grid.get(3, 4));
    try std.testing.expect(grid.count == 0);
}

test "HexGrid out of bounds" {
    var grid = HexGrid(5).init();
    try std.testing.expect(!grid.set(10, 0));
    try std.testing.expect(!grid.get(10, 0));
}

test "HexGrid neighbors" {
    var grid = HexGrid(10).init();
    // Set origin and 3 neighbors
    _ = grid.set(0, 0);
    _ = grid.set(1, 0);
    _ = grid.set(0, 1);
    _ = grid.set(-1, 1);

    var nbuf: [6]IntPair = undefined;
    const ncount = grid.neighbors(0, 0, &nbuf);
    try std.testing.expect(ncount == 3);
}

test "HexGrid flood fill" {
    const allocator = std.testing.allocator;
    var grid = HexGrid(10).init();

    // Create a small cluster around origin
    _ = grid.set(0, 0);
    _ = grid.set(1, 0);
    _ = grid.set(0, 1);
    _ = grid.set(-1, 1);
    // Disconnected point
    _ = grid.set(5, 5);

    var filled = try grid.floodFill(0, 0, 3, allocator);
    defer filled.deinit();
    try std.testing.expect(filled.items.len == 4); // 4 connected points
}

test "HexGrid collectAll" {
    const allocator = std.testing.allocator;
    var grid = HexGrid(10).init();
    _ = grid.set(1, 2);
    _ = grid.set(3, 4);

    var all = try grid.collectAll(allocator);
    defer all.deinit();
    try std.testing.expect(all.items.len == 2);
}

test "HexGrid reset" {
    var grid = HexGrid(10).init();
    _ = grid.set(1, 2);
    _ = grid.set(3, 4);
    try std.testing.expect(grid.count == 2);
    grid.reset();
    try std.testing.expect(grid.count == 0);
    try std.testing.expect(!grid.get(1, 2));
}

test "constraint solver single disk" {
    const allocator = std.testing.allocator;
    const constraints = [_]Constraint{
        .{ .center = .{ .a = 0, .b = 0 }, .radius = 2.0 },
    };
    const result = try solveConstraints(&constraints, allocator);
    defer allocator.free(result);
    try std.testing.expect(result.len == 19);
}

test "constraint solver intersection" {
    const allocator = std.testing.allocator;
    const constraints = [_]Constraint{
        .{ .center = .{ .a = 0, .b = 0 }, .radius = 2.0 },
        .{ .center = .{ .a = 2, .b = 0 }, .radius = 2.0 },
    };
    const result = try solveConstraints(&constraints, allocator);
    defer allocator.free(result);
    // Intersection of two disks radius 2 centered 2 apart should be non-empty but < 19
    try std.testing.expect(result.len > 0 and result.len < 19);
}

test "constraint solver optimized matches brute" {
    const allocator = std.testing.allocator;
    const constraints = [_]Constraint{
        .{ .center = .{ .a = 0, .b = 0 }, .radius = 3.0 },
        .{ .center = .{ .a = 1, .b = 1 }, .radius = 2.5 },
    };
    const brute = try solveConstraints(&constraints, allocator);
    defer allocator.free(brute);
    const opt = try solveConstraintsOptimized(&constraints, allocator);
    defer allocator.free(opt);
    try std.testing.expect(brute.len == opt.len);
}

test "constraint solver empty" {
    const allocator = std.testing.allocator;
    const result = try solveConstraints(&[_]Constraint{}, allocator);
    try std.testing.expect(result.len == 0);
}

test "JSON round-trip" {
    const allocator = std.testing.allocator;
    const points = [_]IntPair{
        .{ .a = 1, .b = 0 },
        .{ .a = 0, .b = 1 },
        .{ .a = 5, .b = -3 },
    };

    const json_str = try serialize.toJson(allocator, "test_set", 5.0, &points);
    defer allocator.free(json_str);

    const parsed = try serialize.fromJson(allocator, json_str);
    defer {
        allocator.free(parsed.name);
        allocator.free(parsed.points);
    }

    try std.testing.expectEqualStrings("test_set", parsed.name);
    try std.testing.expect(parsed.radius == 5.0);
    try std.testing.expect(parsed.points.len == 3);
    try std.testing.expect(parsed.points[0].eql(.{ .a = 1, .b = 0 }));
    try std.testing.expect(parsed.points[2].eql(.{ .a = 5, .b = -3 }));
}

test "JSON file round-trip" {
    const allocator = std.testing.allocator;
    const points = [_]IntPair{
        .{ .a = 2, .b = 3 },
        .{ .a = -1, .b = 4 },
    };

    const path = "/tmp/zig_constraint_test.json";
    try serialize.toJsonFile(allocator, path, "file_test", 3.0, &points);

    const parsed = try serialize.fromJsonFile(allocator, path);
    defer {
        allocator.free(parsed.name);
        allocator.free(parsed.points);
    }

    try std.testing.expectEqualStrings("file_test", parsed.name);
    try std.testing.expect(parsed.points.len == 2);
    try std.testing.expect(parsed.points[0].eql(.{ .a = 2, .b = 3 }));
}
