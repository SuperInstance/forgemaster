const std = @import("std");

pub fn build(b: *std.Build) void {
    const target = b.standardTargetOptions(.{});
    const optimize = b.standardOptimizeOption(.{});

    // --- Static library ---
    const lib = b.addStaticLibrary(.{
        .name = "snapkit",
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    lib.installHeader(b.path("src/root.zig"), "snapkit-zig.h");
    b.installArtifact(lib);

    // --- Shared library (C-compatible exports) ---
    const shared = b.addSharedLibrary(.{
        .name = "snapkit",
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    b.installArtifact(shared);

    // --- Tests ---
    const unit_tests = b.addTest(.{
        .root_source_file = b.path("src/root.zig"),
        .target = target,
        .optimize = optimize,
    });
    const run_unit_tests = b.addRunArtifact(unit_tests);
    const test_step = b.step("test", "Run unit tests");
    test_step.dependOn(&run_unit_tests.step);

    // --- Cross-compilation demo targets ---
    // zig build arm64  -> aarch64-linux
    const arm64_step = b.step("arm64", "Cross-compile for aarch64-linux");
    const arm64_lib = b.addStaticLibrary(.{
        .name = "snapkit",
        .root_source_file = b.path("src/root.zig"),
        .target = b.resolveTargetQuery(.{ .cpu_arch = .aarch64, .os_tag = .linux }),
        .optimize = .ReleaseSmall,
    });
    arm64_step.dependOn(&b.addInstallArtifact(arm64_lib, .{}).step);

    // zig build wasm   -> wasm32-freestanding
    const wasm_step = b.step("wasm", "Cross-compile for wasm32-freestanding");
    const wasm_lib = b.addStaticLibrary(.{
        .name = "snapkit",
        .root_source_file = b.path("src/root.zig"),
        .target = b.resolveTargetQuery(.{ .cpu_arch = .wasm32, .os_tag = .freestanding }),
        .optimize = .ReleaseSmall,
    });
    wasm_step.dependOn(&b.addInstallArtifact(wasm_lib, .{}).step);

    // zig build x86-windows
    const win_step = b.step("x86-windows", "Cross-compile for x86_64-windows");
    const win_lib = b.addStaticLibrary(.{
        .name = "snapkit",
        .root_source_file = b.path("src/root.zig"),
        .target = b.resolveTargetQuery(.{ .cpu_arch = .x86_64, .os_tag = .windows }),
        .optimize = .ReleaseSmall,
    });
    win_step.dependOn(&b.addInstallArtifact(win_lib, .{}).step);
}
