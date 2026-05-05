# FLUX-C Bytecode Signing Design

**Status:** Draft  
**Author:** Forgemaster ⚒️  
**Date:** 2025-05-05  

## Overview

FLUX-C bytecode executes on constrained embedded hardware. Unsigned bytecode is a security liability — any malicious actor with bus access can inject arbitrary opcodes and escape the VM sandbox. This document specifies an Ed25519-based signing and verification system that ensures only authorized bytecode runs on FLUX hardware.

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Bytecode tampering (MITM, flash corruption) | Ed25519 signature verification |
| Replay of old (vulnerable) bytecode | Monotonic version counter + nonce |
| Key extraction from device | Keys never leave HSM/secure enclave |
| Supply-chain attack on compiler | Signing keys held by release engineering only |
| Denial of service via invalid signatures | Fast Ed25519 verify (<1ms on target) |

## Signing Flow

```
┌─────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│ FLUX-C  │────▶│ Bytecode  │────▶│  Sign     │────▶│ Signed  │
│ Compiler│     │ Validator │     │  Tool     │     │ Bundle  │
└─────────┘     └──────────┘     └──────────┘     └─────────┘
                     │                                  │
                 validate()                      ┌──────┴──────┐
                 (reject if                       │  Header     │
                  invalid)                        │  Bytecode   │
                                                 │  Signature  │
                                                 │  Version    │
                                                 │  Nonce      │
                                                 └─────────────┘
```

### Steps

1. **Compile** FLUX-C source to raw bytecode
2. **Validate** bytecode through `bytecode_validator::validate()` — reject if invalid
3. **Hash** the validated bytecode with BLAKE2b-256 (faster than SHA-256 on embedded)
4. **Sign** the hash with Ed25519 using the release private key
5. **Bundle** into a signed container format

## Signed Bundle Format

```
┌──────────────────────────────────────────┐
│ Magic:   [0x46, 0x4C, 0x58, 0x53]       │  "FLXS" — 4 bytes
│ Version: u16 LE                          │  Bundle format version (currently 1)
│ Flags:   u16 LE                          │  Bit 0: compressed, Bit 1: debug_info
│ BC Len:  u32 LE                          │  Bytecode length in bytes
│ BC Hash: [u8; 32]                        │  BLAKE2b-256 of bytecode
│ Nonce:   [u8; 16]                        │  Random nonce for replay protection
│ Counter: u64 LE                          │  Monotonic version counter
│ Key ID:  u8                              │  Which public key to use (0-255)
│ Reserved: [u8; 7]                        │  Padding / future use
│ ─────────────────────────────────────────│
│ Bytecode: [u8; BC_LEN]                   │  The actual bytecode
│ ─────────────────────────────────────────│
│ Signature: [u8; 64]                      │  Ed25519 signature over header + bytecode
└──────────────────────────────────────────┘
```

**Total overhead:** 4 + 2 + 2 + 4 + 32 + 16 + 8 + 1 + 7 + 64 = **140 bytes**

## Verification Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌─────────┐
│  Signed  │────▶│  Parse    │────▶│  Verify  │────▶│ Execute │
│  Bundle  │     │  Header   │     │  Sig     │     │ on VM   │
└──────────┘     └──────────┘     └──────────┘     └─────────┘
                      │                │
                  parse magic      Ed25519 verify
                  check version    hash check
                  read fields      counter > last_seen
                                   then validate()
```

### Steps

1. **Parse** the bundle header — validate magic bytes, version, field ranges
2. **Extract** bytecode and signature
3. **Verify counter** — must be strictly greater than the last-seen counter for this key ID (prevents replay)
4. **Verify signature** — Ed25519 verify(header || bytecode, signature, public_key[key_id])
5. **Validate** — run `bytecode_validator::validate()` on the extracted bytecode
6. **Execute** — load into VM only if all checks pass

### Failure Modes

| Failure | Action |
|---------|--------|
| Bad magic | Reject immediately, log tamper event |
| Unknown version | Reject (forward compat not guaranteed) |
| Bad signature | Reject, increment tamper counter, potentially lockout |
| Counter ≤ last_seen | Reject (replay detected) |
| Validation failure | Reject (invalid bytecode even if signed) |

## Key Management

### Key Hierarchy

```
Root Key (offline, HSM)
  ├── Release Key 0 (active signing)
  ├── Release Key 1 (rotation备用)
  └── Revocation Key (emergency key rotation)
