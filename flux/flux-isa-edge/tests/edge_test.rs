use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::Arc;
use flux_isa_edge::bytecode::Bytecode;
use flux_isa_edge::instruction::Instruction;
use flux_isa_edge::opcode::OpCode;
use flux_isa_edge::vm::{ExecutionLimits, Vm};
use flux_isa_edge::sensor::pipeline::{Pipeline, PipelineConfig, PipelineResult};
use flux_isa_edge::sensor::SensorSource;
use flux_isa_edge::sensor::sonar::{SonarConfig, SonarSensor, mackenzie_sound_speed, francois_garrison_absorption};
use flux_isa_edge::plato::sync::PlatoCache;
// use flux_isa_edge::server; // available for server integration tests
use flux_isa_edge::config::Config;
use tokio::sync::mpsc;
use uuid::Uuid;

// ── Opcode tests ──────────────────────────────────────

#[test]
fn test_opcode_roundtrip() {
    for op in OpCode::all() {
        let byte = op.byte();
        let parsed = OpCode::from_byte(byte).unwrap();
        assert_eq!(*op, parsed, "roundtrip failed for {}", op);
    }
}

#[test]
fn test_opcode_display_fromstr() {
    for op in OpCode::all() {
        let s = op.to_string();
        let parsed: OpCode = s.parse().unwrap();
        assert_eq!(*op, parsed);
    }
}

#[test]
fn test_opcode_from_byte_invalid() {
    assert!(OpCode::from_byte(0xFF).is_none());
}

#[test]
fn test_opcode_from_str_invalid() {
    assert!("INVALID".parse::<OpCode>().is_err());
}

// ── Instruction encode/decode ─────────────────────────

#[test]
fn test_instruction_encode_decode() {
    let instr = Instruction::with_operand(OpCode::Push, 42.5);
    let bytes = instr.encode();
    let (decoded, consumed) = Instruction::decode(&bytes).unwrap();
    assert_eq!(consumed, 10);
    assert_eq!(decoded, instr);
}

#[test]
fn test_instruction_no_operand() {
    let instr = Instruction::new(OpCode::Halt);
    let bytes = instr.encode();
    let (decoded, consumed) = Instruction::decode(&bytes).unwrap();
    assert_eq!(consumed, 2);
    assert_eq!(decoded, instr);
}

// ── Bytecode encode/decode ────────────────────────────

#[test]
fn test_bytecode_roundtrip() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 10.0),
        Instruction::with_operand(OpCode::Push, 20.0),
        Instruction::new(OpCode::Add),
        Instruction::new(OpCode::Halt),
    ]);
    let bytes = bc.encode();
    let decoded = Bytecode::decode(&bytes).unwrap();
    assert_eq!(decoded.instructions.len(), 4);
    assert_eq!(decoded.instructions[2].opcode, OpCode::Add);
}

// ── VM execution tests ────────────────────────────────

#[tokio::test]
async fn test_vm_basic_arithmetic() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 10.0),
        Instruction::with_operand(OpCode::Push, 20.0),
        Instruction::new(OpCode::Add),
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![30.0]);
    assert_eq!(result.steps_executed, 3); // push, push, add (halt doesn't increment)
}

#[tokio::test]
async fn test_vm_validation_pass() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 50.0),   // value
        Instruction::with_operand(OpCode::Push, 0.0),    // min
        Instruction::with_operand(OpCode::Push, 100.0),  // max
        Instruction::new(OpCode::Validate),
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![1.0]); // valid
    assert_eq!(result.constraint_checks, 1);
    assert_eq!(result.violations, 0);
}

#[tokio::test]
async fn test_vm_validation_fail() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 150.0),  // value out of range
        Instruction::with_operand(OpCode::Push, 0.0),    // min
        Instruction::with_operand(OpCode::Push, 100.0),  // max
        Instruction::new(OpCode::Validate),
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success); // still halts normally
    assert_eq!(result.final_stack, vec![0.0]); // invalid
    assert_eq!(result.violations, 1);
}

#[tokio::test]
async fn test_vm_assert_fails() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 0.0), // false
        Instruction::new(OpCode::Assert),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(!result.success);
    assert!(result.error.unwrap().contains("assertion"));
}

#[tokio::test]
async fn test_vm_max_steps() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Jump, 0.0), // infinite loop
    ]);
    let limits = ExecutionLimits {
        max_steps: 100,
        ..Default::default()
    };
    let mut vm = Vm::new(limits);
    let result = vm.execute(&bc).await;
    assert!(!result.success);
    assert!(result.error.unwrap().contains("MaxSteps"));
}

#[tokio::test]
async fn test_vm_division_by_zero() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 10.0),
        Instruction::with_operand(OpCode::Push, 0.0),
        Instruction::new(OpCode::Div),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(!result.success);
    assert!(result.error.unwrap().contains("DivisionByZero"));
}

#[tokio::test]
async fn test_vm_clamp() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 150.0),
        Instruction::with_operand(OpCode::Push, 0.0),
        Instruction::with_operand(OpCode::Push, 100.0),
        Instruction::new(OpCode::Clamp),
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![100.0]);
}

#[tokio::test]
async fn test_vm_tolerance() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 100.1),  // value
        Instruction::with_operand(OpCode::Push, 100.0),  // expected
        Instruction::with_operand(OpCode::Push, 0.2),    // tolerance
        Instruction::new(OpCode::Tolerance),
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![1.0]); // within tolerance
}

