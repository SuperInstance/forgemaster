//! Spectral analysis — entropy, Hurst R/S exponent, autocorrelation.
//!
//! No hidden allocations. All scratch buffers provided by the caller.

const std = @import("std");
const types = @import("types.zig");
const SpectralSummary = types.SpectralSummary;

/// Shannon entropy via histogram binning.
/// `counts` must be a slice of length `bins`.
pub fn entropy(data: []const f64, bins: usize, counts: []usize) f64 {
    const n = data.len;
    if (n < 2 or bins < 1) return 0.0;

    // Find min/max
    var min_val = data[0];
    var max_val = data[0];
    for (data[1..]) |x| {
        if (x < min_val) min_val = x;
        if (x > max_val) max_val = x;
    }
    if (max_val == min_val) return 0.0;

    const inv_range = @as(f64, @floatFromInt(bins)) / (max_val - min_val);

    // Zero counts
    @memset(counts[0..bins], 0);

    for (data) |x| {
        var idx: usize = @intFromFloat((x - min_val) * inv_range);
        if (idx >= bins) idx = bins - 1;
        counts[idx] += 1;
    }

    const inv_n = 1.0 / @as(f64, @floatFromInt(n));
    const inv_log2 = 1.0 / @log(2.0);
    var h: f64 = 0.0;
    for (counts[0..bins]) |c| {
        if (c > 0) {
            const p = @as(f64, @floatFromInt(c)) * inv_n;
            h -= p * @log(p) * inv_log2;
        }
    }
    return h;
}

/// Normalized autocorrelation.
/// `out` must have length at least max_lag + 1.
/// Returns the number of lags written.
pub fn autocorrelation(data: []const f64, max_lag: usize, out: []f64) usize {
    const n = data.len;
    if (n < 2) {
        if (out.len > 0) out[0] = 1.0;
        return 1;
    }

    const effective_lag = @min(max_lag, n - 1);
    if (out.len < effective_lag + 1) return 0;

    const inv_n = 1.0 / @as(f64, @floatFromInt(n));

    // Compute mean
    var mean: f64 = 0.0;
    for (data) |x| mean += x;
    mean *= inv_n;

    // Compute variance (r0)
    var r0: f64 = 0.0;
    for (data) |x| {
        const d = x - mean;
        r0 += d * d;
    }
    r0 *= inv_n;

    if (r0 == 0.0) {
        out[0] = 1.0;
        for (out[1 .. effective_lag + 1]) |*o| o.* = 0.0;
        return effective_lag + 1;
    }

    const inv_r0 = 1.0 / r0;

    for (0..effective_lag + 1) |lag| {
        var rk: f64 = 0.0;
        const limit = n - lag;
        for (0..limit) |t| {
            const d1 = data[t] - mean;
            const d2 = data[t + lag] - mean;
            rk += d1 * d2;
        }
        out[lag] = rk * inv_n * inv_r0;
    }
    return effective_lag + 1;
}

/// Hurst exponent via R/S analysis.
pub fn hurstExponent(data: []const f64) f64 {
    const n = data.len;
    if (n < 20) return 0.5;

    const inv_n = 1.0 / @as(f64, @floatFromInt(n));

    // Compute mean
    var mean: f64 = 0.0;
    for (data) |x| mean += x;
    mean *= inv_n;

    // We need centered data — use an allocator-free approach:
    // Process subseries directly from the original data, subtracting sub_mean.
    // This avoids allocating a centered array.

    // Build geometric progression of test sizes
    var test_sizes: [32]usize = undefined;
    var n_sizes: usize = 0;
    var s: usize = 16;
    while (s <= n / 2 and n_sizes < 32) {
        test_sizes[n_sizes] = s;
        n_sizes += 1;
        const next = s * 2;
        s = if (next <= n / 2) next else @intFromFloat(@as(f64, @floatFromInt(s)) * 1.5);
        if (s <= test_sizes[n_sizes - 1]) break;
    }
    if (n_sizes == 0 and n >= 8) {
        test_sizes[0] = n / 4;
        n_sizes = 1;
    }

    var log_sizes: [32]f64 = undefined;
    var log_rs: [32]f64 = undefined;
    var n_pts: usize = 0;

    for (test_sizes[0..n_sizes]) |size| {
        if (size < 4 or size > n) continue;

        const num_sub = n / size;
        if (num_sub < 1) continue;

        const inv_size = 1.0 / @as(f64, @floatFromInt(size));
        var rs_sum: f64 = 0.0;
        var rs_count: usize = 0;

        for (0..num_sub) |i| {
            const start = i * size;
            const sub = data[start .. start + size];

            // Compute sub-mean
            var sub_mean: f64 = 0.0;
            for (sub) |x| sub_mean += x;
            sub_mean *= inv_size;

            // Cumulative deviations with min/max tracking
            var running: f64 = 0.0;
            var cum_min: f64 = 0.0;
            var cum_max: f64 = 0.0;
            for (sub) |x| {
                running += x - sub_mean;
                if (running < cum_min) cum_min = running;
                if (running > cum_max) cum_max = running;
            }
            const R = cum_max - cum_min;

            // Variance
            var var_val: f64 = 0.0;
            for (sub) |x| {
                const d = x - sub_mean;
                var_val += d * d;
            }
            var_val *= inv_size;

            if (var_val > 1e-20) {
                rs_sum += R / @sqrt(var_val);
                rs_count += 1;
            }
        }

        if (rs_count > 0) {
            const avg_rs = rs_sum / @as(f64, @floatFromInt(rs_count));
            if (avg_rs > 0.0) {
                log_sizes[n_pts] = @log(@as(f64, @floatFromInt(size)));
                log_rs[n_pts] = @log(avg_rs);
                n_pts += 1;
            }
        }
    }

    if (n_pts < 2) return 0.5;

    // Linear regression on log-log
    var sx: f64 = 0.0;
    var sy: f64 = 0.0;
    var sxy: f64 = 0.0;
    var sx2: f64 = 0.0;
    for (0..n_pts) |i| {
        const lx = log_sizes[i];
        const ly = log_rs[i];
        sx += lx;
        sy += ly;
        sxy += lx * ly;
        sx2 += lx * lx;
    }

    const n_pts_f = @as(f64, @floatFromInt(n_pts));
    const denom = n_pts_f * sx2 - sx * sx;
    if (denom == 0.0) return 0.5;

    var h = (n_pts_f * sxy - sx * sy) / denom;
    if (h < 0.0) h = 0.0;
    if (h > 1.0) h = 1.0;
    return h;
}

