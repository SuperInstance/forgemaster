;===- test/xconstr-guard.ll - Xconstr GUARD constraint codegen test --------===
;
; RISC-V Xconstr Extension — Test: GUARD constraint → Xconstr assembly
;
; Scenario: 8-queens CSP, from flux-isa-architecture.md §4.2
;   Two queens on rows i and j must not share a column.
;   Domains are 64-bit bitmasks: bit k = 1 ⟹ column k is still valid.
;
; The GUARD constraint:
;   GUARD no_queen_conflict(domain_i: u64, domain_j: u64) -> u64
;     -- Remove from domain_i any column that domain_j forces
;     -- Fault architecturally if domain_i is wiped out (no valid column)
;     -- Return the revised domain_i
;
; Compile + run:
;   llc -march=riscv64 -mattr=+xconstr \
;       -verify-machineinstrs xconstr-guard.ll -o xconstr-guard.s
;
; Expected assembly output (register allocation may vary):
;   guard_no_queen_conflict:
;       cld     cr0, a0          # load domain_i into CR0
;       cld     cr1, a1          # load domain_j into CR1
;       crevise cr2, cr0, cr1    # cr2 = cr0 & ~cr1 (remove conflicting cols)
;       cempty  a2,  cr2         # a2 = (cr2 == 0) ? 1 : 0
;       cfault  cr2              # architectural fault if domain empty
;       cst     a0,  cr2         # store revised domain back to a0
;       ret
;
; Run FileCheck:
;   llc ... | FileCheck xconstr-guard.ll
;
; RUN: llc -march=riscv64 -mattr=+xconstr -verify-machineinstrs %s \
; RUN:   | FileCheck %s
;
; RUN: llc -march=riscv64 -mattr=+xconstr -verify-machineinstrs %s \
; RUN:   -filetype=obj -o %t.o
; RUN: llvm-objdump -d --mattr=+xconstr %t.o | FileCheck %s --check-prefix=ENC
;===------------------------------------------------------------------------===

target triple = "riscv64-unknown-elf"

declare i64 @llvm.riscv.xconstr.cld(i64)
declare i64 @llvm.riscv.xconstr.cst(i64)
declare i64 @llvm.riscv.xconstr.cand(i64, i64)
declare i64 @llvm.riscv.xconstr.cor(i64, i64)
declare i64 @llvm.riscv.xconstr.cnot(i64)
declare i64 @llvm.riscv.xconstr.cpop(i64)
declare i64 @llvm.riscv.xconstr.crevise(i64, i64)
declare i64 @llvm.riscv.xconstr.cempty(i64)
declare void @llvm.riscv.xconstr.cfault(i64)

;===------------------------------------------------------------------------===
; Test 1: guard_no_queen_conflict
;
; GUARD: queens[i] ≠ queens[j]  (column-uniqueness constraint, 8-queens CSP)
;
; domain_i and domain_j are bitmasks of valid columns {0..7}.
; After revision, domain_i has column c removed iff domain_j is singleton {c}.
; The hardware CREVISE opcode handles the revision policy; the compiler emits
; the instruction and the constraint checker unit applies the correct rule.
;===------------------------------------------------------------------------===
; CHECK-LABEL: guard_no_queen_conflict:
define i64 @guard_no_queen_conflict(i64 %domain_i, i64 %domain_j) {
entry:
  ; Load both domains into constraint registers.
  ; CHECK: cld cr{{[0-7]}}, a0
  %cr_i = call i64 @llvm.riscv.xconstr.cld(i64 %domain_i)

  ; CHECK: cld cr{{[0-7]}}, a1
  %cr_j = call i64 @llvm.riscv.xconstr.cld(i64 %domain_j)

  ; Arc-consistency revision: remove from domain_i any value that conflicts
  ; with domain_j under the inequality constraint.
  ; Hardware semantic: revised = domain_i & ~domain_j
  ; CHECK: crevise cr{{[0-7]}}, cr{{[0-7]}}, cr{{[0-7]}}
  %cr_revised = call i64 @llvm.riscv.xconstr.crevise(i64 %cr_i, i64 %cr_j)

  ; Check if revision wiped out domain_i.
  ; CHECK: cempty {{a[0-7]}}, cr{{[0-7]}}
  %is_empty = call i64 @llvm.riscv.xconstr.cempty(i64 %cr_revised)

  ; Architectural fault if domain is empty — maps to ASSERT opcode in FLUX ISA,
  ; FAULT_ILLEGAL_OP in flux_checker_top.sv, irreversible safe-state transition.
  ; CHECK: cfault cr{{[0-7]}}
  call void @llvm.riscv.xconstr.cfault(i64 %cr_revised)

  ; Store revised domain back into a GPR to return it.
  ; CHECK: cst a0, cr{{[0-7]}}
  %result = call i64 @llvm.riscv.xconstr.cst(i64 %cr_revised)

  ; CHECK: ret
  ret i64 %result
}

