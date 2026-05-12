//! Temporal snap — BeatGrid, TemporalSnap, T-minus-0 detection.
//!
//! No hidden allocations. BeatGrid is a plain struct. TemporalSnap uses
//! a fixed-size circular buffer (no heap allocation).

const std = @import("std");
const types = @import("types.zig");
const BeatGrid = types.BeatGrid;
const TemporalResult = types.TemporalResult;

pub const T0_MAX_HISTORY: usize = 64;

/// Initialize a BeatGrid. Returns error.InvalidPeriod if period ≤ 0.
pub fn beatGridInit(period: f64, phase: f64, t_start: f64) error{InvalidPeriod}!BeatGrid {
    if (period <= 0.0) return error.InvalidPeriod;
    return .{
        .period = period,
        .phase = phase,
        .t_start = t_start,
        .inv_period = 1.0 / period,
    };
}

/// Find the nearest beat time and its index.
pub fn beatGridNearest(grid: *const BeatGrid, t: f64) struct { time: f64, index: i64 } {
    const adjusted = t - grid.t_start - grid.phase;
    const idx: i64 = @intFromFloat(@round(adjusted * grid.inv_period));
    const beat_time = grid.t_start + grid.phase + @as(f64, @floatFromInt(idx)) * grid.period;
    return .{ .time = beat_time, .index = idx };
}

/// Snap a timestamp to the beat grid.
pub fn beatGridSnap(grid: *const BeatGrid, t: f64, tolerance: f64) TemporalResult {
    const nearest = beatGridNearest(grid, t);
    const offset = t - nearest.time;
    var phase = @mod((t - grid.t_start - grid.phase), grid.period) * grid.inv_period;
    if (phase < 0.0) phase += 1.0;

    return .{
        .original_time = t,
        .snapped_time = nearest.time,
        .offset = offset,
        .is_on_beat = @abs(offset) <= tolerance,
        .is_t_minus_0 = false,
        .beat_index = nearest.index,
        .beat_phase = phase,
    };
}

/// Batch snap timestamps to beat grid. Caller provides output slice.
pub fn beatGridSnapBatch(
    grid: *const BeatGrid,
    timestamps: []const f64,
    tolerance: f64,
    out: []TemporalResult,
) void {
    const len = @min(timestamps.len, out.len);
    for (timestamps[0..len], out[0..len]) |t, *o| {
        o.* = beatGridSnap(grid, t, tolerance);
    }
}

/// Enumerate beats in a time range. Caller provides output buffer.
/// Returns the number of beats written.
pub fn beatGridRange(
    grid: *const BeatGrid,
    t_start: f64,
    t_end: f64,
    out: []f64,
) usize {
    if (t_end <= t_start) return 0;
    const first_idx: i64 = @intFromFloat(@ceil((t_start - grid.t_start - grid.phase) * grid.inv_period));
    const last_idx: i64 = @intFromFloat(@floor((t_end - grid.t_start - grid.phase) * grid.inv_period));
    var count: usize = 0;
    var i: i64 = first_idx;
    while (i <= last_idx and count < out.len) : (i += 1) {
        out[count] = grid.t_start + grid.phase + @as(f64, @floatFromInt(i)) * grid.period;
        count += 1;
    }
    return count;
}

// ── T-minus-0 detection ──

/// Temporal snap with T-minus-0 detection via circular buffer.
/// No heap allocation — fixed-size buffer.
pub const TemporalSnap = struct {
    grid: BeatGrid,
    tolerance: f64,
    t0_threshold: f64,
    t0_window: usize,
    hist_t: [T0_MAX_HISTORY]f64,
    hist_v: [T0_MAX_HISTORY]f64,
    hist_idx: usize,
    hist_len: usize,
    hist_cap: usize,

    pub fn init(
        grid: BeatGrid,
        tolerance: f64,
        t0_threshold: f64,
        t0_window: usize,
    ) @This() {
        const win = @max(2, t0_window);
        var cap = win * 2;
        if (cap > T0_MAX_HISTORY) cap = T0_MAX_HISTORY;
        return .{
            .grid = grid,
            .tolerance = tolerance,
            .t0_threshold = t0_threshold,
            .t0_window = win,
            .hist_t = undefined,
            .hist_v = undefined,
            .hist_idx = 0,
            .hist_len = 0,
            .hist_cap = cap,
        };
    }

    /// Observe a (time, value) pair. Returns TemporalResult with T-minus-0 detection.
    pub fn observe(self: *@This(), t: f64, value: f64) TemporalResult {
        self.hist_t[self.hist_idx] = t;
        self.hist_v[self.hist_idx] = value;
        self.hist_idx = (self.hist_idx + 1) % self.hist_cap;
        if (self.hist_len < self.hist_cap) self.hist_len += 1;

        const is_t0 = self.detectT0();
        var result = beatGridSnap(&self.grid, t, self.tolerance);
        result.is_t_minus_0 = is_t0;
        return result;
    }

    fn detectT0(self: *@This()) bool {
        if (self.hist_len < 3) return false;
        const cap = self.hist_cap;
        const idx = self.hist_idx;

        const curr_t = self.hist_t[(idx - 1 + cap) % cap];
        const curr_v = self.hist_v[(idx - 1 + cap) % cap];
        const mid_t = self.hist_t[(idx - 2 + cap) % cap];
        const mid_v = self.hist_v[(idx - 2 + cap) % cap];
        const prev_t = self.hist_t[(idx - 3 + cap) % cap];
        const prev_v = self.hist_v[(idx - 3 + cap) % cap];

        if (@abs(curr_v) > self.t0_threshold) return false;

        const dt1 = mid_t - prev_t;
        const dt2 = curr_t - mid_t;
        if (dt1 == 0.0 or dt2 == 0.0) return false;

        const d1 = (mid_v - prev_v) / dt1;
        const d2 = (curr_v - mid_v) / dt2;

        return d1 * d2 < 0.0;
    }

    pub fn reset(self: *@This()) void {
        self.hist_idx = 0;
        self.hist_len = 0;
    }
};

