---
# CRITICAL ARCHITECTURE REVIEW: FLUX COMPILER
*Reviewer: 20 year GCC/CompCert safety certification engineer. I have signed off compiler safety cases for commercial aircraft. I will not pull punches.*

First, the unvarnished opening assessment:
> What you have described is an extremely promising research compiler. It is 0% production ready for safety-critical systems. Right now I would not trust this compiler to operate a toaster, let alone flight controls. You have solved the fun computer science parts. You have not even started on the 90% of the work that actually matters for safety.

Every assumption below is challenged. No polite academic hedging.

---

## 1. CRITICAL MISSING COMPONENTS
You listed 7 correctness theorems. None of them matter for certification. This is what is actually missing, ordered by severity:
1.  **Formal GUARD language semantics**
    You wrote a parser before you wrote the specification of the language. This is backwards, always. All your theorems are almost certainly proven over ideal mathematical integers/reals. There is zero specification for: overflow behaviour, rounding mode, NaN propagation, trap semantics, alignment, partial evaluation, or error termination. For DAL A this is an immediate disqualification. No regulator will even look at you without this.
2.  **Verified parser**
    A hand-written recursive descent parser for safety critical systems is professional malpractice. I have personally seen three separate Airbus compiler qualification failures caused by un-audited edge cases in hand written parsers. There is no way to prove that this parser correctly accepts exactly valid GUARD and rejects all invalid input. You will never get this past an auditor.
3.  **Bidirectional traceability**
    There is no proven, auditable link between every single bit of generated output back to the exact line/column and token in the original GUARD source. For DO-178C this is not optional. Every operation emitted must be accounted for, every line of input must be traceable through every compiler pass. You have none of this.
4.  **Undefined behaviour validation**
    Your optimizers and code generators will produce UB. Guaranteed. There are no passes verifying that generated code does not contain unaligned accesses, stack overflow, integer division by zero, floating point denormal divergence between target steppings, or aliasing violations. You assume correct input produces correct output. This is never true for real hardware.
5.  **Stack boundedness proof**
    You have a stack-based VM. Every stack VM ever built for safety critical had this exact hole: there is no proof that no opcode will ever underflow the stack, no proof of maximum stack depth for any program. This is the #1 silent failure mode in embedded VM runtimes.
6.  **Translation validation**
    No compiler is bug free. Not even CompCert. You do not have a post-compilation equivalence checker that verifies *every single compiled output* matches the original constraint semantics. Testing catches 99% of bugs. Translation validation catches 100%.
7.  *Also: You listed strength reduction twice in your optimizer pass list. Nobody noticed. That is the perfect metaphor for the current maturity level.*

---

## 2. REPOSITORY STRUCTURE
Stop copying Javascript CRUD repo layouts. This is safety critical software. 70% of the repo will be code that never runs on target:
```
flux/
├── formal/               # THIS COMES FIRST. NOT AN AFTERTHOUGHT.
│   ├── guard-semantics/  # Machine checked Coq/Isabelle spec, 1:1 with grammar
│   ├── pass-theorems/    # One correctness lemma per compiler pass, no exceptions
│   └── vrs/              # Signed verification review records
├── compiler/
│   ├── parser/           # Generated, not hand written. Grammar committed here.
│   ├── normalizer/
│   ├── optimizer/
│   └── codegen/          # One isolated subdir per target, each with own proof
├── vm/
│   ├── spec/
│   ├── impl/
│   └── wcet/             # Proven WCET bounds for every opcode on every arch
├── qualification/        # 70% OF ALL WORK GOES HERE
│   ├── do178c/
│   ├── iso26262/
│   └── ecss-e-st-40c/
├── tests/
│   ├── conform/          # Standardized test suite
│   ├── miscompile-regressions/
│   ├── fuzz/
│   └── negative/         # 50% of all tests: invalid input that MUST be rejected
├── cli/
├── docs/
│   ├── user-manual/      # For aerospace engineers, not compiler hackers
│   └── safety-case/
└── third-party/          # Hash pinned, no dynamic dependencies. Ever.
```

Rule: Nothing may be merged into `compiler/` until there is a corresponding machine checked proof in `formal/`. No exceptions.

---

## 3. CLI DESIGN FOR AEROSPACE ENGINEERS
These people do not care about SSA, -O2, or compiler flags. They care about not killing people. 95% of users will only ever run one command:
```bash
flux compile \
  --target=arm-r5f \
  --safety-level=DAL-A \
  --wcet-budget=12us \
  brake_constraint.guard
```

That is it. No `-f` flags. No magic optimizations. If you cannot write a 1 page auditable safety justification for a flag, it does not exist.

Output rules:
1.  Always print the human safety report *before* any object code
2.  Never output object code if any check fails
3.  No warnings. Only hard errors. Aerospace engineers ignore warnings. Warnings are bugs in the compiler.
4.  Never print `internal compiler error`. Print:
    ```
    ❌ COMPILER VERIFICATION FAILURE. NO OUTPUT PRODUCED.
    ❌ INCIDENT ID: 742. CONTACT FLUX SAFETY TEAM.
    ❌ DO NOT ATTEMPT TO WORK AROUND THIS ERROR.
    ```

---

