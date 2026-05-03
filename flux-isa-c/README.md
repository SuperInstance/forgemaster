# FLUX ISA — C99 Virtual Machine

Edge-deployable constraint VM. Zero dependencies, pure C99.

## Build

```sh
make                # builds libflux.a and libflux.so
make test           # builds and runs unit tests
make clean          # remove build artifacts
```

Requires `gcc` or `clang` with C99 support.

## API Overview

### Opcodes

| Category    | Opcodes |
|-------------|---------|
| Arithmetic  | `ADD`(0x01) `SUB`(0x02) `MUL`(0x03) `DIV`(0x04) `MOD`(0x05) |
| Constraints | `ASSERT`(0x10) `CHECK`(0x11) `VALIDATE`(0x12) `REJECT`(0x13) |
| Control     | `JUMP`(0x20) `BRANCH`(0x21) `CALL`(0x22) `RETURN`(0x23) `HALT`(0x24) |
| Stack/Mem   | `LOAD`(0x30) `STORE`(0x31) `PUSH`(0x32) `POP`(0x33) `SWAP`(0x34) |
| Precision   | `SNAP`(0x40) `QUANTIZE`(0x41) `CAST`(0x42) `PROMOTE`(0x43) |
| Logic       | `AND`(0x50) `OR`(0x51) `NOT`(0x52) `XOR`(0x53) |
| Comparison  | `EQ`(0x60) `NEQ`(0x61) `LT`(0x62) `GT`(0x63) `LTE`(0x64) `GTE`(0x65) |
| Debug       | `NOP`(0x70) `DEBUG`(0x71) `TRACE`(0x72) `DUMP`(0x73) |

### VM Lifecycle

```c
flux_vm_t vm;
flux_vm_init(&vm, 0);           // 0 = default trace buffer (1024 entries)

flux_result_t result;
flux_vm_execute(&vm, &bytecode, &result);

// Use result.outputs[], result.constraints_satisfied, result.trace[]

free(result.trace);             // you own the trace memory
flux_vm_destroy(&vm);
```

### Bytecode Builder

```c
flux_bytecode_t bc;
flux_bytecode_init(&bc, 16);

flux_instruction_t push = {
    .opcode = FLUX_PUSH,
    .operand_count = 2,
    .operands = {10.0, 20.0}
};
flux_bytecode_push(&bc, &push);
flux_bytecode_push(&bc, &(flux_instruction_t){.opcode = FLUX_ADD});
flux_bytecode_push(&bc, &(flux_instruction_t){.opcode = FLUX_SNAP});
flux_bytecode_push(&bc, &(flux_instruction_t){.opcode = FLUX_HALT});

// ... execute ...

flux_bytecode_free(&bc);
```

### Binary Encode/Decode

```c
uint8_t *buf;
size_t len = flux_bytecode_encode(&bc, &buf);
// write buf to file, send over network, etc.

flux_bytecode_t bc2;
flux_bytecode_decode(buf, len, &bc2);
// bc2 is now usable

free(buf);
flux_bytecode_free(&bc2);
```

Binary format: `FLUX` magic (0x464C5558) + version header + instruction stream.

### Disassembly

```c
// Single instruction
char line[256];
flux_disassemble(&inst, line, sizeof(line));

// Entire bytecode
char *text = flux_disassemble_all(&bc);
printf("%s", text);
free(text);
```

## Architecture

- **Stack**: 256-entry `double` stack
- **Call stack**: 64-entry depth
- **Registers**: 16 general-purpose `double` registers (LOAD/STORE)
- **Trace buffer**: configurable, default 1024 entries
- **Outputs**: dynamically grown output stream via SNAP/DUMP

## Return Codes

| Code | Meaning |
|------|---------|
| 0    | Success |
| -1   | Stack overflow/underflow or invalid state |
| -2   | Division by zero |
| -3   | Call stack overflow |
| -4   | Call stack underflow (RETURN with empty call stack) |
| -5   | Unknown opcode |

## License

Part of the SuperInstance / FLUX project.