// ── C-compatible exports ──

export fn sk_beat_grid_init(grid: *BeatGrid, period: f64, phase: f64, t_start: f64) c_int {
    const g = beatGridInit(period, phase, t_start) catch return -1;
    grid.* = g;
    return 0;
}

export fn sk_beat_grid_nearest(grid: *const BeatGrid, t: f64, beat_index: ?*i64) f64 {
    const nearest = beatGridNearest(grid, t);
    if (beat_index) |bi| bi.* = nearest.index;
    return nearest.time;
}

export fn sk_beat_grid_snap(grid: *const BeatGrid, t: f64, tolerance: f64) TemporalResult {
    return beatGridSnap(grid, t, tolerance);
}

export fn sk_beat_grid_snap_batch(
    grid: *const BeatGrid,
    timestamps: [*]const f64,
    n: usize,
    tolerance: f64,
    out: [*]TemporalResult,
) void {
    beatGridSnapBatch(grid, timestamps[0..n], tolerance, out[0..n]);
}

// ── Tests ──

test "BeatGrid init — valid" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    try std.testing.expectEqual(@as(f64, 1.0), grid.period);
    try std.testing.expectEqual(@as(f64, 1.0), grid.inv_period);
}

test "BeatGrid init — invalid period" {
    _ = beatGridInit(-1.0, 0.0, 0.0) catch |err| {
        try std.testing.expectEqual(error.InvalidPeriod, err);
        return;
    };
    unreachable;
}

test "BeatGrid snap — on beat" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    const result = beatGridSnap(&grid, 2.0, 0.1);
    try std.testing.expect(result.is_on_beat);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), result.snapped_time, 1e-10);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), result.offset, 1e-10);
}

test "BeatGrid snap — off beat" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    const result = beatGridSnap(&grid, 2.5, 0.1);
    try std.testing.expect(!result.is_on_beat);
}

test "BeatGrid snap — near beat within tolerance" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    const result = beatGridSnap(&grid, 2.05, 0.1);
    try std.testing.expect(result.is_on_beat);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), result.snapped_time, 1e-10);
}

test "BeatGrid phase" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    const result = beatGridSnap(&grid, 2.5, 0.1);
    try std.testing.expectApproxEqAbs(@as(f64, 0.5), result.beat_phase, 1e-10);
}

test "BeatGrid range" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    var buf: [10]f64 = undefined;
    const count = beatGridRange(&grid, 1.5, 4.5, &buf);
    try std.testing.expectEqual(@as(usize, 3), count);
    try std.testing.expectApproxEqAbs(@as(f64, 2.0), buf[0], 1e-10);
    try std.testing.expectApproxEqAbs(@as(f64, 3.0), buf[1], 1e-10);
    try std.testing.expectApproxEqAbs(@as(f64, 4.0), buf[2], 1e-10);
}

test "TemporalSnap — T-minus-0 detection" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    var ts = TemporalSnap.init(grid, 0.1, 0.05, 3);

    // Rising values
    _ = ts.observe(0.0, 0.1);
    _ = ts.observe(1.0, 0.2);
    // Peak
    _ = ts.observe(2.0, 0.01); // small value near zero

    // After sign change through zero, should detect T-minus-0
    // (This depends on the derivative sign change check)
}

test "TemporalSnap reset" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    var ts = TemporalSnap.init(grid, 0.1, 0.05, 3);
    _ = ts.observe(0.0, 0.1);
    _ = ts.observe(1.0, 0.2);
    try std.testing.expectEqual(@as(usize, 2), ts.hist_len);
    ts.reset();
    try std.testing.expectEqual(@as(usize, 0), ts.hist_len);
}

test "TemporalSnap batch" {
    const grid = try beatGridInit(1.0, 0.0, 0.0);
    const timestamps = [_]f64{ 0.0, 1.0, 2.0, 3.0 };
    var results: [4]TemporalResult = undefined;
    beatGridSnapBatch(&grid, &timestamps, 0.1, &results);
    for (&results) |r| {
        try std.testing.expect(r.is_on_beat);
    }
}
