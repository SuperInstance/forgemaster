use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};
use plato_engine::{Gate, GateConfig, PlatoEngine, TileBuilder, Provenance};

fn make_tile(answer: &str, question: &str) -> plato_engine::Tile {
    TileBuilder::new()
        .domain("bench")
        .question(question)
        .answer(answer)
        .source("bench-source")
        .confidence(0.85)
        .provenance(Provenance {
            agent_id: "bench-agent".into(),
            session_id: "bench-session".into(),
            chain_hash: "bench-chain".into(),
            signature: "bench-sig".into(),
        })
        .build()
        .unwrap()
}

fn bench_gate_throughput(c: &mut Criterion) {
    let gate = Gate::with_defaults();
    let tile = make_tile(
        "Rust provides zero-cost abstractions and memory safety without garbage collection.",
        "Why use Rust?",
    );

    c.bench_function("gate/evaluate_accept", |b| {
        b.iter(|| gate.evaluate(&tile))
    });

    let bad_tile = make_tile(
        "This will always work and never fails under any circumstances whatsoever.",
        "Is it reliable?",
    );

    c.bench_function("gate/evaluate_reject", |b| {
        b.iter(|| gate.evaluate(&bad_tile))
    });
}

fn bench_room_operations(c: &mut Criterion) {
    let engine = PlatoEngine::with_defaults();

    // Pre-populate with tiles
    for i in 0..1000 {
        let tile = make_tile(
            &format!("This is answer number {} about the topic in question.", i),
            &format!("What is fact {}?", i),
        );
        let _ = engine.submit("bench-room", tile);
    }

    c.bench_function("room/lookup_existing", |b| {
        b.iter(|| engine.get_room("bench-room"))
    });

    c.bench_function("room/lookup_missing", |b| {
        b.iter(|| engine.get_room("nonexistent-room"))
    });

    c.bench_function("room/list_rooms", |b| {
        b.iter(|| engine.list_rooms(None))
    });
}

fn bench_engine_submit(c: &mut Criterion) {
    let mut group = c.benchmark_group("engine/submit");

    for size in [10, 100, 1000] {
        let engine = PlatoEngine::with_defaults();
        let room_id = format!("room-{}", size);

        // Pre-populate
        for i in 0..size {
            let tile = make_tile(
                &format!("Pre-existing answer {} for the room.", i),
                &format!("Question {}?", i),
            );
            let _ = engine.submit(&room_id, tile);
        }

        group.bench_with_input(BenchmarkId::from_parameter(size), &engine, |b, engine| {
            let mut counter = size;
            b.iter(|| {
                let tile = make_tile(
                    &format!("New answer {} submitted to the engine.", counter),
                    &format!("New question {}?", counter),
                );
                let _ = engine.submit(&room_id, tile);
                counter += 1;
            });
        });
    }

    group.finish();
}

criterion_group!(
    benches,
    bench_gate_throughput,
    bench_room_operations,
    bench_engine_submit,
);
criterion_main!(benches);
