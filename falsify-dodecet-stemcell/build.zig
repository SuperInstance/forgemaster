.{
    .name = "falsify-dodecet-stemcell",
    .version = "0.1.0",
    .minimum_zig_version = "0.13.0",
    .dependencies = .{},
    .targets = .{
        .{
            .name = "falsify",
            .root = "src/main.zig",
            .target = .{ .cpu_arch = .x86_64, .os_tag = .linux },
        },
    },
}
