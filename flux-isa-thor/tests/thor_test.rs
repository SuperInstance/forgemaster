use flux_isa_thor::cuda::solver::{BatchCspSolver, CspConstraint, ConstraintRelation, CspInstance};
use flux_isa_thor::cuda::sonar::{BatchSonarPhysics, SonarParams};
use flux_isa_thor::cuda::GpuDispatcher;
use flux_isa_thor::fleet::{FleetHandle, FleetNode, NodeRole, NodeStatus};
use flux_isa_thor::opcode::{Instruction, Opcode, ThorOpcode};
use flux_isa_thor::plato::{PlatoHandle, cache::TileCache, client::PlatoClient};
use flux_isa_thor::vm::{ThorVm, VmConfig};

fn make_test_vm() -> std::sync::Arc<ThorVm> {
    let gpu = std::sync::Arc::new(GpuDispatcher::new(false, 0, 4));
    let plato_client = std::sync::Arc::new(PlatoClient::new("http://localhost:1", 4, std::time::Duration::from_secs(1)));
    let cache = std::sync::Arc::new(tokio::sync::RwLock::new(TileCache::new(100)));
    let plato = std::sync::Arc::new(PlatoHandle::new(plato_client, cache));
    let fleet = std::sync::Arc::new(FleetHandle::new(FleetNode {
        id: "test".into(),
        hostname: "test".into(),
        role: NodeRole::Thor,
        gpu_available: false,
        gpu_memory_mb: 0,
        status: NodeStatus::Online,
        last_heartbeat: 0,
    }));
    std::sync::Arc::new(ThorVm::new(VmConfig::default(), gpu, plato, fleet))
}

#[test]
fn test_opcode_round_trip() {
    assert_eq!(Instruction::Base(Opcode::Nop).to_byte(), 0x00);
    assert_eq!(Instruction::Thor(ThorOpcode::BatchSolve).to_byte(), 0x83);
    assert!(Instruction::from_byte(0xFF).is_none());
}

#[tokio::test]
async fn test_vm_push_add_halt() {
    let vm = make_test_vm();
    let mut bc = vec![0x01]; // PUSH 3.0
    bc.extend_from_slice(&3.0f64.to_be_bytes());
    bc.push(0x01); // PUSH 4.0
    bc.extend_from_slice(&4.0f64.to_be_bytes());
    bc.push(0x10); // ADD
    bc.push(0x45); // HALT

    let result = vm.execute(&bc).await;
    assert_eq!(result.stack.len(), 1);
    assert!((result.stack[0].as_f64().unwrap() - 7.0).abs() < f64::EPSILON);
}

#[tokio::test]
async fn test_vm_compare_and_jump() {
    let vm = make_test_vm();
    let mut bc = vec![0x01]; // PUSH 5.0
    bc.extend_from_slice(&5.0f64.to_be_bytes());
    bc.push(0x01); // PUSH 5.0
    bc.extend_from_slice(&5.0f64.to_be_bytes());
    bc.push(0x30); // EQ
    bc.push(0x45); // HALT

    let result = vm.execute(&bc).await;
    assert_eq!(result.stack.len(), 1);
    assert!(result.stack[0].as_bool().unwrap());
}

#[tokio::test]
async fn test_batch_csp_solve() {
    let dispatcher = std::sync::Arc::new(GpuDispatcher::new(false, 0, 4));
    let solver = BatchCspSolver::new(dispatcher);
    let instances: Vec<CspInstance> = (0..20)
        .map(|i| CspInstance {
            id: i,
            variables: vec!["x".into(), "y".into()],
            domains: vec![vec![1.0, 2.0], vec![1.0, 2.0]],
            constraints: vec![CspConstraint {
                var_indices: vec![0, 1],
                relation: ConstraintRelation::NotEqual,
                params: vec![],
            }],
        })
        .collect();

    let results = solver.solve_batch(&instances).await;
    assert_eq!(results.len(), 20);
    assert!(results.iter().all(|r| r.satisfied));
}

#[tokio::test]
async fn test_batch_sonar() {
    let dispatcher = std::sync::Arc::new(GpuDispatcher::new(false, 0, 4));
    let engine = BatchSonarPhysics::new(dispatcher);
    let params: Vec<SonarParams> = (0..50)
        .map(|i| SonarParams {
            depth: i as f64 * 100.0,
            temperature: 15.0,
            salinity: 35.0,
            ph: 8.1,
            frequency_khz: 12.0,
        })
        .collect();

    let results = engine.compute_batch(&params).await;
    assert_eq!(results.len(), 50);
    assert!(results.iter().all(|r| r.sound_speed > 1400.0 && r.sound_speed < 1600.0));
}

#[test]
fn test_config_default() {
    let config = flux_isa_thor::config::ThorConfig::default();
    assert!(!config.node_id.is_empty());
    assert!(!config.plato_url.is_empty());
    assert_eq!(config.pipeline_channel_capacity, 1024);
}

#[test]
fn test_fleet_i2i_message() {
    use flux_isa_thor::fleet::i2i::{I2iMessage, I2iType};
    let msg = I2iMessage::new(I2iType::Task, "thor-1", vec![1, 2, 3]);
    assert_eq!(msg.msg_type, I2iType::Task);
    assert!(msg.to_header().contains("[I2I:TASK]"));
}

#[tokio::test]
async fn test_pipeline() {
    use flux_isa_thor::pipeline::{Pipeline, PipelineConfig};
    let config = PipelineConfig::default();
    let pipeline = Pipeline::new(config);
    let (tx, rx) = tokio::sync::mpsc::channel(16);
    pipeline.run(rx).await;

    // Send an item
    let item = flux_isa_thor::pipeline::PipelineItem {
        id: uuid::Uuid::new_v4(),
        stage: flux_isa_thor::pipeline::Stage::Ingest,
        payload: vec![0x45], // HALT
        error: None,
        entered_at_ns: 0,
    };
    tx.send(item).await.unwrap();

    // Give pipeline time to process
    tokio::time::sleep(std::time::Duration::from_millis(100)).await;
    assert!(pipeline.total_committed() >= 1);
}

#[test]
fn test_tile_cache() {
    use flux_isa_thor::plato::{Tile, cache::TileCache};
    let mut cache = TileCache::new(100);
    let tile = Tile {
        id: uuid::Uuid::new_v4(),
        room_id: "test-room".into(),
        content: serde_json::json!({"key": "value"}),
        confidence: 0.95,
        tags: vec!["test".into()],
        created_at: 12345,
    };
    let id = tile.id;
    cache.insert(tile);
    assert!(cache.get(&id).is_some());
    assert_eq!(cache.get_room("test-room").len(), 1);
}
