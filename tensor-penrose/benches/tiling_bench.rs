//! Criterion benchmarks for tensor-penrose.

use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use tensor_penrose::PTiling;
use tensor_penrose::backend::eisenstein::EisensteinBackend;
use tensor_penrose::ops::Threshold;

fn generate_points(n: usize) -> Vec<[i32; 5]> {
    (0..n)
        .map(|i| {
            let a = ((i as i32) % 20) - 10;
            let b = (((i as i32) * 7) % 20) - 10;
            let c = (((i as i32) * 13) % 20) - 10;
            let d = (((i as i32) * 3) % 20) - 10;
            let e = (((i as i32) * 11) % 20) - 10;
            [a, b, c, d, e]
        })
        .collect()
}

fn bench_create(c: &mut Criterion) {
    let mut group = c.benchmark_group("create_tiling");
    for size in [100, 1000, 10000] {
        group.bench_with_input(BenchmarkId::from_parameter(size), &size, |b, &size| {
            let backend = EisensteinBackend::new();
            b.iter(|| {
                let points = generate_points(size);
                PTiling::from_lattice(black_box(&points), black_box(&backend))
            });
        });
    }
    group.finish();
}

fn bench_apply(c: &mut Criterion) {
    let backend = EisensteinBackend::new();
    let mut group = c.benchmark_group("apply_threshold");

    for size in [100, 1000, 10000] {
        let points = generate_points(size);
        let tiling = PTiling::from_lattice(&points, &backend);
        group.bench_with_input(BenchmarkId::from_parameter(size), &tiling, |b, tiling| {
            let op = Threshold::new(0.5);
            b.iter(|| {
                let mut t = tiling.clone();
                t.apply(black_box(&op));
                black_box(&t);
            });
        });
    }
    group.finish();
}

criterion_group!(benches, bench_create, bench_apply);
criterion_main!(benches);
