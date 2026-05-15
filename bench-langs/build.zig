const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // Native benchmark executable
    const exe = b.addExecutable(.{
        .name = "constraint_bench",
        .root_source_file = b.path("constraint.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(exe);

    // Run step
    const run_cmd = b.addRunArtifact(exe);
    run_cmd.step.dependOn(b.getInstallStep());
    const run_step = b.step("run", "Run the constraint theory benchmark");
    run_step.dependOn(&run_cmd.step);

    // Tests
    const unit_tests = b.addTest(.{
        .root_source_file = b.path("constraint.zig"),
        .target = target,
        .optimize = optimize,
    });
    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);

    // WASM executable (separate entry point for freestanding target)
    const wasm_exe = b.addExecutable(.{
        .name = "constraint",
        .root_source_file = b.path("constraint_wasm.zig"),
        .target = b.resolveTargetQuery(.{
            .cpu_arch = .wasm32,
            .os_tag = .freestanding,
        }),
        .optimize = optimize,
    });
    wasm_exe.rdynamic = true;
    wasm_exe.entry = .disabled;
    b.installArtifact(wasm_exe);

    const wasm_step = b.step("wasm", "Build WASM library");
    wasm_step.dependOn(&b.addInstallArtifact(wasm_exe, .{}).step);
}
