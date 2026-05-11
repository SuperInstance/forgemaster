//! SnapKit benchmarks.
//!
//! Measures performance of core operations:
//! - Snap function batch processing
//! - Eisenstein lattice snapping
//! - Delta detection
//! - Attention budget allocation

use criterion::{black_box, criterion_group, criterion_main, Criterion};

use snapkit::{
    eisenstein_snap, eisenstein_snap_batch, AttentionBudget, AllocationStrategy, Delta, DeltaSeverity,
    SnapFunction, SnapTopology,
};

fn bench_snap_observe(c: &mut Criterion) {
    let mut snap = SnapFunction::<f64>::builder()
        .tolerance(0.1)
        .topology(SnapTopology::Hexagonal)
        .build();

    c.bench_function("snap_observe_single", |b| {
        b.iter(|| snap.observe(black_box(0.05)))
    });

    c.bench_function("snap_observe_delta", |b| {
        b.iter(|| snap.observe(black_box(0.3)))
    });
}

fn bench_snap_batch(c: &mut Criterion) {
    let mut snap = SnapFunction::<f64>::builder()
        .tolerance(0.1)
        .topology(SnapTopology::Hexagonal)
        .build();

    let data: Vec<f64> = (0..1000).map(|i| (i as f64 * 0.01).sin()).collect();

    c.bench_function("snap_batch_1000", |b| {
        b.iter(|| {
            let results = snap.snap_batch(black_box(&data));
            black_box(results)
        })
    });
}

fn bench_eisenstein_snap(c: &mut Criterion) {
    c.bench_function("eisenstein_snap_single", |b| {
        b.iter(|| eisenstein_snap(black_box((1.2, 0.7))))
    });
}

fn bench_eisenstein_snap_batch(c: &mut Criterion) {
    let xs: Vec<f64> = (0..1000).map(|i| i as f64 * 0.01).collect();
    let ys: Vec<f64> = (0..1000).map(|i| (i as f64 * 0.01).cos()).collect();

    c.bench_function("eisenstein_snap_batch_1000", |b| {
        b.iter(|| eisenstein_snap_batch(black_box(&xs), black_box(&ys)))
    });
}

fn bench_attention_allocate(c: &mut Criterion) {
    let deltas: Vec<Delta> = (0..10)
        .map(|i| Delta {
            value: i as f64 * 0.3,
            expected: 0.0,
            magnitude: i as f64 * 0.3,
            tolerance: 0.1,
            severity: if i < 3 {
                DeltaSeverity::Medium
            } else if i < 7 {
                DeltaSeverity::High
            } else {
                DeltaSeverity::Critical
            },
            timestamp: i as u64,
            stream_id: format!("s{}", i),
            attention_weight: i as f64,
        })
        .collect();

    let delta_refs: Vec<&Delta> = deltas.iter().collect();

    c.bench_function("attention_allocate_actionability", |b| {
        let mut budget =
            AttentionBudget::new(100.0, AllocationStrategy::Actionability);
        b.iter(|| {
            let allocations = budget.allocate(black_box(&delta_refs));
            black_box(allocations)
        })
    });

    c.bench_function("attention_allocate_reactive", |b| {
        let mut budget = AttentionBudget::new(100.0, AllocationStrategy::Reactive);
        b.iter(|| {
            let allocations = budget.allocate(black_box(&delta_refs));
            black_box(allocations)
        })
    });
}

fn bench_delta_detection(c: &mut Criterion) {
    use snapkit::DeltaDetector;

    let mut detector = DeltaDetector::new();
    detector.add_stream("s1", SnapFunction::<f64>::new());
    detector.add_stream("s2", SnapFunction::<f64>::new());
    detector.add_stream("s3", SnapFunction::<f64>::new());

    let observations: Vec<(&str, f64)> = (0..100)
        .map(|i| {
            let stream = ["s1", "s2", "s3"][i % 3];
            (stream, (i as f64 * 0.05).sin())
        })
        .collect();

    c.bench_function("delta_detect_stream", |b| {
        b.iter(|| {
            for &(stream, value) in &observations {
                let _ = detector.observe(stream, black_box(value));
            }
        })
    });
}

criterion_group!(
    benches,
    bench_snap_observe,
    bench_snap_batch,
    bench_eisenstein_snap,
    bench_eisenstein_snap_batch,
    bench_attention_allocate,
    bench_delta_detection,
);
criterion_main!(benches);
