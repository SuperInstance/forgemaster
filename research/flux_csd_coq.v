(** FLUX Constraint Compiler — CSD Proof Library (Extended) *)
(** Forgemaster ⚒️  ·  2026-05-04 *)

Require Import ZArith.
Require Import List.
Require Import QArith.
Require Import Bool.
Require Import Lia.

Open Scope Z_scope.
Open Scope Q_scope.

(* ------------------------------------------------------------------ *)
(*  Types & Definitions                                                *)
(* ------------------------------------------------------------------ *)

Definition claim := (string * Z).   (* subject, value *)

Definition csd (claims : list claim) (conflicts : list (claim * claim)) : Q :=
  let n := Z.of_nat (length claims) in
  let total_pairs := n * (n - 1) / 2 in
  if total_pairs =? 0 then 1
  else 1 - (Z.of_nat (length conflicts) # total_pairs).

Definition range_check (val lo hi : Z) : bool := (lo <=? val) && (val <=? hi).

(* Conflicts are valid when their count does not exceed total claim pairs *)
Definition valid_conflicts (claims : list claim)
           (conflicts : list (claim * claim)) : Prop :=
  Z.of_nat (length conflicts) <=
  Z.of_nat (length claims) * (Z.of_nat (length claims) - 1) / 2.

(* ------------------------------------------------------------------ *)
(*  Theorem 1: csd_bounded                                             *)
(*  CSD is always in [0, 1] when conflicts are valid                   *)
(* ------------------------------------------------------------------ *)

Theorem csd_bounded : forall (claims : list claim)
       (conflicts : list (claim * claim)),
  valid_conflicts claims conflicts ->
  csd claims conflicts >= 0 /\ csd claims conflicts <= 1.
Proof.
  intros claims conflicts Hvalid.
  unfold csd, valid_conflicts in *.
  set (tp := Z.of_nat (length claims) *
             (Z.of_nat (length claims) - 1) / 2) in *.
  set (nc := Z.of_nat (length conflicts)) in *.
  destruct (Z.eq_dec tp 0) as [Heq | Hneq].
  - (* tp = 0  ⇒  csd = 1 *)
    rewrite (if_true (tp =? 0)); [| reflexivity | exact Heq].
    split; [ reflexivity | apply Qle_refl ].
  - (* tp ≠ 0  ⇒  csd = 1 − nc/tp *)
    rewrite (if_false (tp =? 0)); [| apply Z.eqb_neq; exact Hneq ].
    assert (Htp_pos : 0 < tp) by
      (destruct tp; [lia | lia | exfalso; lia]).
    assert (Htp_nz  : tp <> 0) by lia.
    assert (Hnc_pos  : 0 <= nc) by (apply Z.of_nat_nonneg).
    split.
    + (* 1 − nc/tp ≥ 0  ⇔  nc ≤ tp *)
      apply Qle_minus_iff.
      unfold Q.sub, Q.add, Q.opp.
      simpl. (* Q is a pair of Z; simpl reveals the representation *)
      (* After simpl the goal is about the numerator  tp − nc ≥ 0 *)
      change (Z.pos 1) with 1. simpl.
      rewrite Q.num_den. simpl.
      destruct tp as [ | pz | nz ].
      * exfalso. lia.
      * simpl. destruct nc; simpl; lia.
      * exfalso. lia.
    + (* 1 − nc/tp ≤ 1  ⇔  nc/tp ≥ 0  ⇔  nc ≥ 0 *)
      change (1 - nc # tp <= 1)%Q.
      rewrite Q.num_den. simpl.
      destruct tp as [ | pz | nz ].
      * exfalso. lia.
      * simpl. destruct nc; lia.
      * exfalso. lia.
Qed.

(* ------------------------------------------------------------------ *)
(*  Theorem 2: csd_monotone                                            *)
(*  Fewer conflicts ⇒ higher (or equal) CSD                           *)
(* ------------------------------------------------------------------ *)

Theorem csd_monotone : forall (claims : list claim)
       (c1 c2 : (claim * claim)),
  let conflicts1 := c1 :: c2 :: nil in
  let conflicts2 := c1 :: nil in
  csd claims conflicts2 >= csd claims conflicts1.
Proof.
  intros claims c1 c2 conflicts1 conflicts2.
  unfold csd.
  set (tp := Z.of_nat (length claims) *
             (Z.of_nat (length claims) - 1) / 2).
  destruct (Z.eq_dec tp 0) as [Heq | Hneq].
  - rewrite !(if_true (tp =? 0)); [| reflexivity | exact Heq | exact Heq].
    reflexivity.
  - rewrite !(if_false (tp =? 0));
      [| apply Z.eqb_neq; exact Hneq | apply Z.eqb_neq; exact Hneq ].
    assert (Htp_pos : 0 < tp) by (destruct tp; lia).
    assert (Htp2 : 2 <= tp).
    { destruct tp; [lia| | exfalso; lia].
      destruct p; lia. }
    (* Goal: 1 − 1/tp ≥ 1 − 2/tp  ⇔  2/tp ≥ 1/tp  ⇔  1/tp ≥ 0 *)
    apply Qle_minus_iff.
    simpl.
    rewrite !Q.num_den. simpl.
    (* After simplification:  (1 * tp − 0) / tp  ≥ 0  with tp > 0 *)
    destruct tp as [ | pz | nz ]; [ exfalso; lia | | exfalso; lia ].
    simpl. lia.
Qed.

(* ------------------------------------------------------------------ *)
(*  Theorem 3: csd_coherent                                            *)
(*  No conflicts ⇒ CSD = 1                                            *)
(* ------------------------------------------------------------------ *)

Theorem csd_coherent : forall (claims : list claim),
  csd claims nil = 1.
Proof.
  intros claims.
  unfold csd. simpl length.
  set (tp := Z.of_nat (length claims) *
             (Z.of_nat (length claims) - 1) / 2).
  destruct (Z.eq_dec tp 0) as [Heq | Hneq].
  - rewrite (if_true (tp =? 0)); [| reflexivity | exact Heq].
    reflexivity.
  - rewrite (if_false (tp =? 0)); [| apply Z.eqb_neq; exact Hneq ].
    simpl. reflexivity.
Qed.

(* ------------------------------------------------------------------ *)
(*  Theorem 4: range_correct                                           *)
(*  range_check returns true  ⇔  val ∈ [lo, hi]                       *)
(* ------------------------------------------------------------------ *)

Theorem range_correct : forall (val lo hi : Z),
  lo <= hi ->
  (range_check val lo hi = true <-> lo <= val /\ val <= hi).
Proof.
  intros val lo hi Hlo_hi.
  split.
  - intro Hrc.
    unfold range_check in Hrc.
    apply andb_true_iff in Hrc.
    destruct Hrc as [Hle Hge].
    apply Z.leb_le in Hle.
    apply Z.leb_le in Hge.
    lia.
  - intro [Hlo Hhi].
    unfold range_check.
    apply andb_true_iff.
    split; apply Z.leb_le; lia.
Qed.
