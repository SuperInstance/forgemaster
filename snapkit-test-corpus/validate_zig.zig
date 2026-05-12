//! Validate snapkit-zig implementation against the test corpus.
//! Build: zig build (with build.zig) or zig run validate_zig.zig
//! Note: Requires a JSON reader. This uses a simple hand-rolled parser.

const std = @import("std");
const math = std.math;

const SQRT3: f64 = 1.7320508075688772;

fn snapError(x: f64, y: f64, a: i32, b: i32) f64 {
    const lx = @as(f64, @floatFromInt(a)) - @as(f64, @floatFromInt(b)) / 2.0;
    const ly = @as(f64, @floatFromInt(b)) * SQRT3 / 2.0;
    return math.sqrt((x - lx) * (x - lx) + (y - ly) * (y - ly));
}

fn eisensteinSnap(x: f64, y: f64) [2]i32 {
    const b_float = 2.0 * y / SQRT3;
    const a_float = x + y / SQRT3;

    const a_lo: i32 = @intFromFloat(@floor(a_float));
    const b_lo: i32 = @intFromFloat(@floor(b_float));

    var best_a: i32 = 0;
    var best_b: i32 = 0;
    var best_err: f64 = math.floatMax(f64);

    // Check 4 floor/ceil candidates
    for ([_]i32{ 0, 1 }) |da| {
        for ([_]i32{ 0, 1 }) |db| {
            const ca = a_lo + da;
            const cb = b_lo + db;
            const err = snapError(x, y, ca, cb);
            if (err < best_err - 1e-15) {
                best_a = ca;
                best_b = cb;
                best_err = err;
            } else if (@abs(err - best_err) < 1e-15) {
                if (ca < best_a or (ca == best_a and cb < best_b)) {
                    best_a = ca;
                    best_b = cb;
                }
            }
        }
    }

    // Check ±1 neighborhood
    for ([_]i32{ -1, 0, 1 }) |da| {
        for ([_]i32{ -1, 0, 1 }) |db| {
            const ca = best_a + da;
            const cb = best_b + db;
            const err = snapError(x, y, ca, cb);
            if (err < best_err - 1e-15) {
                best_a = ca;
                best_b = cb;
                best_err = err;
            } else if (@abs(err - best_err) < 1e-15) {
                if (ca < best_a or (ca == best_a and cb < best_b)) {
                    best_a = ca;
                    best_b = cb;
                }
            }
        }
    }

    return .{ best_a, best_b };
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const allocator = gpa.allocator();

    const cwd = std.fs.cwd();
    const data = try cwd.readFileAlloc(allocator, "corpus/snap_corpus.json", 50_000_000);
    defer allocator.free(data);

    var passed: u32 = 0;
    var failed: u32 = 0;
    var errors = std.ArrayList([]const u8).init(allocator);
    defer errors.deinit();

    // Simple JSON array-of-objects parser
    var i: usize = 0;
    while (i < data.len) : (i += 1) {
        // Find "id":
        const id_tag = "\"id\":";
        const id_pos = std.mem.indexOfPos(u8, data, i, id_tag) orelse break;
        i = id_pos + id_tag.len;

        const id_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const case_id = std.fmt.parseInt(u32, std.mem.trim(u8, data[i..id_end], " \t\n"), 10) catch continue;
        i = id_end;

        // Find x:
        const x_tag = "\"x\":";
        const x_pos = std.mem.indexOfPos(u8, data, i, x_tag) orelse break;
        i = x_pos + x_tag.len;
        const x_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const x_val = std.fmt.parseFloat(f64, std.mem.trim(u8, data[i..x_end], " \t\n")) catch continue;
        i = x_end;

        // Find y:
        const y_tag = "\"y\":";
        const y_pos = std.mem.indexOfPos(u8, data, i, y_tag) orelse break;
        i = y_pos + y_tag.len;
        const y_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const y_val = std.fmt.parseFloat(f64, std.mem.trim(u8, data[i..y_end], " \t\n")) catch continue;
        i = y_end;

        // Find expected a:
        const exp_tag = "\"expected\"";
        const exp_pos = std.mem.indexOfPos(u8, data, i, exp_tag) orelse break;
        i = exp_pos + exp_tag.len;
        const ea_tag = "\"a\":";
        const ea_pos = std.mem.indexOfPos(u8, data, i, ea_tag) orelse break;
        i = ea_pos + ea_tag.len;
        const ea_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const exp_a = std.fmt.parseInt(i32, std.mem.trim(u8, data[i..ea_end], " \t\n"), 10) catch continue;
        i = ea_end;

        // Find expected b:
        const eb_tag = "\"b\":";
        const eb_pos = std.mem.indexOfPos(u8, data, i, eb_tag) orelse break;
        i = eb_pos + eb_tag.len;
        const eb_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const exp_b = std.fmt.parseInt(i32, std.mem.trim(u8, data[i..eb_end], " \t\n"), 10) catch continue;
        i = eb_end;

        // Find snap_error_max:
        const sem_tag = "\"snap_error_max\":";
        const sem_pos = std.mem.indexOfPos(u8, data, i, sem_tag) orelse break;
        i = sem_pos + sem_tag.len;
        const sem_end = std.mem.indexOfAnyPos(u8, data, i, ",}") orelse break;
        const err_max = std.fmt.parseFloat(f64, std.mem.trim(u8, data[i..sem_end], " \t\n")) catch continue;
        i = sem_end;

        // Run snap
        const result = eisensteinSnap(x_val, y_val);
        const a = result[0];
        const b = result[1];
        const err = snapError(x_val, y_val, a, b);

        var ok = true;
        if (a != exp_a) {
            try errors.append(std.fmt.allocPrint(allocator, "Case {d}: a={d}, expected={d}", .{ case_id, a, exp_a }) catch "error");
            ok = false;
        }
        if (b != exp_b) {
            try errors.append(std.fmt.allocPrint(allocator, "Case {d}: b={d}, expected={d}", .{ case_id, b, exp_b }) catch "error");
            ok = false;
        }
        if (err > err_max + 1e-10) {
            try errors.append(std.fmt.allocPrint(allocator, "Case {d}: snap_error={d} > max={d}", .{ case_id, err, err_max }) catch "error");
            ok = false;
        }

        if (ok) passed += 1 else failed += 1;
    }

    const total = passed + failed;
    const stdout = std.io.getStdOut().writer();
    try stdout.print("Results: {d}/{d} passed, {d} failed\n", .{ passed, total, failed });

    if (errors.items.len > 0) {
        for (errors.items[0..@min(errors.items.len, 20)]) |e| {
            try stdout.print("  {s}\n", .{e});
        }
        std.process.exit(1);
    } else {
        try stdout.print("All cases passed ✓\n", .{});
    }
}
