use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use ct_bench::*;

fn bench_snap_comparison(c: &mut Criterion) {
    let mut group = c.benchmark_group("snap");
    
    for max_c in [1000u64, 10000, 50000] {
        let raw = generate_triples(max_c);
        let sorted = build_angle_array(&raw);
        let n = sorted.len();
        let step = std::f64::consts::TAU / 100_000.0;
        
        group.bench_with_input(
            BenchmarkId::new("binary_search", max_c),
            &sorted,
            |b, sorted| {
                b.iter(|| {
                    let mut sum = 0u64;
                    for i in 0..100_000 {
                        let idx = snap_binary(sorted, i as f64 * step);
                        sum = sum.wrapping_add(idx as u64);
                    }
                    black_box(sum);
                });
            },
        );
        
        group.bench_with_input(
            BenchmarkId::new("brute_force", max_c),
            &sorted,
            |b, sorted| {
                b.iter(|| {
                    let mut sum = 0u64;
                    for i in 0..10_000 { // fewer for brute
                        let idx = snap_brute(sorted, i as f64 * step * 10.0);
                        sum = sum.wrapping_add(idx as u64);
                    }
                    black_box(sum);
                });
            },
        );
    }
    
    group.finish();
}

fn bench_holonomy_measurement(c: &mut Criterion) {
    let mut group = c.benchmark_group("holonomy");
    
    for max_c in [1000u64, 10000, 50000] {
        let raw = generate_triples(max_c);
        let sorted = build_angle_array(&raw);
        
        group.bench_with_input(
            BenchmarkId::new("random_walk", max_c),
            &sorted,
            |b, sorted| {
                b.iter(|| {
                    let n = sorted.len();
                    let mut pos = 0usize;
                    let mut state: u64 = 42;
                    for _ in 0..10_000 {
                        state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
                        let step = (state >> 33) as usize % (n / 10).max(1);
                        pos = (pos + step) % n;
                    }
                    black_box(pos);
                });
            },
        );
    }
    
    group.finish();
}

criterion_group!(benches, bench_snap_comparison, bench_holonomy_measurement);
criterion_main!(benches);
