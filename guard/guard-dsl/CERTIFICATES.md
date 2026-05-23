# GUARD Proof Certificates

Every compiled GUARD module produces a **Proof Certificate** alongside its FLUX bytecode. The certificate is a standalone artifact that can be verified independently of the compiler, using only the module source and the certificate itself.

## Design Goals

1. **Independence** — A safety auditor can verify the certificate with a small, trusted checker (≈ 500 lines of Rust).
2. **Reproducibility** — The same source + compiler version always yields the same certificate hash.
3. **Granularity** — Certificates are per-module, per-proof-declaration, so partial verification is possible.
4. **Traceability** — Every bytecode instruction maps back to a source range.

## Certificate Format (Native)

```json
{
  "certificate_format": "guard-native-v1",
  "module": "ThrottleLimit",
  "version": "1.0.0",
  "compiler": {
    "name": "guardc",
    "version": "1.0.0-ship",
    "target": "flux-isa-43"
  },
  "source_hash": "sha256:9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "bytecode_hash": "sha256:a3c5f1e...",
  "proofs": [
    {
      "proof_id": "ThrottleSafetyProof",
      "tactics": ["interval_arithmetic", "bit_blast"],
      "status": "verified",
      "verification_time_ms": 47,
      "obligations": [
        {
          "obligation_id": "inv-01",
          "kind": "invariant_preservation",
          "name": "ThrottleMustNotExceedMax",
          "source_span": "throttle.guard:13:3-15:19",
          "vc": {
            "logic": "QF_LRA",
            "formula": "(assert (<= throttle_command 1.0))",
            "status": "sat"
          },
          "trace_digest": "sha256:bb12a9...",
          "counterexample": null
        },
        {
          "obligation_id": "inv-02",
          "kind": "invariant_preservation",
          "name": "ThrottleMustNotReverse",
          "source_span": "throttle.guard:18:3-20:19",
          "vc": {
            "logic": "QF_LRA",
            "formula": "(assert (>= throttle_command 0.0))",
            "status": "sat"
          },
          "trace_digest": "sha256:cc23b0...",
          "counterexample": null
        },
        {
          "obligation_id": "der-01",
          "kind": "derived_rule_sanity",
          "name": "PositiveThrottleImpliesEngineEnabled",
          "source_span": "throttle.guard:24:1-27:30",
          "vc": {
            "logic": "QF_LIA",
            "formula": "(assert (=> (> throttle_command 0.0) engine_enabled))",
            "status": "sat"
          },
          "trace_digest": "sha256:dd34c1...",
          "counterexample": null
        }
      ],
      "merkle_root": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  ],
  "metadata": {
    "generated_at": "2026-05-03T08:35:51Z",
    "host_os": "linux-x86_64",
    " deterministic": true
  }
}
```

## Field Semantics

| Field | Meaning |
|-------|---------|
| `source_hash` | SHA-256 of the canonicalized source text (UTF-8, LF-only, no trailing whitespace). |
| `bytecode_hash` | SHA-256 of the emitted FLUX bytecode object. |
| `proofs` | One entry per `proof { ... }` block in the source. |
| `obligations` | Individual Verification Conditions (VCs). Each invariant and derived rule generates at least one. |
| `vc.logic` | SMT-LIB logic used (e.g., `QF_LRA` for quantifier-free linear real arithmetic, `QF_BV` for bit-vectors). |
| `vc.status` | `sat` = no counterexample found (property holds), `unsat` = counterexample exists (property violated), `unknown` = solver timeout. |
| `trace_digest` | Hash of the symbolic execution trace that established this obligation. Used for incremental verification. |
| `counterexample` | Concrete assignment to state variables that violates the VC, if `status` is `unsat`. Null otherwise. |
| `merkle_root` | Merkle tree root of all `trace_digest` values in this proof. Tamper-evident seal. |

## Verification Condition Kinds

| Kind | Description |
|------|-------------|
| `invariant_preservation` | Does the invariant hold in all reachable states? |
| `invariant_initiation` | Does the invariant hold in the initial state? |
| `derived_rule_sanity` | Is the derived rule logically entailed by its premises? |
| `temporal_liveness` | Does an `eventually` property eventually occur? |
| `temporal_safety` | Does an `always` property hold forever? |
| `unit_consistency` | Are all operations dimensionally consistent? |
| `domain_membership` | Can any variable leave its declared domain? |

## Merkle Tree Construction

The Merkle root provides a compact, tamper-evident summary of the entire proof:

```
leaf_i = SHA-256( obligation_id || trace_digest )
parent = SHA-256( left || right )
root   = reduce(leaves, parent_fn)
```

If **any** obligation is recomputed with a different solver or different bounds, its `trace_digest` changes, and the `merkle_root` changes. This lets auditors detect regressions with a single hash comparison.

## Counterexample Format

When a property fails, the certificate includes a concrete counterexample that a safety engineer can inspect:

```json
"counterexample": {
  "model": {
    "throttle_command": 1.07,
    "engine_enabled": false
  },
  "time_step": 0,
  "violated_invariant": "ThrottleMustNotExceedMax",
  "explanation": "At time step 0, throttle_command = 1.07 (107 %), which exceeds the maximum of 100 %."
}
```

## Trusted Computing Base (TCB)

The certificate verifier has a minimal TCB:

1. **SHA-256** implementation (or Blake3, if selected).
2. **SMT solver** (Z3, cvc5, or Bitwuzla) for re-checking VCs.
3. **FLUX VM** (≈ 300 lines) for executing the bytecode trace.
4. **Source parser** (≈ 200 lines) for confirming source-to-bytecode mapping.

The GUARD compiler itself is **not** in the TCB. A malicious or buggy compiler cannot forge a valid certificate because the verifier re-runs the proof obligations independently.

## Certificate Lifecycle

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  GUARD Source │ ──► │   guardc     │ ──► │ FLUX Bytecode│
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Prover     │  (SMT + symbolic exec)
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │  Certificate │  (.guardcert)
                     └──────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Verifier   │  (auditor / CI)
                     └──────────────┘
```