/// Full spectral summary of a signal.
/// `acf_buf` must be length at least max_lag + 1.
/// `counts_buf` must be length at least bins.
pub fn spectralSummary(
    data: []const f64,
    bins: usize,
    max_lag: usize,
    acf_buf: []f64,
    counts_buf: []usize,
) SpectralSummary {
    const h = entropy(data, bins, counts_buf);
    const hurst_val = hurstExponent(data);

    const effective_lag = if (max_lag > 0) max_lag else data.len / 2;
    const acf_len = autocorrelation(data, effective_lag, acf_buf);

    const acf_lag1: f64 = if (acf_len > 1) acf_buf[1] else 0.0;

    // Find decay lag (where |acf| < 1/e)
    const threshold: f64 = 0.36787944117144233; // 1/e
    var decay_lag: f64 = @as(f64, @floatFromInt(acf_len));
    for (1..acf_len) |i| {
        if (@abs(acf_buf[i]) < threshold) {
            decay_lag = @as(f64, @floatFromInt(i));
            break;
        }
    }

    const is_stationary = (hurst_val >= 0.4 and hurst_val <= 0.6) and @abs(acf_lag1) < 0.3;

    return .{
        .entropy_bits = h,
        .hurst = hurst_val,
        .autocorr_lag1 = acf_lag1,
        .autocorr_decay = decay_lag,
        .is_stationary = is_stationary,
    };
}

// ── C-compatible exports ──

export fn sk_entropy(data: [*]const f64, n: usize, bins: usize) f64 {
    // Use a static buffer for small bin counts
    var counts_buf: [256]usize = undefined;
    const effective_bins = @min(bins, 256);
    return entropy(data[0..n], effective_bins, &counts_buf);
}

export fn sk_hurst_exponent(data: [*]const f64, n: usize) f64 {
    return hurstExponent(data[0..n]);
}

// ── Tests ──

test "entropy — constant signal" {
    const data = [_]f64{ 1.0, 1.0, 1.0, 1.0 };
    var counts: [10]usize = undefined;
    const h = entropy(&data, 10, &counts);
    try std.testing.expectApproxEqAbs(@as(f64, 0.0), h, 1e-10);
}

test "entropy — uniform signal" {
    // With 10 bins and 10 uniformly spaced points, entropy ≈ log2(10)
    const data = [_]f64{ 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0 };
    var counts: [10]usize = undefined;
    const h = entropy(&data, 10, &counts);
    try std.testing.expect(h > 3.0); // log2(10) ≈ 3.32
}

test "autocorrelation — lag 0 is 1.0" {
    const data = [_]f64{ 1.0, 2.0, 3.0, 4.0, 5.0 };
    var acf: [5]f64 = undefined;
    const len = autocorrelation(&data, 4, &acf);
    try std.testing.expectEqual(@as(usize, 5), len);
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), acf[0], 1e-10);
}

test "autocorrelation — constant signal" {
    const data = [_]f64{ 5.0, 5.0, 5.0, 5.0 };
    var acf: [4]f64 = undefined;
    const len = autocorrelation(&data, 3, &acf);
    try std.testing.expectEqual(@as(usize, 4), len);
    try std.testing.expectApproxEqAbs(@as(f64, 1.0), acf[0], 1e-10);
    // All other lags should be 0 for constant signal
    for (acf[1..len]) |val| {
        try std.testing.expectApproxEqAbs(@as(f64, 0.0), val, 1e-10);
    }
}

test "Hurst exponent — returns 0.5 for small data" {
    const data = [_]f64{ 1.0, 2.0, 3.0 };
    const h = hurstExponent(&data);
    try std.testing.expectEqual(@as(f64, 0.5), h);
}

test "Hurst exponent — reasonable range for random-ish data" {
    // Generate a simple sequence
    var data: [100]f64 = undefined;
    for (&data, 0..) |*d, i| {
        d.* = @sin(@as(f64, @floatFromInt(i)) * 0.1);
    }
    const h = hurstExponent(&data);
    try std.testing.expect(h >= 0.0 and h <= 1.0);
}

test "spectral summary — basic" {
    var data: [100]f64 = undefined;
    for (&data, 0..) |*d, i| {
        d.* = @sin(@as(f64, @floatFromInt(i)) * 0.3);
    }
    var acf_buf: [50]f64 = undefined;
    var counts: [10]usize = undefined;
    const summary = spectralSummary(&data, 10, 25, &acf_buf, &counts);
    try std.testing.expect(summary.entropy_bits >= 0.0);
    try std.testing.expect(summary.hurst >= 0.0 and summary.hurst <= 1.0);
    try std.testing.expect(summary.autocorr_decay >= 0.0);
}
