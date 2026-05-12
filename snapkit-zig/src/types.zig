//! snapkit-zig — shared types used across all modules.
//!
//! Zero dependencies, no hidden allocations, no hidden control flow.

/// An Eisenstein integer a + bω where a, b ∈ Z.
pub const EisensteinInteger = extern struct {
    a: i64,
    b: i64,

    pub fn init(a: i64, b: i64) @This() {
        return .{ .a = a, .b = b };
    }

    /// Convert to Cartesian x coordinate.
    pub fn x(self: @This()) f64 {
        return @as(f64, @floatFromInt(self.a)) - 0.5 * @as(f64, @floatFromInt(self.b));
    }

    /// Convert to Cartesian y coordinate.
    pub fn y(self: @This()) f64 {
        return half_sqrt3 * @as(f64, @floatFromInt(self.b));
    }

    /// Eisenstein norm squared: a² - ab + b². Always ≥ 0.
    pub fn normSquared(self: @This()) i64 {
        return self.a * self.a - self.a * self.b + self.b * self.b;
    }

    /// Euclidean magnitude.
    pub fn abs(self: @This()) f64 {
        return @sqrt(@as(f64, @floatFromInt(self.normSquared())));
    }

    pub fn add(self: @This(), other: @This()) @This() {
        return .{ .a = self.a + other.a, .b = self.b + other.b };
    }

    pub fn sub(self: @This(), other: @This()) @This() {
        return .{ .a = self.a - other.a, .b = self.b - other.b };
    }

    /// Multiply two Eisenstein integers: (a+bω)(c+dω) = (ac−bd) + (ad+bc−bd)ω
    pub fn mul(self: @This(), other: @This()) @This() {
        return .{
            .a = self.a * other.a - self.b * other.b,
            .b = self.a * other.b + self.b * other.a - self.b * other.b,
        };
    }

    /// Galois conjugate: (a+b) − bω
    pub fn conjugate(self: @This()) @This() {
        return .{ .a = self.a + self.b, .b = -self.b };
    }

    pub fn format(self: @This(), comptime fmt: []const u8, options: std.fmt.FormatOptions, writer: anytype) !void {
        _ = fmt;
        _ = options;
        try writer.print("EisensteinInteger({}, {})", .{ self.a, self.b });
    }
};

/// Result of snapping a point to the Eisenstein lattice.
pub const SnapResult = extern struct {
    nearest: EisensteinInteger,
    distance: f64,
    is_snap: bool,
};

/// Result of snapping a timestamp to a beat grid.
pub const TemporalResult = extern struct {
    original_time: f64,
    snapped_time: f64,
    offset: f64,
    is_on_beat: bool,
    is_t_minus_0: bool,
    beat_index: i64,
    beat_phase: f64,
};

/// A periodic beat grid.
pub const BeatGrid = extern struct {
    period: f64,
    phase: f64,
    t_start: f64,
    inv_period: f64,
};

/// Spectral analysis summary.
pub const SpectralSummary = extern struct {
    entropy_bits: f64,
    hurst: f64,
    autocorr_lag1: f64,
    autocorr_decay: f64,
    is_stationary: bool,
};

// ── Precomputed constants ──

pub const sqrt3: f64 = 1.7320508075688772;
pub const inv_sqrt3: f64 = 0.5773502691896258;
pub const half_sqrt3: f64 = 0.8660254037844386;
pub const covering_radius: f64 = inv_sqrt3; // 1/√3 guaranteed

const std = @import("std");
