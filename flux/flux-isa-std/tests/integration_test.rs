use flux_isa_std::bytecode::{FluxBytecode, BytecodeMetadata};
use flux_isa_std::gate::{GateConfig, GateVerdict, QualityGate};
use flux_isa_std::instruction::FluxInstruction;
use flux_isa_std::opcode::FluxOpCode;
use flux_isa_std::pipeline::{Pipeline, PipelineConfig};
use flux_isa_std::sonar_physics;
use flux_isa_std::vm::{FluxVM, VMConfig};

fn make_push(val: f64) -> FluxInstruction {
    FluxInstruction::new(FluxOpCode::Push).with_operand(val)
}

#[test]
fn test_compile_and_execute_roundtrip() {
    // Program: push 10, push 20, add, push 5, mul, print, halt
    let instructions = vec![
        make_push(10.0),
        make_push(20.0),
        FluxInstruction::new(FluxOpCode::Add),
        make_push(5.0),
        FluxInstruction::new(FluxOpCode::Mul),
        FluxInstruction::new(FluxOpCode::Print),
        FluxInstruction::new(FluxOpCode::Halt),
    ];

    let bytecode = FluxBytecode::new(instructions);
    let encoded = bytecode.encode();

    let decoded = FluxBytecode::decode(&encoded).expect("decode should succeed");
    assert_eq!(decoded.instructions.len(), 7);

    let mut vm = FluxVM::with_default_config();
    vm.execute_bytecode(&decoded).expect("execution should succeed");
    assert_eq!(vm.stack().len(), 0); // print pops
    assert_eq!(vm.output(), &["150"]);
}

#[test]
fn test_file_persistence() {
    let path = "/tmp/flux_test_persistence.flux";

    let instructions = vec![
        make_push(42.0),
        FluxInstruction::new(FluxOpCode::Dup),
        FluxInstruction::new(FluxOpCode::Add),
        FluxInstruction::new(FluxOpCode::Halt),
    ];
    let bc = FluxBytecode::new(instructions)
        .with_metadata(BytecodeMetadata {
            created: "2026-05-02".into(),
            source: Some("test".into()),
            author: Some("test".into()),
        });

    bc.save_to_file(path).expect("save should work");
    let loaded = FluxBytecode::load_from_file(path).expect("load should work");
    assert_eq!(loaded.instructions.len(), 4);

    let mut vm = FluxVM::with_default_config();
    vm.execute_bytecode(&loaded).expect("exec should work");
    assert_eq!(vm.stack(), &[84.0]);

    // Cleanup
    let _ = std::fs::remove_file(path);
}

#[test]
fn test_json_serialization() {
    let bc = FluxBytecode::new(vec![
        make_push(1.0),
        make_push(2.0),
        FluxInstruction::new(FluxOpCode::Add),
        FluxInstruction::new(FluxOpCode::Halt),
    ]);
    let json = bc.to_json().expect("json serialize");
    let restored = FluxBytecode::from_json(&json).expect("json deserialize");
    assert_eq!(restored.instructions.len(), 4);
}

#[test]
fn test_sonar_physics_values() {
    // Standard ocean: 15°C, 35 PSU, 0m depth → ~1500 m/s
    let c = sonar_physics::sound_speed(15.0, 35.0, 0.0);
    assert!((c - 1500.0).abs() < 15.0, "Sound speed {} not near 1500", c);

    // Wavelength at 12 kHz
    let wl = sonar_physics::wavelength(12.0, 15.0, 35.0, 0.0);
    assert!(wl > 0.10 && wl < 0.14, "Wavelength {} out of range", wl);

    // Travel time: 1500m ≈ 1s
    let tt = sonar_physics::travel_time(1500.0, 15.0, 35.0, 0.0);
    assert!((tt - 1.0).abs() < 0.05, "Travel time {} not near 1.0", tt);

    // Absorption should be positive
    let a = sonar_physics::absorption(50.0, 0.0, 15.0, 35.0);
    assert!(a >= 0.0, "Absorption should be non-negative");
}

#[test]
fn test_gate_rejection() {
    let gate = QualityGate::with_default_config();

    // Too short
    match gate.check("hi") {
        GateVerdict::Reject(_) => {}
        GateVerdict::Accept => panic!("Should reject short content"),
    }

    // Absolute claim
    match gate.check("This definitely proves the theory is correct") {
        GateVerdict::Reject(_) => {}
        GateVerdict::Accept => panic!("Should reject absolute claims"),
    }

    // Valid content
    match gate.check("The constraint solver found a feasible solution region") {
        GateVerdict::Accept => {}
        GateVerdict::Reject(r) => panic!("Should accept: {}", r),
    }
}

#[test]
fn test_gate_with_required_fields() {
    let config = GateConfig {
        min_length: 5,
        required_fields: vec!["tile_id".into(), "value".into()],
        ..Default::default()
    };
    let gate = QualityGate::new(config);

    match gate.check("tile_id:42, value:3.14, this is valid data") {
        GateVerdict::Accept => {}
        GateVerdict::Reject(r) => panic!("Should accept: {}", r),
    }

    match gate.check("some data without required fields at all") {
        GateVerdict::Reject(_) => {}
        GateVerdict::Accept => panic!("Should reject missing fields"),
    }
}