#[tokio::test]
async fn test_vm_memory_load_store() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Push, 42.0),
        Instruction::with_operand(OpCode::Push, 0.0),
        Instruction::new(OpCode::Store),       // memory[0] = 42
        Instruction::with_operand(OpCode::Load, 0.0), // push memory[0]
        Instruction::new(OpCode::Halt),
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![42.0]);
}

#[tokio::test]
async fn test_vm_call_ret() {
    let bc = Bytecode::new(vec![
        Instruction::with_operand(OpCode::Call, 3.0), // call function at index 3
        Instruction::new(OpCode::Halt),               // index 1: halt after return
        Instruction::new(OpCode::Nop),                // index 2: filler
        Instruction::with_operand(OpCode::Push, 99.0), // index 3: function start
        Instruction::new(OpCode::Ret),                // index 4: return
    ]);
    let mut vm = Vm::with_defaults();
    let result = vm.execute(&bc).await;
    assert!(result.success);
    assert_eq!(result.final_stack, vec![99.0]);
}

// ── Sonar tests ───────────────────────────────────────

#[test]
fn test_mackenzie_sound_speed() {
    // Freshwater at surface, 10°C should be ~1447 m/s.
    let c = mackenzie_sound_speed(10.0, 0.0, 0.0);
    assert!(c > 1400.0 && c < 1500.0, "sound speed {} out of expected range", c);
}

#[test]
fn test_francois_garrison_absorption() {
    let alpha = francois_garrison_absorption(200.0, 10.0, 35.0, 100.0);
    // At 200 kHz, absorption should be positive and reasonable (tens of dB/km).
    assert!(alpha > 0.0, "absorption should be positive, got {}", alpha);
}

#[test]
fn test_sonar_validation_bytecode() {
    let config = SonarConfig::default();
    let sonar = SonarSensor::new(config);
    let bc = sonar.validation_bytecode();
    assert!(!bc.is_empty());
    assert_eq!(bc.label.as_deref(), Some("sonar-validation"));
}

#[tokio::test]
async fn test_sonar_sensor_reads() {
    let mut sonar = SonarSensor::simulated(SonarConfig::default());
    let data = sonar.read_sensor_data();
    assert!(!data.is_empty());
    assert!(data[0] >= sonar.config().min_range_m);
    assert!(data[0] <= sonar.config().max_range_m);
}

// ── PLATO cache tests ─────────────────────────────────

#[tokio::test]
async fn test_plato_cache_sync_and_query() {
    use flux_isa_edge::plato::client::Tile;
    let cache = PlatoCache::new();
    let tiles = vec![
        Tile {
            id: Uuid::new_v4(),
            room: "test".into(),
            content: "hello".into(),
            timestamp: 1,
            tags: vec![],
        },
    ];
    cache.sync_room("test", tiles).await;
    let result = cache.query_room("test").await;
    assert_eq!(result.len(), 1);
    assert_eq!(result[0].content, "hello");
}

#[tokio::test]
async fn test_plato_cache_local_tile() {
    use flux_isa_edge::plato::client::Tile;
    let cache = PlatoCache::new();
    let tile = Tile {
        id: Uuid::new_v4(),
        room: "local".into(),
        content: "local data".into(),
        timestamp: 2,
        tags: vec![],
    };
    cache.add_local(tile).await;
    let result = cache.query_room("local").await;
    assert_eq!(result.len(), 1);
    let pending = cache.drain_pending().await;
    assert_eq!(pending.len(), 1);
}

// ── Config tests ──────────────────────────────────────

#[test]
fn test_config_default() {
    let config = Config::default();
    assert!(config.node_id.starts_with("edge-"));
    assert_eq!(config.port, 9090);
}

// ── Pipeline integration test ─────────────────────────

struct MockSensor {
    name: String,
    counter: Arc<AtomicUsize>,
}

impl MockSensor {
    fn new(name: &str) -> Self {
        MockSensor { name: name.into(), counter: Arc::new(AtomicUsize::new(0)) }
    }
}

impl SensorSource for MockSensor {
    fn read_sensor_data(&mut self) -> Vec<f64> {
        let v = self.counter.fetch_add(1, Ordering::Relaxed) as f64;
        vec![v]
    }
    fn sensor_name(&self) -> &str { &self.name }
}

#[tokio::test]
async fn test_pipeline_processes_batches() {
    let sensor = MockSensor::new("mock");
    let bc = Bytecode::new(vec![
        Instruction::new(OpCode::Input),
        Instruction::with_operand(OpCode::Push, 0.0),
        Instruction::with_operand(OpCode::Push, 1000.0),
        Instruction::new(OpCode::Validate),
        Instruction::new(OpCode::Halt),
    ]);
    let config = PipelineConfig {
        batch_size: 4,
        ..Default::default()
    };
    let limits = ExecutionLimits::default();
    let (tx, mut rx) = mpsc::channel::<PipelineResult>(16);
    let (shutdown_tx, shutdown_rx) = tokio::sync::watch::channel(false);

    let pipeline = Pipeline::new(sensor, bc, config, limits);
    let handle = tokio::spawn(async move {
        pipeline.run(tx, shutdown_rx).await;
    });

    // Let it run briefly.
    tokio::time::sleep(std::time::Duration::from_millis(200)).await;
    shutdown_tx.send(true).unwrap();
    let _ = handle.await;

    // Should have received at least one result.
    let mut count = 0;
    while let Ok(r) = rx.try_recv() {
        count += 1;
        assert!(r.passed);
    }
    assert!(count > 0, "expected at least one pipeline result");
}