## 4. REQUIRED TESTING INFRASTRUCTURE
Your current unit tests are worthless for safety. This is what you need:
1.  **Per-compilation translation validation**: Every single time any user runs the compiler, it runs a formal equivalence check between generated code and the original AST. Not just in CI. For end users.
2.  **Exhaustive fuzzing**: Generate 10 million random valid GUARD constraints, compile for every target, run on VM, native, and formally verified reference interpreter. Fail on any divergence. Run this 24/7 forever.
3.  **Fault injection testing**: Flip every single bit in the compiler binary. Prove that no single bit flip will ever produce silently incorrect output. Compiler must either crash or produce correct output.
4.  **Negative test dominance**: 50% of your test suite must be invalid GUARD input. Prove the compiler rejects every single one correctly.
5.  **WCET validation**: For every test case, measure actual execution time on physical hardware, fail if it ever exceeds the proven bound.

---

## 5. BECOMING THE DEFINITIVE REFERENCE IMPLEMENTATION
1.  **The semantics are the reference, not your code**: Your compiler is just one correct implementation of the formal spec. Anyone should be able to write an independent compiler that passes 100% of conformance tests.
2.  **Full public bug transparency**: Publish every bug ever found. Not just fixed bugs. All of them. With full root cause, safety impact, and audit trail. No CVEs hidden. No security through obscurity.
3.  **Bit perfect backwards compatibility forever**: A constraint written today will produce exactly identical output bit for bit in 30 years. Aircraft fly for 40 years. They do not upgrade compilers mid program.
4.  **Reproducible builds guaranteed**: Every version will produce exactly the same binary hash, on any host OS, for all time. No timestamps, no randomness, no host dependencies.

---

## 6. RESEARCH VS PRODUCTION COMPILER GAP
This is the part no paper will ever tell you:
| Research Compiler | Production Safety Compiler |
|---|---|
| Built to pass 99% of test cases | Built to never fail any possible input |
| Bugs get fixed next release | We prove an entire class of bug cannot exist anywhere |
| Optimizations added for benchmark speed | Optimizations only added if formally proven correct for all inputs |
| Internal compiler error is annoying | Internal compiler error is a catastrophic safety event requiring full audit of all previous releases |
| 7 correctness theorems are impressive | 7 correctness theorems are table stakes before you write the first line of compiler code |
| Abandoned when the PhD graduates | Supported for 40 years |

---

## 7. ERROR REPORTING FOR NON EXPERTS
Never print `syntax error line 12`. Print this:
```
❌ ERROR brake.guard:12:8 SAFETY-CRITICAL
  constraint decel < 10g
                  ^
Units mismatch: left hand side is m/s², right hand side is standard gravity.
This constraint will evaluate incorrectly by a factor of 9.81.

✅ Suggested fix: decel < 10 * g
✅ Permanent error ID: FLUX-E-1072 https://flux.dev/errors/1072
✅ Compilation aborted. No output produced.
```

Rules:
- No compiler jargon ever
- Always explain the actual safety impact
- Always provide an exact fix
- Every error has a permanent public ID with full documentation

---

## 8. CI/CD PIPELINE
This is not normal open source CI. Every commit runs:
1.  All formal proofs are rechecked. Any broken proof = immediate commit rejection
2.  Triplicate bootstrap: Build the compiler 3 times with 3 different previous versions, confirm all produce bit identical binaries
3.  Full test suite run on physical hardware, not emulators, for all targets
4.  1 million random fuzz cases with differential testing
5.  Fault injection validation
6.  Qualification pack consistency check

There is no unstable `main` branch. Every commit that passes CI is a release candidate. No nightly builds. CI runs on fully airgapped hardware with no internet access.

---

## 9. VERSIONING
SemVer is completely useless for safety critical software. Use this scheme:
`FLUX-<YEAR>.<REVISION>.<QUALIFICATION-LEVEL>`
Example: `FLUX-2025.3.DAL-A`

Rules:
1.  All versions in the same calendar year are 100% bit perfect backwards compatible. No behaviour changes. Only bug fixes that do not alter correct output.
2.  Revision increments only for safety bug fixes
3.  Qualification level is audited and certified. You may never use a DAL-B version in a DAL-A system.
4.  Every released version is supported for a minimum of 25 years.
5.  No API breaking changes ever. If you need new behaviour add a new flag, leave old behaviour exactly as it was forever.

---

## 10. WHAT WOULD MAKE ME TRUST THIS COMPILER
Let me be absolutely clear:
1.  First fire everyone who thought a hand written recursive descent parser was acceptable for safety critical. That single decision demonstrates the team does not understand even the most basic principles of safety.
2.  Formal GUARD semantics are completed and machine checked *before* any further compiler work.
3.  Every single compiler pass has an independent machine checked correctness proof. Not 7 high level theorems. Every pass. Every transformation.
4.  Translation validation runs on every end user compilation.
5.  Full independent third party audit of every line of code, every proof, every test case. Not done by your team. Not done by your employer.
6.  Continuous fuzzing for a minimum of 2 calendar years with zero silent miscompilations found.
7.  Legally binding 30 year support commitment.
8.  Every bug ever found is published in full.
9.  And finally: You put your actual name on the safety case. You sign the legal document that says you are personally responsible if this compiler causes an accident.

That is the only thing that ever actually matters.

---

## CLOSING REMARK
You have an excellent start. The unique normal form theorem is genuinely impressive, most research compilers never reach that bar. But you are at mile 1 of a 100 mile marathon. 90% of the work is not the clever compiler code. It is all the boring, unglamorous, un-publishable work around it that separates something that wins a best paper award from something that flies on an aircraft.

And for god's sake fix the duplicate strength reduction pass.