```

### Key Rotation

- Each device stores up to 4 public keys in OTP fuses
- Key ID in bundle header selects which key to verify against
- Rotation procedure:
  1. Sign new bytecode with both old and new keys (transition period)
  2. Deploy update signed with new key
  3. After all devices updated, revoke old key
- Emergency: Revocation key can push a "key revoke" bundle that invalidates a compromised key ID

### Key Storage

| Location | Keys | Protection |
|----------|------|-----------|
| Signing workstation | Private release key | HSM (YubiHSM2 or equivalent) |
| Build server | None (signing is offline) | Air-gapped signing ceremony |
| FLUX device | Public keys (up to 4) | OTP fuses / secure enclave |
| Backup | Encrypted private key backup | Offline, physical safe |

## Replay Protection

### Monotonic Counter

- Each (key_id, counter) pair must be strictly increasing
- Device stores the highest-seen counter per key ID in persistent memory
- Counter is u64 — sufficient for >584 billion updates at 1 update/second for 18,000 years
- On counter overflow: force key rotation

### Nonce

- 16-byte random nonce per bundle
- Prevents identical bytecode from producing identical bundles
- Not checked by verifier — exists solely for signature diversity

## Integration with FLUX-C Toolchain

### Compiler Integration

```bash
# Compile and sign in one step
fluxc compile --input constraints.fc --output constraints.fxb --sign --key-id 0

# Validate only (no signing)
fluxc validate --input constraints.fxb

# Verify signature
fluxc verify --input constraints.fxb --public-key keys/pub0.ed25519
```

### Build Pipeline

```yaml
# CI/CD integration
- name: Compile FLUX-C
  run: fluxc compile --input src/constraints.fc --output build/constraints.raw

- name: Validate bytecode
  run: fluxc validate --input build/constraints.raw

- name: Sign bytecode (offline ceremony)
  # This step runs on the air-gapped signing workstation
  run: fluxc sign --input build/constraints.raw --output release/constraints.fxb --key-id 0 --counter $(cat .last-counter)
```

### Runtime Integration

```rust
// In the FLUX VM bootloader
fn load_bytecode(bundle: &[u8]) -> Result<ValidatedProgram, LoadError> {
    // 1. Parse and verify signature
    let parsed = SignedBundle::parse(bundle)?;
    let pubkey = get_public_key(parsed.key_id())?;
    parsed.verify(&pubkey, &mut counter_store)?;
    
    // 2. Validate bytecode safety
    let info = bytecode_validator::validate(parsed.bytecode())?;
    
    // 3. Update monotonic counter
    counter_store.set(parsed.key_id(), parsed.counter());
    
    Ok(ValidatedProgram {
        bytecode: parsed.bytecode().to_vec(),
        info,
    })
}
```

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Signature verification | < 1ms | Ed25519 on Cortex-M7 @ 480MHz |
| Bundle parsing | < 100µs | Simple header extraction |
| Bytecode validation | < 500µs | Typical ~100 instruction program |
| Total load time | < 2ms | End-to-end from flash to VM ready |

## Open Questions

1. **Ed25519 or Ed25519-BLAKE2?** — Ed25519 (SHA-512 based) is more widely supported. Ed25519-BLAKE2 is faster but less standard. Recommendation: stick with standard Ed25519.
2. **Multi-signature support?** — Require M-of-N signatures for critical infrastructure? Adds complexity but improves security. Recommendation: defer to v2.
3. **Certificate transparency?** — Publish all signed bundle hashes to an append-only log for audit. Recommendation: defer to v2.

## References

- [RFC 8032: Ed25519](https://datatracker.ietf.org/doc/html/rfc8032)
- [BLAKE2 specification](https://www.blake2.net/)
- `bytecode_validator.rs` — FLUX-C bytecode validation implementation
