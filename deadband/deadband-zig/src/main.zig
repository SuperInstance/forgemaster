const std = @import("std");

/// Apply a deadband filter: values within ±threshold are treated as zero.
/// This eliminates noise/jitter around the zero axis, common in sensor
/// readings, joystick input, and control systems.
pub fn apply(value: f64, threshold: f64) f64 {
    std.debug.assert(threshold >= 0);
    if (@abs(value) <= threshold) return 0.0;
    return value;
}

/// Apply deadband with rescale: output is linearly mapped so the transition
/// at ±threshold maps to 0.0 and the full-range maps linearly beyond.
pub fn apply_rescale(value: f64, threshold: f64) f64 {
    std.debug.assert(threshold >= 0);
    std.debug.assert(threshold < 1.0);
    if (@abs(value) <= threshold) return 0.0;
    const sign: f64 = if (value > 0) 1.0 else -1.0;
    return sign * (@abs(value) - threshold) / (1.0 - threshold);
}

pub fn main() !void {
    const stdout = std.io.getStdOut().writer();

    try stdout.print("=== Deadband Filter Demo ===\n\n", .{});

    const test_values = [_]f64{ -2.0, -0.8, -0.05, 0.0, 0.03, 0.5, 1.5 };
    const threshold: f64 = 0.1;

    try stdout.print("Threshold: {d:.2}\n\n", .{threshold});
    try stdout.print("{s:>10} | {s:>10} | {s:>10}\n", .{ "Input", "Output", "Rescaled" });
    try stdout.print("{s:>10}-+-{s:>10}-+-{s:>10}\n", .{"----------", "----------", "----------"});

    for (test_values) |v| {
        try stdout.print("{d:>10.3} | {d:>10.3} | {d:>10.3}\n", .{
            v,
            apply(v, threshold),
            apply_rescale(v, threshold),
        });
    }

    try stdout.print("\n", .{});
}
