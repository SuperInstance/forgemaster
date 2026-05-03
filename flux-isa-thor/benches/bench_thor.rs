use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};
use flux_isa_thor::vm::ThorVm;
use std::sync::Arc;

fn bench_vm_sequential(c: &mut Criterion) {
    // PUSH 1.0, PUSH 2.0, ADD, HALT
    let mut bytecode: Vec<u8> = vec![0x01]; // PUSH
    bytecode.extend_from_slice(&1.0f64.to_be_bytes());
    bytecode.push(0x01); // PUSH
    bytecode.extend_from_slice(&2.0f64.to_be_bytes());
    bytecode.push(0x10); // ADD
    bytecode.push(0x45); // HALT

    let rt = tokio::runtime::Runtime::new().unwrap();
    let vm = create_test_vm();

    c.bench_function("vm_sequential_push_add_halt", |b| {
        b.to_async(&rt).iter(|| vm.execute(&bytecode));
    });
}

fn bench_vm_parallel_branches(c: &mut Criterion) {
    let rt = tokio::runtime::Runtime::new().unwrap();
    let vm = create_test_vm();

    let mut group = c.benchmark_group("parallel_branches");
    for n in [1, 4, 8, 16] {
        // PARALLEL_BRANCH N, HALT
        let mut bytecode = vec![0x80]; // PARALLEL_BRANCH
        bytecode.extend_from_slice(&(n as u32).to_be_bytes());
        bytecode.push(0x45); // HALT

        group.bench_with_input(BenchmarkId::from_parameter(n), &n, |b, _| {
            b.to_async(&rt).iter(|| vm.execute(&bytecode));
        });
    }
    group.finish();
}

fn create_test_vm() -> Arc<ThorVm> {
    use flux_isa_thor::cuda::GpuDispatcher;
    use flux_isa_thor::fleet::{FleetHandle, FleetNode, NodeRole, NodeStatus};
    use flux_isa_thor::plato::{PlatoHandle, cache::TileCache, client::PlatoClient};
    use flux_isa_thor::vm::VmConfig;

    let gpu = Arc::new(GpuDispatcher::new(false, 0, 4));
    let plato_client = Arc::new(PlatoClient::new("http://localhost:1", 4, std::time::Duration::from_secs(1)));
    let cache = Arc::new(tokio::sync::RwLock::new(TileCache::new(1000)));
    let plato = Arc::new(PlatoHandle::new(plato_client, cache));
    let fleet = Arc::new(FleetHandle::new(FleetNode {
        id: "bench-node".into(),
        hostname: "bench".into(),
        role: NodeRole::Thor,
        gpu_available: false,
        gpu_memory_mb: 0,
        status: NodeStatus::Online,
        last_heartbeat: 0,
    }));

    Arc::new(ThorVm::new(VmConfig::default(), gpu, plato, fleet))
}

criterion_group!(benches, bench_vm_sequential, bench_vm_parallel_branches);
criterion_main!(benches);
