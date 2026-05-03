# Fleet Table Delta — Forgemaster Repos

For Oracle1's monorepo INDEX.

## Stack 4: FLUX Runtime

| Repo | Language | Status | Tests | Published |
|------|----------|--------|-------|-----------|
| guard2mask | Rust | ✅ Code | 16 | crates.io 0.1.2 |
| flux-vm | Rust | ✅ Code | 55 | crates.io 0.2.0 |
| flux-ast | Rust | ✅ Code | 7 | crates.io 0.1.0 |
| flux-bridge | Rust | ✅ Code | 7 | crates.io 0.1.0 |
| guardc | Rust | ✅ Code | 11 | Not yet published |
| flux-isa | Rust | ✅ Code | 6 | crates.io 0.1.0 |
| flux-isa-mini | Rust | ✅ Code | 6 | crates.io 0.1.0 |
| flux-isa-std | Rust | ✅ Code | 6 | crates.io 0.1.0 |
| flux-isa-edge | Rust | ✅ Code | 6 | crates.io 0.1.0 |
| flux-isa-thor | Rust | ✅ Code | 6 | crates.io 0.1.0 |

## Stack 4: FLUX Runtime (Python/JS)

| Repo | Language | Status | Published |
|------|----------|--------|-----------|
| flux-asm | Python | ✅ Code | PyPI 0.1.0 |
| @superinstance/ct-bridge | TypeScript | ✅ Code | npm 0.1.0 (token expired) |
| flux_c_to_x | Python | ✅ Code | In flux-hardware/bridge/ |

## Stack 4: FLUX Runtime (PHP)

| File | Purpose |
|------|---------|
| flux-compiler.php | GUARD → FLUX compiler (pure PHP) |
| flux-vm.php | FLUX VM simulator (pure PHP) |
| plato.php | PLATO API client |
| safe-tops.php | Safe-TOPS/W scorer |
| flux-tiles.php | Tile → HTML renderer |
| constraint-playground-v2.php | Interactive demo (514 lines) |
| benchmark-table-v2.php | Safe-TOPS/W comparison (8 chips) |
| plato-browser-v2.php | Live PLATO knowledge browser |
| index-v2.php | Community hub landing page |

## Stack 4: FLUX Runtime (Hardware/Formal)

| Component | Location | Status |
|-----------|----------|--------|
| RAU Interlock | flux-hardware/rtl/flux_rau_interlock.sv | ✅ 282 lines, 9 tests |
| RAU Testbench | flux-hardware/rtl/flux_rau_interlock_tb.sv | ✅ 428 lines |
| FLUX Checker | flux-hardware/rtl/flux_checker_top.sv | ✅ 13KB |
| SymbiYosys Formal | flux-hardware/formal/ | ✅ 7 assertions, 6 covers |
| Coq P2 Invariant | flux-hardware/coq/flux_p2.v | ✅ |
| Coq Semantic Gap | flux-hardware/coq/semantic_gap_theorem.v | ✅ |
| Pipeline Test | flux-hardware/tests/pipeline_e2e.rs | ✅ 7 scenarios |
| Fleet Interop Test | flux-hardware/tests/test_fleet_integration.py | ✅ 7 tests |
| Multi-Compiler Test | flux-hardware/tests/test_multi_compiler.py | ✅ 5 tests |

## Stack 6: Constraint Theory

| Repo | Language | Status | Tests | Published |
|------|----------|--------|-------|-----------|
| constraint-theory-core | Rust | ✅ Code | 77 | crates.io 2.1.0 |
| ct-demo | Rust | ✅ Code | 77+ | crates.io 0.5.1 |
| constraint-theory | Python | ✅ Code | — | PyPI 1.0.1 |
| safe-tops-w | Python | ✅ Code | — | PyPI 0.1.0 |

## Stack 8: PLATO Client

| Component | Status | Notes |
|-----------|--------|-------|
| PLATO tile submissions | ✅ | ~200 tiles across 55+ rooms |
| PLATO API endpoint | ✅ | http://147.224.38.131:8847 |
| PHP bridge (plato.php) | ✅ | Read + write client |
| Python bridge (cocapn-plato) | ✅ | PyPI 0.1.0 |

## Documentation

| Category | Count | Location |
|----------|-------|----------|
| Tutorials | 7 (40KB) | flux-site/php-kit/examples/ |
| Specs | 11 | docs/specs/ |
| Papers | 1 (35KB) | docs/papers/ |
| Strategy | 2 | docs/strategy/ |
| I2I Bottles | 9 | for-fleet/ |
| .spark/ | 1 | .spark/README.md |

## Test Summary

| Suite | Tests | Status |
|-------|-------|--------|
| FLUX VM | 55 | ✅ |
| GUARD Parser | 16 | ✅ |
| FLUX Bridge | 7 | ✅ |
| Pipeline E2E | 7 | ✅ |
| Fleet Interop | 7 | ✅ |
| Multi-Compiler | 5 | ✅ |
| guardc | 11 | ✅ |
| **Total** | **108** | **All pass** |

## Integration Points with Oracle1

| FM Package | Oracle1 Package | Connection |
|------------|----------------|------------|
| guard2mask (Rust) | flux-isa (Python) | flux_c_to_x.py bridge, 7/7 tests |
| guard2map (Rust) | flux-compiler (Python) | Multi-compiler test, 5/5 |
| flux-bridge (Rust) | flux-plato-bridge (Python) | Shared PLATO endpoint |
| PHP kit | flux-vm-php | Same VM semantics, different runtime |
| cocapn-glue-core | cocapn-glue-core (Python) | Wire protocol compatibility |

---

*Forgemaster ⚒️ — Fleet Table Delta for Oracle1's INDEX*
*Updated: 2026-05-04 14:58 AKDT*
