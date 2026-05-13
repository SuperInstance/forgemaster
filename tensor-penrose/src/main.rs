//! CLI binary for tensor-penrose.
//!
//! Usage:
//!   pt create --backend eisenstein --points 1000 --output tiling.tp
//!   pt info tiling.tp
//!   pt apply tiling.tp --op threshold --params 0.5
//!   pt bench tiling.tp

use std::env;
use std::process;

use tensor_penrose::PTiling;
use tensor_penrose::ops::Threshold;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: pt <command> [options]");
        eprintln!("Commands: create, info, apply, bench");
        process::exit(1);
    }

    match args[1].as_str() {
        "create" => cmd_create(&args[2..]),
        "info" => cmd_info(&args[2..]),
        "apply" => cmd_apply(&args[2..]),
        "bench" => cmd_bench(&args[2..]),
        other => {
            eprintln!("Unknown command: {}", other);
            eprintln!("Commands: create, info, apply, bench");
            process::exit(1);
        }
    }
}

fn parse_args<'a>(args: &'a [String]) -> Vec<(&'a str, &'a str)> {
    let mut pairs = Vec::new();
    let mut i = 0;
    while i + 1 < args.len() {
        if args[i].starts_with("--") {
            pairs.push((&args[i][2..], &args[i + 1][..]));
            i += 2;
        } else {
            i += 1;
        }
    }
    pairs
}

fn get_opt<'a>(pairs: &'a [(&'a str, &'a str)], key: &str) -> Option<&'a str> {
    pairs.iter().find(|(k, _)| *k == key).map(|(_, v)| *v)
}

fn cmd_create(args: &[String]) {
    let opts = parse_args(args);
    let backend_name = get_opt(&opts, "backend").unwrap_or("eisenstein");
    let points: usize = get_opt(&opts, "points")
        .and_then(|s| s.parse().ok())
        .unwrap_or(100);
    let output = get_opt(&opts, "output").unwrap_or("tiling.tp");

    let mut lattice_points = Vec::with_capacity(points);
    for i in 0..points {
        let a = ((i as i32) % 20) - 10;
        let b = (((i as i32) * 7) % 20) - 10;
        let c = (((i as i32) * 13) % 20) - 10;
        let d = (((i as i32) * 3) % 20) - 10;
        let e = (((i as i32) * 11) % 20) - 10;
        lattice_points.push([a, b, c, d, e]);
    }

    let tiling = match backend_name {
        "eisenstein" => {
            let backend = tensor_penrose::backend::eisenstein::EisensteinBackend::new();
            PTiling::from_lattice(&lattice_points, &backend)
        }
        "penrose" => {
            let backend = tensor_penrose::backend::penrose::PenroseBackend::new();
            PTiling::from_lattice(&lattice_points, &backend)
        }
        _ => {
            eprintln!("Unknown backend: {}. Use 'eisenstein' or 'penrose'.", backend_name);
            process::exit(1);
        }
    };

    match tiling.save(output) {
        Ok(()) => {
            let info = tiling.info();
            println!("Created tiling: {} tiles ({} thick, {} thin), {} edges",
                     info.tile_count, info.thick_count, info.thin_count, info.adjacency_count);
            println!("Saved to: {}", output);
        }
        Err(e) => {
            eprintln!("Error saving: {}", e);
            process::exit(1);
        }
    }
}

fn cmd_info(args: &[String]) {
    if args.is_empty() {
        eprintln!("Usage: pt info <tiling.tp>");
        process::exit(1);
    }
    let path = &args[0];

    let tiling = match PTiling::load(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Error loading {}: {}", path, e);
            process::exit(1);
        }
    };

    let info = tiling.info();
    println!("Tiling: {} backend", info.backend_name);
    println!("Tiles: {} ({} thick, {} thin)", info.tile_count, info.thick_count, info.thin_count);
    println!("Adjacent pairs: {}", info.adjacency_count);

    if !tiling.tiles.is_empty() {
        let shapes: std::collections::HashSet<(usize, usize)> =
            tiling.tiles.iter().map(|t| t.shape()).collect();
        print!("Shape(s) per tile:");
        for s in &shapes {
            print!(" ({}, {})", s.0, s.1);
        }
        println!();

        // Compute global L1/L2 norms
        let l1: f32 = tiling.tiles.iter().map(|t| t.l1_norm()).sum();
        let l2: f32 = tiling.tiles.iter().map(|t| t.l2_norm()).sum();
        println!("Global L1 norm: {:.4}", l1);
        println!("Global L2 norm: {:.4}", l2);
    }
}

fn cmd_apply(args: &[String]) {
    let opts = parse_args(args);
    let path = args.first().expect("need tiling path");
    let op_name = get_opt(&opts, "op").unwrap_or("threshold");
    let params = get_opt(&opts, "params").unwrap_or("0.5");

    let mut tiling = match PTiling::load(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Error loading {}: {}", path, e);
            process::exit(1);
        }
    };

    match op_name {
        "threshold" => {
            let threshold: f32 = params.parse().unwrap_or(0.5);
            let op = Threshold::new(threshold);
            tiling.apply(&op);
            println!("Applied threshold({}) to {} tiles", threshold, tiling.tiles.len());
        }
        _ => {
            eprintln!("Unknown op: {}. Available: threshold", op_name);
            process::exit(1);
        }
    }

    // Save back
    if let Err(e) = tiling.save(path) {
        eprintln!("Error saving: {}", e);
        process::exit(1);
    }
    println!("Saved to: {}", path);
}

fn cmd_bench(args: &[String]) {
    if args.is_empty() {
        eprintln!("Usage: pt bench <tiling.tp>");
        process::exit(1);
    }
    let path = &args[0];

    let mut tiling = match PTiling::load(path) {
        Ok(t) => t,
        Err(e) => {
            eprintln!("Error loading {}: {}", path, e);
            process::exit(1);
        }
    };

    let tile_count = tiling.tiles.len();
    let adj_count = tiling.adjacency.len();

    // Benchmark apply
    let iterations = 100;
    let start = std::time::Instant::now();
    let op = Threshold::new(0.5);
    for _ in 0..iterations {
        tiling.apply(&op);
    }
    let elapsed = start.elapsed();
    let per_op = elapsed / iterations;
    let ops_per_sec = 1_000_000_000u128 / per_op.as_nanos().max(1);

    println!("Apply benchmark (threshold 0.5):");
    println!("  Tiles: {}", tile_count);
    println!("  Adjacent pairs: {}", adj_count);
    println!("  {} iterations in {:?}", iterations, elapsed);
    println!("  {:.0} ns/op ({} ops/sec)", per_op.as_nanos(), ops_per_sec);

    // Benchmark constraint check
    if !tiling.adjacency.is_empty() {
        // Constrain all adjacent pairs
        let edges: Vec<(usize, usize)> = tiling.adjacency.iter().map(|&(i, j, _)| (i, j)).collect();
        tiling.constrain(&edges);

        let start = std::time::Instant::now();
        for _ in 0..iterations {
            let _ = tiling.constraint_check();
        }
        let elapsed = start.elapsed();
        let per_op = elapsed / iterations;
        println!("Constraint check: {:.0} ns/op ({:.0} ops/sec)", per_op.as_nanos(),
                 1_000_000_000u128 / per_op.as_nanos().max(1));
    }
}
