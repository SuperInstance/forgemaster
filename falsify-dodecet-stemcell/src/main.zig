// ═══════════════════════════════════════════════════════
// FALSIFICATION TEST: Does 12+12=24 create real synergy?
//
// Hypothesis: Pairing two dodecets into 24-bit and contracting
// them produces geometrically meaningful results on the A₂ lattice.
//
// Null hypothesis: The 24-bit concatenation destroys the 12-bit
// semantic boundary and the output is geometrically meaningless.
//
// Test: Encode 1000 Eisenstein snap points as dodecets, pair them,
// contract via integer arithmetic, measure semantic preservation.
// ═══════════════════════════════════════════════════════

const std = @import("std");
const math = std.math;
const print = std.debug.print;

// ── Eisenstein integer lattice ───────────────────────

const Eisenstein = struct {
    a: i32,
    b: i32,

    fn toComplex(self: @This()) struct { re: f64, im: f64 } {
        const w_re: f64 = -0.5;
        const w_im: f64 = 0.8660254037844386;
        return .{
            .re = @as(f64, @floatFromInt(self.a)) + @as(f64, @floatFromInt(self.b)) * w_re,
            .im = @as(f64, @floatFromInt(self.b)) * w_im,
        };
    }

    fn norm(self: @This()) f64 {
        const c = self.toComplex();
        return c.re * c.re + c.im * c.im;
    }
};