;===------------------------------------------------------------------------===
; Test 2: guard_domain_intersection
;
; GUARD: queen i's valid columns ∩ queen j's valid columns must be non-empty.
; Used when checking whether two queens' domains are still jointly satisfiable
; before committing to an assignment (lookahead in backtracking search).
;===------------------------------------------------------------------------===
; CHECK-LABEL: guard_domain_intersection:
define i64 @guard_domain_intersection(i64 %domain_i, i64 %domain_j) {
entry:
  ; CHECK: cld cr{{[0-7]}}, a0
  %cr_i = call i64 @llvm.riscv.xconstr.cld(i64 %domain_i)
  ; CHECK: cld cr{{[0-7]}}, a1
  %cr_j = call i64 @llvm.riscv.xconstr.cld(i64 %domain_j)

  ; Intersection: bits set in both domains (columns valid for both queens).
  ; CHECK: cand cr{{[0-7]}}, cr{{[0-7]}}, cr{{[0-7]}}
  %cr_inter = call i64 @llvm.riscv.xconstr.cand(i64 %cr_i, i64 %cr_j)

  ; Fault if intersection is empty — the two queens have no compatible columns.
  ; CHECK: cfault cr{{[0-7]}}
  call void @llvm.riscv.xconstr.cfault(i64 %cr_inter)

  ; Return cardinality of the intersection (how many shared columns remain).
  ; CHECK: cpop {{a[0-7]}}, cr{{[0-7]}}
  %card = call i64 @llvm.riscv.xconstr.cpop(i64 %cr_inter)

  ; CHECK: ret
  ret i64 %card
}

;===------------------------------------------------------------------------===
; Test 3: guard_sonar_bounds
;
; GUARD: sound speed in [1430, 1560] m/s (Mackenzie 1981 bounds, §4.4)
; Demonstrates the sonar physics constraint from the paper compiled to Xconstr.
;
; Domain encoding: for integer-valued domains, bit k = 1 means value (k+BASE)
; is valid.  Here we use a 128-unit quantisation: bit k = (speed - 1430) / 1.
; Full 64-bit coverage spans 1430..1493 m/s in this quantisation.  A wider
; encoding (e.g. 2 m/s per bit) would cover 1430..1557 (rounds to 1556).
;
; In practice the FLUX mini-tier uses pre-computed bitmask constants; this
; test shows the compilation pattern for a 64-value discrete domain.
;===------------------------------------------------------------------------===
; CHECK-LABEL: guard_sonar_bounds:
define i64 @guard_sonar_bounds(i64 %measured_domain, i64 %valid_range_mask) {
entry:
  ; %measured_domain:  bitmask of quantised sound-speed values from sensor.
  ; %valid_range_mask: compile-time constant 0x3FFFFFFFFFFFFFFF (bits 0..61,
  ;                    representing 1430..1491 m/s at 1 m/s resolution).

  ; CHECK: cld cr{{[0-7]}}, a0
  %cr_meas = call i64 @llvm.riscv.xconstr.cld(i64 %measured_domain)
  ; CHECK: cld cr{{[0-7]}}, a1
  %cr_valid = call i64 @llvm.riscv.xconstr.cld(i64 %valid_range_mask)

  ; Intersect measured domain with valid physics range.
  ; After CAND, only values within Mackenzie bounds remain.
  ; CHECK: cand cr{{[0-7]}}, cr{{[0-7]}}, cr{{[0-7]}}
  %cr_checked = call i64 @llvm.riscv.xconstr.cand(i64 %cr_meas, i64 %cr_valid)

  ; If the intersection is empty, the sensor reading is physically impossible —
  ; architecturally fault.  This matches the sonar assertion in §4.4:
  ;   PUSH 1500.0 / PUSH 1430.0 / PUSH 1560.0 / Constrain / Verify / Assert
  ; CHECK: cfault cr{{[0-7]}}
  call void @llvm.riscv.xconstr.cfault(i64 %cr_checked)

  ; Return the constrained domain for downstream propagation.
  ; CHECK: cst a0, cr{{[0-7]}}
  %result = call i64 @llvm.riscv.xconstr.cst(i64 %cr_checked)

  ; CHECK: ret
  ret i64 %result
}

;===------------------------------------------------------------------------===
; Test 4: guard_full_propagation
;
; GUARD: demonstrate a full AC-3 propagation step for 3 queens.
;   Domain revision: queen 0 vs queen 1, then queen 0 vs queen 2.
;   Union the two revised domains to see remaining options for queen 0.
;===------------------------------------------------------------------------===
; CHECK-LABEL: guard_full_propagation:
define i64 @guard_full_propagation(i64 %d0, i64 %d1, i64 %d2) {
entry:
  ; CHECK: cld
  %cr0 = call i64 @llvm.riscv.xconstr.cld(i64 %d0)
  ; CHECK: cld
  %cr1 = call i64 @llvm.riscv.xconstr.cld(i64 %d1)
  ; CHECK: cld
  %cr2 = call i64 @llvm.riscv.xconstr.cld(i64 %d2)

  ; Revise cr0 with respect to cr1 (queen 0 vs queen 1).
  ; CHECK: crevise
  %rev01 = call i64 @llvm.riscv.xconstr.crevise(i64 %cr0, i64 %cr1)

  ; Revise cr0 with respect to cr2 (queen 0 vs queen 2).
  ; CHECK: crevise
  %rev02 = call i64 @llvm.riscv.xconstr.crevise(i64 %cr0, i64 %cr2)

  ; Intersect both revisions: only columns consistent with BOTH constraints.
  ; CHECK: cand
  %cr_final = call i64 @llvm.riscv.xconstr.cand(i64 %rev01, i64 %rev02)

  ; Fault if queen 0 has no valid column left.
  ; CHECK: cfault
  call void @llvm.riscv.xconstr.cfault(i64 %cr_final)

  ; Return cardinality — number of still-valid columns for queen 0.
  ; CHECK: cpop
  %card = call i64 @llvm.riscv.xconstr.cpop(i64 %cr_final)

  ; CHECK: ret
  ret i64 %card
}

; ENC:      1011011   {{.*}}CAND
; ENC:      1011011   {{.*}}CREVISE
; ENC:      1011011   {{.*}}CFAULT
; (All Xconstr instructions share the custom-2 opcode field 0x5B = 0b1011011)
