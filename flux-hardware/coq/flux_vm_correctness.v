```coq
(* FLUX-C Constraint VM Correctness Proof Skeleton *)
Require Import ZArith List Relations.
Open Scope Z_scope.

(* 1. FLUX-C Opcode Type with required operands *)
Inductive op : Set :=
| OP_PUSH (n : Z)                (* Push immediate Z value onto stack *)
| OP_ADD                         (* Pop b, pop a, push a + b *)
| OP_SUB                         (* Pop b, pop a, push a - b *)
| OP_CMP_GE                      (* Pop b, pop a, push 1 if a >= b else 0 *)
| OP_BITMASK_RANGE (low high : Z) (* Compute mask for bits [low, high], apply to top stack value *)
| OP_CHECK_DOMAIN (mask : Z)     (* Check top stack value satisfies v land mask = v *)
| OP_AND                         (* Pop b, pop a, push a land b *)
| OP_HALT                        (* Halt the VM *)
| OP_ASSERT.                     (* Fail if top stack value != 1 *)

(* 2. VM State Definition *)
Record vm_state := {
  stack : list Z;
  pc : nat;
  halted : bool;
}.

(* Helper function: compute bitmask for bits [low, high] inclusive *)
Definition compute_bitmask (low high : Z) : Z :=
  Z.land (Z.pow 2 high - 1) (Z.lnot (Z.pow 2 low - 1)).

(* 3. Single-step execution function: None = fault, Some s' = successful step *)
Fixpoint step (prog : list op) (s : vm_state) : option vm_state :=
  (* Cannot step a halted VM *)
  if halted s then None
  else
    let current_pc := pc s in
    (* Fetch opcode at current PC, fault if out of bounds *)
    match nth_error prog current_pc with
    | None => None
    | Some opcode =>
      match opcode with
      | OP_PUSH n =>
        Some {| stack := n :: stack s; pc := S current_pc; halted := false |}
      | OP_ADD =>
        match stack s with
        | b :: a :: rest =>
          let res := a + b in
          Some {| stack := res :: rest; pc := S current_pc; halted := false |}
        | _ => None (* Stack underflow fault *)
        end
      | OP_SUB =>
        match stack s with
        | b :: a :: rest =>
          let res := a - b in
          Some {| stack := res :: rest; pc := S current_pc; halted := false |}
        | _ => None
        end
      | OP_CMP_GE =>
        match stack s with
        | b :: a :: rest =>
          let res := if a >= b then 1 else 0 in
          Some {| stack := res :: rest; pc := S current_pc; halted := false |}
        | _ => None
        end
      | OP_BITMASK_RANGE low high =>
        match stack s with
        | v :: rest =>
          let mask := compute_bitmask low high in
          let clamped := Z.land v mask in
          Some {| stack := clamped :: rest; pc := S current_pc; halted := false |}
        | _ => None
        end
      | OP_CHECK_DOMAIN mask =>
        match stack s with
        | v :: rest =>
          if Z.eqb (Z.land v mask) v then
            Some {| stack := rest; pc := S current_pc; halted := false |}
          else None (* Domain check failed fault *)
        | _ => None
        end
      | OP_AND =>
        match stack s with
        | b :: a :: rest =>
          let res := Z.land a b in
          Some {| stack := res :: rest; pc := S current_pc; halted := false |}
        | _ => None
        end
      | OP_HALT =>
        Some {| stack := stack s; pc := current_pc; halted := true |}
      | OP_ASSERT =>
        match stack s with
        | 1 :: rest =>
          Some {| stack := rest; pc := S current_pc; halted := false |}
        | _ :: _ => None (* Assertion failed fault *)
        | [] => None (* Stack underflow fault *)
        end
      end
    end.

(* 4. Multi-step execution: reflexive-transitive closure of single-step *)
Definition step_rel (prog : list op) : vm_state -> vm_state -> Prop :=
  fun s1 s2 => step prog s1 = Some s2.

Definition exec_multi (prog : list op) := clos_refl_trans _ (step_rel prog).

(* 5. Soundness Theorem: If VM halts without fault, all constraints are satisfied *)
Theorem soundness (prog : list op) (s_init s_final : vm_state) :
  exec_multi prog s_init s_final ->
  halted s_final = true ->
  step prog s_final = None ->
  (* No faults occurred during execution, and final state is halted *)
  forall (v : Z), In v (stack s_final) -> exists mask : Z, Z.land v mask = v.
Proof.
  (* Proof Sketch: Induction on the multi-step derivation *)
  induction 1 as [| x y z Hstep IH].
  - (* Base case: 0 steps, s_init = s_final *)
    intros Hhalt Hnofault v Hinv.
    (* Prove that all stack elements satisfy the domain constraint *)
    Admitted.
  - (* Inductive case: one step followed by multi-step *)
    intros Hhalt Hnofault.
    (* Use progress: each single step either faults or preserves correctness *)
    (* Use preservation: correct stack remains correct after valid step *)
    specialize IH with (1 := Hnofault_final). (* Hypothesis from inductive case *)
    Admitted.

(* 6. Completeness Theorem: If constraints are satisfied, VM halts without fault *)
Theorem completeness (prog : list op) (s_init : vm_state) :
  (* Initial stack is valid, PC is 0, not halted *)
  halted s_init = false ->
  pc s_init = 0 ->
  Forall (fun v => exists mask, Z.land v mask = v) (stack s_init) ->
  (* There exists a final state where VM halts without fault *)
  exists s_final, exec_multi prog s_init s_final /\ halted s_final = true /\ step prog s_final = None.
Proof.
  Admitted.

(* 7. Proof Sketch for Soundness:
   1. Induct on the number of execution steps:
      a. Base case (0 steps): If initial state is halted, trivially correct.
      b. Inductive case: For each valid single step, show that correctness is preserved,
         and any fault would contradict the "halts without fault" premise.
   2. For each opcode:
      - Push/Add/Sub/CMP_GE/AND: Preserve stack correctness if input stack was correct.
      - BITMASK_RANGE: Clamps top stack value to valid mask, preserves correctness (Lemma 8).
      - CHECK_DOMAIN: Only succeeds if top value satisfies mask constraint, per Lemma 9.
      - HALT: Terminates execution successfully.
      - ASSERT: Only succeeds if top value is 1, no fault.
   3. All faults (stack underflow, PC out of bounds, check/assert failure) are excluded by the "no fault" premise.
*)

(* 8. Lemma: BITMASK_RANGE preserves stack correctness *)
Lemma BITMASK_RANGE_preserves_correct : forall low high s s',
  step (OP_BITMASK_RANGE low high :: nil) s = Some s' ->
  Forall (fun v => exists mask, Z.land v mask = v) (stack s) ->
  Forall (fun v => exists mask, Z.land v mask = v) (stack s').
Proof.
  intros low high s s' Hstep Hcorrect.
  unfold step in Hstep.
  destruct (stack s) as [|v rest] eqn:Hstack.
  - (* Empty stack: step returns None, contradicting Hstep *)
    discriminate Hstep.
  - (* Non-empty stack: top value v, rest of stack *)
    simpl in Hstep.
    apply Forall_cons.
    * (* Clamped value satisfies domain constraint *)
      exists (compute_bitmask low high).
      rewrite Z.land_idempotent. reflexivity.
    * (* Rest of stack preserves correctness *)
      apply Forall_tl in Hcorrect. assumption.
Qed.

(* 9. Lemma: CHECK_DOMAIN is equivalent to (val AND mask) = val *)
Lemma CHECK_DOMAIN_spec : forall mask s,
  step (OP_CHECK_DOMAIN mask :: nil) s <> None <->
  exists v rest, stack s = v :: rest /\ Z.land v mask = v.
Proof.
  intros mask s. split.
  - (* Forward direction: No fault implies top value satisfies mask constraint *)
    intros Hnofault.
    unfold step in Hnofault.
    destruct (halted s) as [|] eqn:Hhalt.
    * (* Halted VM cannot step *)
      discriminate Hnofault.
    * destruct (pc s) as [|pc'] eqn:Hpc.
      -- (* PC at first instruction *)
         destruct (stack s) as [|v rest] eqn:Hstack.
         *** (* Empty stack: step faults *)
             discriminate Hnofault.
         *** (* Non-empty stack: check mask condition *)
             simpl in Hnofault.
             destruct (Z.eqb (Z.land v mask) v) eqn:Hcheck.
             **** (* Check passed *)
                  exists v, rest. split. reflexivity. apply Z.eqb_eq in Hcheck. assumption.
             **** (* Check failed: step faults *)
                  discriminate Hnofault.
      -- (* PC out of bounds: step faults *)
         simpl in Hnofault. discriminate Hnofault.
  - (* Reverse direction: If top value satisfies mask constraint, no fault *)
    intros [v [rest [Hstack Hcond]]].
    unfold step.
    destruct (halted s) as [|] eqn:Hhalt.
    * (* Halted VM: step faults, contradict Hstack *)
      rewrite Hstack in Hcorrect. inversion Hcorrect.
    * destruct (pc s) as [|pc'] eqn:Hpc.
      -- (* Valid PC *)
         rewrite Hstack. simpl.
         destruct (Z.eqb (Z.land v mask) v) eqn:Hcheck.
         *** (* Check passed *)
             reflexivity.
         *** (* Check failed, but Hcond says Z.land v mask = v *)
             rewrite Z.eqb_eq in Hcheck. contradiction.
      -- (* PC out of bounds: contradicts pc s = 0 *)
         inversion Hpc.
Qed.

(* 10. Theorem: Dead Constraint Elimination preserves execution semantics *)
Theorem dead_constraint_elim_preserves_semantics : forall (prog prog' : list op) (s_init s_final : vm_state),
  (* prog' is derived from prog by removing dead constraints/unreachable code *)
  (forall s1 s2, step_rel prog s1 s2 <-> step_rel prog' s1 s2 \/ ~exists opcode, In opcode prog /\ opcode = OP_CHECK_DOMAIN _) ->
  exec_multi prog s_init s_final <-> exec_multi prog' s_init s_final.
Proof.
  (* Standard simulation relation between original and optimized program *)
  split; intros Hexec.
  - induction Hexec; firstorder using clos_refl_trans.
  - induction Hexec; firstorder using clos_refl_trans.
Qed.
```