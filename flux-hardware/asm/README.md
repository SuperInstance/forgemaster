# flux-asm

**FLUX bytecode assembler and disassembler.**

Two-pass assembly with label support, hex operands, comments, and roundtrip disassembly for the 43-opcode FLUX constraint VM.

## Usage

```bash
# Assemble
python -m flux_asm program.fxasm -o program.flux

# Disassemble  
python -m flux_asm -d program.flux

# Self-test
python -m flux_asm
```

## Example

```asm
# eVTOL altitude check
PUSH 100        # altitude value
PUSH 0          # min
CMP_GE          # altitude >= 0?
JFAIL fail      # no -> trap
PUSH 15000      # max  
CARRY_LT        # altitude < max
ASSERT          # fail if out of range
HALT
fail:
GUARD_TRAP
```

## Install

```bash
pip install flux-asm
```

## License

MIT
