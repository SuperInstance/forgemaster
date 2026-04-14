# 🔒 Brig — Failed Experiments & Lessons

## Entry 001: OOM Massacre (2026-04-14)

**What happened**: Fired 4 Claude Code agents simultaneously, all running `cargo check`. WSL2 ran out of memory. Agents 3 and 4 got SIGKILL. Lost the vector search source files entirely.

**Root cause**: Each `cargo check` with `constraint-theory-core` dependency compiles the full dependency tree. 4 parallel compilations = 4× RAM usage. On 8GB shared WSL2, that's fatal.

**Fix**: Max 2 concurrent builds. Serialize cargo operations. Write code in parallel (Pi agents on remote Groq), compile one at a time (local).

**Rigging rule**: `MAX_CONCURRENT_BUILDS=2`

---

## Entry 002: Pi Generation Failure (2026-04-14)

**What happened**: Pi agent on Groq failed with "Failed to call a function. See 'failed_generation'" when asked to build the signal processing proof. No source files were written.

**Root cause**: Likely the prompt was too complex for llama-3.3-70b — chained IIR filters + constraint theory + real API adaptation in one shot.

**Fix**: Break complex tasks into smaller steps. First generate Cargo.toml + skeleton, then fill in logic. Or use Claude Code for complex architecture, Pi for simpler batch work.

**Rigging rule**: Pi handles well-scoped tasks. Claude handles complex multi-constraint tasks.

---

## Entry 003: Crate API Mismatch (2026-04-14)

**What happened**: Claude Code agents wrote code against a guessed API for constraint-theory-core. The real API is different:
- `PythagoreanManifold::new(density: usize)` not `new(tolerance: f64)`
- `snap([f32; 2])` returns `([f32; 2], f32)` not `Vec<f64>`

**Root cause**: The crate's README/docs describe a different API than what's actually exported. The agents inferred from doc strings.

**Fix**: Clone the actual crate, study the real `lib.rs`, then write proofs against the verified API.

**Rigging rule**: Verify APIs against source before writing proofs. Trust code, not docs.

---

## Entry 004: Git Lock File (2026-04-14)

**What happened**: Pi agent couldn't commit because `.git/index.lock` was left from a previous failed operation.

**Fix**: `rm -f .git/index.lock` before retrying.

**Rigging rule**: Always clean lock files after crashes.