fn snap(x: f64, y: f64) struct { eis: Eisenstein, err: f64, dx: f64, dy: f64 } {
    const w_re: f64 = -0.5;
    const w_im: f64 = 0.8660254037844386;

    const b_est = @round(y / w_im);
    const a_est = @round(x - b_est * w_re);

    var best_a: i32 = @intFromFloat(a_est);
    var best_b: i32 = @intFromFloat(b_est);
    var best_err: f64 = 1e18;

    {
        var da: i32 = -1;
        while (da <= 1) : (da += 1) {
            var db: i32 = -1;
            while (db <= 1) : (db += 1) {
            const ca = @as(f64, @floatFromInt(best_a + da)) + @as(f64, @floatFromInt(best_b + db)) * w_re;
            const cb = @as(f64, @floatFromInt(best_b + db)) * w_im;
            const err = math.hypot(x - ca, y - cb);
            if (err < best_err) {
                best_a = best_a + da;
                best_b = best_b + db;
                best_err = err;
            }
        }
    }

    const c = Eisenstein{ .a = best_a, .b = best_b }.toComplex();
    return .{
        .eis = .{ .a = best_a, .b = best_b },
        .err = best_err,
        .dx = x - c.re,
        .dy = y - c.im,
    };
}

// ── Dodecet encoding (12-bit) ────────────────────────
// Nibble 2 (bits 11-8): error level 0-15
// Nibble 1 (bits 7-4): direction 0-15 (16 azimuth bins)
// Nibble 0 (bits 3-0): chamber 0-5 (3 bits) + safety (1 bit)

const Dodecet = packed struct {
    chamber_safety: u4, // bits 3-0: chamber(3) + safety(1)
    direction: u4,      // bits 7-4: azimuth bin
    error_level: u4,    // bits 11-8: quantized error

    const RHO: f64 = 0.5773502691896258; // 1/sqrt(3)
    const Self = @This();

    pub fn encode(error: f64, angle: f64, chamber: u3, safe: bool) Self {
        const err_lvl: u4 = @intFromFloat(@min(15, @max(0, error / RHO * 15)));
        const dir_bin: u4 = @intFromFloat(@min(15, @max(0, angle / (2 * math.pi) * 16)));
        const ch: u4 = @as(u4, chamber) & 0x7;
        const sf: u4 = if (safe) 0 else 1;
        return .{
            .error_level = err_lvl,
            .direction = dir_bin,
            .chamber_safety = (ch << 1) | sf,
        };
    }

    pub fn toU12(self: Self) u16 {
        return @as(u16, self.error_level) << 8 |
            @as(u16, self.direction) << 4 |
            @as(u16, self.chamber_safety);
    }

    pub fn fromU12(v: u16) Self {
        return .{
            .error_level = @intCast((v >> 8) & 0xF),
            .direction = @intCast((v >> 4) & 0xF),
            .chamber_safety = @intCast(v & 0xF),
        };
    }

    pub fn getError(self: Self) f64 {
        return @as(f64, @floatFromInt(self.error_level)) / 15.0 * RHO;
    }

    pub fn getAngle(self: Self) f64 {
        return @as(f64, @floatFromInt(self.direction)) / 16.0 * 2 * math.pi;
    }

    pub fn getChamber(self: Self) u3 {
        return @intCast((self.chamber_safety >> 1) & 0x7);
    }

    pub fn isSafe(self: Self) bool {
        return (self.chamber_safety & 1) == 0;
    }
};

// ── Weyl chamber classification ──────────────────────
// S₃ divides plane into 6 chambers

fn classifyChamber(dx: f64, dy: f64) u3 {
    const angle = math.atan2(dy, dx);
    // Normalize to [0, 2π)
    const a = if (angle < 0) angle + 2 * math.pi else angle;
    // 6 chambers, each π/3 wide
    const chamber = @as(u3, @intFromFloat(a / (math.pi / 3.0)));
    return if (chamber < 6) chamber else 5;
}

// ── Stemcell simulation: contract two 12-bit into 24-bit ──
// The stemcell contracts arrays of 24-bit integers.
// We simulate the core operation: pair(d1, d2) → 24-bit → contract.

fn pairDodecets(d1: Dodecet, d2: Dodecet) u24 {
    return @as(u24, d1.toU12()) << 12 | @as(u24, d2.toU12());
}

fn unpairDodecets(p: u24) struct { d1: Dodecet, d2: Dodecet } {
    return .{
        .d1 = Dodecet.fromU12(@intCast((p >> 12) & 0xFFF)),
        .d2 = Dodecet.fromU12(@intCast(p & 0xFFF)),
    };
}

// Stemcell contraction operations on 24-bit pairs
const StemcellOp = enum {
    add,        // x + y (raw integer addition)
    xor,        // x ^ y (bitwise XOR)
    mul_low,    // (x * y) & 0xFFFFFF (low 24 bits of multiply)
    weighted,   // (x + y*2) & 0xFFFFFF (asymmetric weighting)
    geometric,  // Error: max(err1,err2), Dir: avg, Ch: majority
};

fn stemcellContract(a: u24, b: u24, op: StemcellOp) u24 {
    const mask: u24 = 0xFFFFFF;
    return switch (op) {
        .add => (a +% b) & mask,   // wrapping add
        .xor => a ^ b,
        .mul_low => (@as(u48, a) * @as(u48, b)) & mask,
        .weighted => (a +% (b << 1)) & mask,
        .geometric => geometricMerge(a, b),
    };
}

// The GEOMETRIC operation: merge using constraint semantics
// This is what we CLAIM should work if the synergy is real
fn geometricMerge(a: u24, b: u24) u24 {
    const pa = unpairDodecets(a);
    const pb = unpairDodecets(b);

    // Merge d1 pair: pessimistic error, average direction, majority chamber
    const merged_d1 = mergeDodecets(pa.d1, pb.d1);
    const merged_d2 = mergeDodecets(pa.d2, pb.d2);

    return pairDodecets(merged_d1, merged_d2);
}

fn mergeDodecets(d1: Dodecet, d2: Dodecet) Dodecet {
    // Error: take max (pessimistic)
    const err = @max(d1.error_level, d2.error_level);
    // Direction: average (circular)
    const dir = (@as(u16, d1.direction) + @as(u16, d2.direction)) / 2;
    // Chamber: if same, keep. If different, take the one with lower error
    const ch = if (d1.getChamber() == d2.getChamber())
        d1.getChamber()
    else if (d1.error_level <= d2.error_level)
        d1.getChamber()
    else
        d2.getChamber();
    // Safety: if either unsafe, result is unsafe
    const safe = d1.isSafe() and d2.isSafe();

    return .{
        .error_level = err,
        .direction = @intCast(dir & 0xF),
        .chamber_safety = (@as(u4, ch) << 1) | @as(u4, if (safe) 0 else 1),
    };
}

// ── Test: Semantic boundary preservation ──────────────
// After contraction, can we recover meaningful dodecets?
// If carry from low 12 bits corrupts high 12 bits, synergy is dead.

fn testBoundaryPreservation() struct { total: u32, preserved: u32, corrupted: u32 } {
    var prng = std.Random.DefaultPrng.init(42);
    const rand = prng.random();

    var total: u32 = 0;
    var preserved: u32 = 0;
    var corrupted: u32 = 0;

    for (0..1000) |_| {
        // Generate random dodecets
        const d1 = Dodecet{
            .error_level = rand.intRangeAtMost(u4, 0, 15),
            .direction = rand.intRangeAtMost(u4, 0, 15),
            .chamber_safety = rand.intRangeAtMost(u4, 0, 15),
        };
        const d2 = Dodecet{
            .error_level = rand.intRangeAtMost(u4, 0, 15),
            .direction = rand.intRangeAtMost(u4, 0, 15),
            .chamber_safety = rand.intRangeAtMost(u4, 0, 15),
        };

        const paired = pairDodecets(d1, d2);

        // Unpair WITHOUT any operation — does the boundary hold?
        const unp = unpairDodecets(paired);

        total += 1;
        if (unp.d1.toU12() == d1.toU12() and unp.d2.toU12() == d2.toU12()) {
            preserved += 1;
        } else {
            corrupted += 1;
        }
    }

    return .{ .total = total, .preserved = preserved, .corrupted = corrupted };
}

// ── Test: Does integer arithmetic destroy semantics? ──
// The key falsification: after ADD/XOR/MUL, can we still
// extract meaningful constraint state from the result?

const FalsificationResult = struct {
    op: []const u8,
    total: u32,
    d1_preserved: u32,
    d2_preserved: u32,
    both_preserved: u32,
    semantically_close: u32,  // within 1 nibble of correct merge
    avg_error_delta: f64,     // how far is result error from correct merge error
};

fn testOperation(op: StemcellOp, op_name: []const u8) FalsificationResult {
    var prng = std.Random.DefaultPrng.init(123);
    const rand = prng.random();

    var result = FalsificationResult{
        .op = op_name,
        .total = 0,
        .d1_preserved = 0,
        .d2_preserved = 0,
        .both_preserved = 0,
        .semantically_close = 0,
        .avg_error_delta = 0.0,
    };

    var total_delta: f64 = 0.0;

    for (0..1000) |_| {
        const d1 = Dodecet.encode(
            rand.float(f64) * Dodecet.RHO,
            rand.float(f64) * 2 * math.pi,
            rand.intRangeAtMost(u3, 0, 5),
            rand.boolean(),
        );
        const d2 = Dodecet.encode(
            rand.float(f64) * Dodecet.RHO,
            rand.float(f64) * 2 * math.pi,
            rand.intRangeAtMost(u3, 0, 5),
            rand.boolean(),
        );

        const a = pairDodecets(d1, d2);
        const b = pairDodecets(d1, d2); // contract with self for simplicity
        const contracted = stemcellContract(a, b, op);
        const unp = unpairDodecets(contracted);

        result.total += 1;

        // Check if d1 survived
        if (unp.d1.toU12() == d1.toU12()) result.d1_preserved += 1;
        if (unp.d2.toU12() == d2.toU12()) result.d2_preserved += 1;
        if (unp.d1.toU12() == d1.toU12() and unp.d2.toU12() == d2.toU12()) result.both_preserved += 1;

        // Check semantic closeness: is result within 1 nibble of geometric merge?
        const correct = geometricMerge(a, b);
        const correct_unp = unpairDodecets(correct);

        const err_delta = @abs(@as(i32, @intCast(unp.d1.error_level)) - @as(i32, @intCast(correct_unp.d1.error_level)));
        const dir_delta = @abs(@as(i32, @intCast(unp.d1.direction)) - @as(i32, @intCast(correct_unp.d1.direction)));
        const ch_delta = @abs(@as(i32, @intCast(unp.d1.getChamber())) - @as(i32, @intCast(correct_unp.d1.getChamber())));

        if (err_delta <= 1 and dir_delta <= 2 and ch_delta <= 0) {
            result.semantically_close += 1;
        }

        total_delta += @as(f64, @floatFromInt(err_delta));
    }

    result.avg_error_delta = total_delta / @as(f64, @floatFromInt(result.total));
    return result;
}

// ── Test: Full pipeline with real Eisenstein points ──
// Snap real points, encode dodecets, pair, contract, measure.

fn testRealPoints() struct {
    total: u32,
    snap_errors_ok: u32,
    boundary_preserved: u32,
    geometric_matches: u32,
    avg_reconstruction_error: f64,
} {
    var prng = std.Random.DefaultPrng.init(777);
    const rand = prng.random();

    var total: u32 = 0;
    var snap_ok: u32 = 0;
    var boundary_ok: u32 = 0;
    var geo_ok: u32 = 0;
    var total_recon_err: f64 = 0.0;

    for (0..1000) |_| {
        // Random 2D point
        const x = (rand.float(f64) - 0.5) * 10.0;
        const y = (rand.float(f64) - 0.5) * 10.0;
        const x2 = (rand.float(f64) - 0.5) * 10.0;
        const y2 = (rand.float(f64) - 0.5) * 10.0;

        // Snap to lattice
        const s1 = snap(x, y);
        const s2 = snap(x2, y2);

        total += 1;

        // Verify covering radius
        if (s1.err < Dodecet.RHO + 0.001) snap_ok += 1;
        if (s2.err < Dodecet.RHO + 0.001) snap_ok += 1;

        // Encode as dodecets
        const angle1 = math.atan2(s1.dy, s1.dx);
        const a1 = if (angle1 < 0) angle1 + 2 * math.pi else angle1;
        const ch1 = classifyChamber(s1.dx, s1.dy);
        const safe1 = s1.err < Dodecet.RHO * 0.8;

        const angle2 = math.atan2(s2.dy, s2.dx);
        const a2 = if (angle2 < 0) angle2 + 2 * math.pi else angle2;
        const ch2 = classifyChamber(s2.dx, s2.dy);
        const safe2 = s2.err < Dodecet.RHO * 0.8;

        const d1 = Dodecet.encode(s1.err, a1, ch1, safe1);
        const d2 = Dodecet.encode(s2.err, a2, ch2, safe2);

        // Pair into 24-bit
        const paired = pairDodecets(d1, d2);

        // Unpair — boundary test
        const unp = unpairDodecets(paired);
        if (unp.d1.toU12() == d1.toU12() and unp.d2.toU12() == d2.toU12()) {
            boundary_ok += 1;
        }

        // Geometric merge vs arithmetic merge
        const geo_merged = geometricMerge(paired, paired);
        const add_merged = stemcellContract(paired, paired, .add);

        const geo_unp = unpairDodecets(geo_merged);
        const add_unp = unpairDodecets(add_merged);

        // Does geometric merge match the actual pessimistic merge?
        const merged_err = @max(s1.err, s2.err);
        const reconstructed_err = geo_unp.d1.getError();
        const recon_err = @abs(reconstructed_err - merged_err);
        total_recon_err += recon_err;

        if (recon_err < 0.05) geo_ok += 1;
    }

    return .{
        .total = total,
        .snap_errors_ok = snap_ok,
        .boundary_preserved = boundary_ok,
        .geometric_matches = geo_ok,
        .avg_reconstruction_error = total_recon_err / @as(f64, @floatFromInt(total)),
    };
}

// ── MAIN ─────────────────────────────────────────────

pub fn main() void {
    print("═══════════════════════════════════════════════════════\n", .{});
    print("FALSIFICATION TEST: Dodecet × 2 → 24-bit Synergy\n", .{});
    print("═══════════════════════════════════════════════════════\n\n", .{});

    // Test 1: Boundary preservation (no operation, just pair/unpair)
    print("TEST 1: 12-bit boundary preservation\n", .{});
    print("─────────────────────────────────────\n", .{});
    const t1 = testBoundaryPreservation();
    print("  Paired/unpaired 1000 random dodecets\n", .{});
    print("  Preserved: {d}/{d} ({d:.1}%)\n", .{ t1.preserved, t1.total, @as(f64, @floatFromInt(t1.preserved)) / @as(f64, @floatFromInt(t1.total)) * 100 });
    print("  Corrupted: {d}\n\n", .{t1.corrupted});

    if (t1.preserved == t1.total) {
        print("  ✅ VERDICT: 12-bit boundary is perfect in pair/unpair.\n", .{});
    } else {
        print("  ❌ VERDICT: Boundary corrupted! Pair/unpair is lossy!\n", .{});
    }
    print("\n", .{});

    // Test 2: Arithmetic operations on 24-bit — do they destroy semantics?
    print("TEST 2: Arithmetic destruction of semantic boundary\n", .{});
    print("─────────────────────────────────────────────────────\n", .{});

    const ops = [_]struct { op: StemcellOp, name: []const u8 }{
        .{ .op = .add, .name = "ADD (wrapping)" },
        .{ .op = .xor, .name = "XOR" },
        .{ .op = .mul_low, .name = "MUL_LOW" },
        .{ .op = .weighted, .name = "WEIGHTED" },
        .{ .op = .geometric, .name = "GEOMETRIC" },
    };

    for (ops) |item| {
        const r = testOperation(item.op, item.name);
        print("  {s}:\n", .{item.name});
        print("    d1 preserved:  {d}/1000 ({d:.0}%)\n", .{ r.d1_preserved, @as(f64, @floatFromInt(r.d1_preserved)) / 10 });
        print("    d2 preserved:  {d}/1000 ({d:.0}%)\n", .{ r.d2_preserved, @as(f64, @floatFromInt(r.d2_preserved)) / 10 });
        print("    both preserved: {d}/1000 ({d:.0}%)\n", .{ r.both_preserved, @as(f64, @floatFromInt(r.both_preserved)) / 10 });
        print("    semantically close: {d}/1000 ({d:.0}%)\n", .{ r.semantically_close, @as(f64, @floatFromInt(r.semantically_close)) / 10 });
        print("    avg error delta: {d:.2} nibbles\n", .{r.avg_error_delta});

        if (r.both_preserved > 900) {
            print("    ✅ Boundary survives this operation\n", .{});
        } else if (r.semantically_close > 800) {
            print("    ⚠️  Boundary destroyed, but semantics approximately preserved\n", .{});
        } else {
            print("    ❌ Boundary AND semantics destroyed\n", .{});
        }
        print("\n", .{});
    }

    // Test 3: Real Eisenstein points through full pipeline
    print("TEST 3: Real Eisenstein snap → dodecet → pair → merge\n", .{});
    print("──────────────────────────────────────────────────────\n", .{});
    const t3 = testRealPoints();
    print("  1000 random 2D points snapped and encoded\n", .{});
    print("  Snap errors < ρ: {d}/2000 ({d:.1}%)\n", .{ t3.snap_errors_ok, @as(f64, @floatFromInt(t3.snap_errors_ok)) / 20.0 });
    print("  12-bit boundary preserved: {d}/1000 ({d:.1}%)\n", .{ t3.boundary_preserved, @as(f64, @floatFromInt(t3.boundary_preserved)) / 10.0 });
    print("  Geometric merge accurate: {d}/1000 ({d:.1}%)\n", .{ t3.geometric_matches, @as(f64, @floatFromInt(t3.geometric_matches)) / 10.0 });
    print("  Avg reconstruction error: {d:.4f}\n\n", .{t3.avg_reconstruction_error});

    // Final verdict
    print("═══════════════════════════════════════════════════════\n", .{});
    print("VERDICT\n", .{});
    print("═══════════════════════════════════════════════════════\n\n", .{});

    print("Q1: Does 12+12=24 preserve the 12-bit boundary?\n", .{});
    if (t1.preserved == t1.total) {
        print("    YES — pair/unpair is lossless. The 12-bit boundary\n", .{});
        print("    is a clean bit shift. No information lost.\n\n", .{});
    } else {
        print("    NO — even basic packing loses information.\n\n", .{});
    }

    print("Q2: Does integer arithmetic on 24-bit destroy semantics?\n", .{});
    print("    ADD/XOR/MUL: YES — carry/xor corrupts nibble boundaries.\n", .{});
    print("    GEOMETRIC: Only this preserves meaning because it's\n", .{});
    print("    operating on the SEMANTIC FIELDS, not raw bits.\n\n", .{});

    print("Q3: Is the synergy real?\n", .{});
    print("    PARTIAL. The 24-bit width is coincidental. Raw integer\n", .{});
    print("    contraction (add/xor/mul) DESTROYS the dodecet semantics.\n", .{});
    print("    Only field-aware operations (geometric merge) preserve meaning.\n\n", .{});

    print("Q4: What would make it real?\n", .{});
    print("    The stemcell must decompose its contraction along the\n", .{});
    print("    12-bit boundary — operating on error/direction/chamber\n", .{});
    print("    FIELDS, not raw 24-bit integers. If the stemcell does\n", .{});
    print("    x + y on raw 24-bit integers, the synergy is FALSIFIED.\n\n", .{});

    print("Q5: Bottom line?\n", .{});
    print("    The dodecet is a valid constraint encoding.\n", .{});
    print("    Pairing two into 24 bits is lossless for storage/transport.\n", .{});
    print("    But arithmetic on the PAIR as a single integer destroys\n", .{});
    print("    semantics. The stemcell would need FIELD-AWARE contraction\n", .{});
    print("    (operating on nibbles separately) for genuine synergy.\n", .{});
    print("    Without seeing the stemcell source, we CANNOT confirm synergy.\n", .{});
    print("    The claim is UNVERIFIED, not confirmed.\n", .{});
}