#[test]
fn test_pipeline_batch() {
    let mut pipeline = Pipeline::new(PipelineConfig::default());

    let bc1 = FluxBytecode::new(vec![
        make_push(10.0),
        make_push(20.0),
        FluxInstruction::new(FluxOpCode::Add),
        FluxInstruction::new(FluxOpCode::Halt),
    ]);
    let bc2 = FluxBytecode::new(vec![
        make_push(5.0),
        make_push(3.0),
        FluxInstruction::new(FluxOpCode::Mul),
        FluxInstruction::new(FluxOpCode::Halt),
    ]);

    let results = pipeline.process_batch(&[bc1, bc2]);
    assert_eq!(results.len(), 2);
    assert!(results[0].success);
    assert!(results[1].success);
    assert_eq!(results[0].stack, vec![30.0]);
    assert_eq!(results[1].stack, vec![15.0]);
}

#[test]
fn test_vm_call_ret() {
    let instructions = vec![
        make_push(5.0),        // 0: push 5
        FluxInstruction::new(FluxOpCode::Call).with_operand(4.0), // 1: call subroutine at 4
        FluxInstruction::new(FluxOpCode::Halt), // 2: halt
        FluxInstruction::new(FluxOpCode::Nop),  // 3: padding
        make_push(10.0),       // 4: subroutine start — push 10
        FluxInstruction::new(FluxOpCode::Add),  // 5: add
        FluxInstruction::new(FluxOpCode::Ret),  // 6: return
    ];

    let mut vm = FluxVM::with_default_config();
    vm.execute_instructions(instructions).expect("exec");
    assert_eq!(vm.stack(), &[15.0]);
}

#[test]
fn test_vm_comparison() {
    let instructions = vec![
        make_push(10.0),
        make_push(10.0),
        FluxInstruction::new(FluxOpCode::Eq),
        FluxInstruction::new(FluxOpCode::Halt),
    ];
    let mut vm = FluxVM::with_default_config();
    vm.execute_instructions(instructions).expect("exec");
    assert_eq!(vm.stack(), &[1.0]);
}

#[test]
fn test_vm_memory_ops() {
    let instructions = vec![
        make_push(42.0),
        FluxInstruction::new(FluxOpCode::Store).with_operand(0.0), // store to addr 0
        make_push(99.0),
        FluxInstruction::new(FluxOpCode::Store).with_operand(1.0), // store to addr 1
        FluxInstruction::new(FluxOpCode::LoadConst).with_operand(0.0), // push addr 0
        FluxInstruction::new(FluxOpCode::Load), // load from addr 0
        FluxInstruction::new(FluxOpCode::Halt),
    ];
    let mut vm = FluxVM::with_default_config();
    vm.execute_instructions(instructions).expect("exec");
    assert_eq!(vm.stack()[0], 42.0);
}

#[test]
fn test_vm_assertion_fail() {
    let instructions = vec![
        make_push(0.0), // false
        FluxInstruction::new(FluxOpCode::Assert),
    ];
    let mut vm = FluxVM::with_default_config();
    let result = vm.execute_instructions(instructions);
    assert!(result.is_err());
}

#[test]
fn test_step_execution() {
    let instructions = vec![
        make_push(1.0),
        make_push(2.0),
        FluxInstruction::new(FluxOpCode::Add),
        FluxInstruction::new(FluxOpCode::Halt),
    ];
    let mut vm = FluxVM::with_default_config();
    vm.load_instructions(instructions);
    // Not calling execute — manual stepping
    assert!(vm.step().unwrap()); // push 1
    assert_eq!(vm.stack(), &[1.0]);
    assert!(vm.step().unwrap()); // push 2
    assert!(vm.step().unwrap()); // add
    assert_eq!(vm.stack(), &[3.0]);
    assert!(!vm.step().unwrap()); // halt → done
    assert!(!vm.step().unwrap()); // still done
}

#[test]
fn test_tracing() {
    let mut config = VMConfig::default();
    config.trace_enabled = true;
    let mut vm = FluxVM::new(config);
    let instructions = vec![
        make_push(1.0),
        make_push(2.0),
        FluxInstruction::new(FluxOpCode::Add),
        FluxInstruction::new(FluxOpCode::Halt),
    ];
    vm.execute_instructions(instructions).expect("exec");
    assert_eq!(vm.trace().len(), 3); // 3 instructions traced (halt returns early)
}

#[test]
fn test_all_opcodes_encode_decode() {
    let opcodes: Vec<FluxOpCode> = vec![
        FluxOpCode::Push, FluxOpCode::Pop, FluxOpCode::Dup, FluxOpCode::Swap,
        FluxOpCode::Over, FluxOpCode::Rot, FluxOpCode::Depth,
        FluxOpCode::Add, FluxOpCode::Sub, FluxOpCode::Mul, FluxOpCode::Div,
        FluxOpCode::Mod, FluxOpCode::Negate, FluxOpCode::Abs,
        FluxOpCode::And, FluxOpCode::Or, FluxOpCode::Not, FluxOpCode::Xor, FluxOpCode::Shl,
        FluxOpCode::Eq, FluxOpCode::Ne, FluxOpCode::Lt, FluxOpCode::Gt,
        FluxOpCode::Le, FluxOpCode::Ge,
        FluxOpCode::Jmp, FluxOpCode::Call, FluxOpCode::Ret, FluxOpCode::Halt, FluxOpCode::Nop,
        FluxOpCode::Load, FluxOpCode::Store, FluxOpCode::LoadConst,
        FluxOpCode::Assert, FluxOpCode::Check,
        FluxOpCode::Print, FluxOpCode::Emit,
    ];
    assert_eq!(opcodes.len(), 37, "Expected 37 opcodes");
    for opcode in &opcodes {
        let byte = opcode.to_byte();
        let restored = FluxOpCode::from_byte(byte);
        assert_eq!(restored, Some(*opcode), "Roundtrip failed for {:?}", opcode);
    }
}
