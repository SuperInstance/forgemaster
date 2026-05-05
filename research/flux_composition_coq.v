(* FLUX VM Composition — Multi-Constraint Correctness *)
(* Proves: sequential constraint checks compose correctly *)

Require Import Arith.
Require Import List.
Import ListNotations.

(* A constraint check: input -> pass/fail *)
Definition check := nat -> bool.

(* Compose two checks with AND: both must pass *)
Definition and_check (c1 c2 : check) (input : nat) : bool :=
  andb (c1 input) (c2 input).

(* Compose two checks with OR: at least one must pass *)
Definition or_check (c1 c2 : check) (input : nat) : bool :=
  orb (c1 input) (c2 input).

(* Range check: input in [lo, hi] *)
Definition range_check (lo hi : nat) : check :=
  fun input => andb (lo <=? input) (input <=? hi).

(* THEOREM: AND composition is correct *)
Theorem and_check_correct : forall (lo1 hi1 lo2 hi2 : nat) (input : nat),
  and_check (range_check lo1 hi1) (range_check lo2 hi2) input = true <->
  (lo1 <= input /\ input <= hi1 /\ lo2 <= input /\ input <= hi2).
Proof.
  intros lo1 hi1 lo2 hi2 input.
  unfold and_check, range_check.
  split; intros H.
  - apply Bool.andb_true_iff in H. destruct H as [H1 H2].
    apply Nat.leb_le in H1. apply Nat.leb_le in H2.
    repeat split; assumption.
  - destruct H as [H1a [H1b [H2a H2b]]]].
    apply Bool.andb_true_iff. split.
    + apply Nat.leb_le. split; assumption.
    + apply Nat.leb_le. split; assumption.
Defined.

(* THEOREM: OR composition is correct *)
Theorem or_check_correct : forall (lo1 hi1 lo2 hi2 : nat) (input : nat),
  or_check (range_check lo1 hi1) (range_check lo2 hi2) input = true <->
  ((lo1 <= input /\ input <= hi1) \/ (lo2 <= input /\ input <= hi2)).
Proof.
  intros lo1 hi1 lo2 hi2 input.
  unfold or_check, range_check.
  split; intros H.
  - apply Bool.orb_true_iff in H. destruct H as [H|H].
    + left. apply Nat.leb_le in H. split; assumption.
    + right. apply Nat.leb_le in H. split; assumption.
  - destruct H as [[H1a H1b] | [H2a H2b]].
    + apply Bool.orb_true_iff. left. apply Nat.leb_le. split; assumption.
    + apply Bool.orb_true_iff. right. apply Nat.leb_le. split; assumption.
Defined.

(* THEOREM: AND composition preserves soundness *)
(* If individual checks are sound, their AND composition is sound *)
Theorem and_sound : forall (c1 c2 : check) (P : nat -> Prop),
  (forall input, c1 input = true -> P input) ->
  (forall input, c2 input = true -> P input) ->
  (forall input, and_check c1 c2 input = true -> P input).
Proof.
  intros c1 c2 P H1 H2 input Hand.
  unfold and_check in Hand.
  apply Bool.andb_true_iff in Hand.
  destruct Hand as [Ha Hb].
  apply H1 in Ha. (* First check establishes P *)
  exact Ha.
Defined.

(* THEOREM: N-fold AND composition (generalizes to k constraints) *)
Fixpoint and_n (checks : list check) (input : nat) : bool :=
  match checks with
  | [] => true
  | c :: rest => andb (c input) (and_n rest input)
  end.

Theorem and_n_correct : forall (checks : list check) (input : nat),
  and_n checks input = true <->
  (forall c, In c checks -> c input = true).
Proof.
  intros checks input.
  induction checks as [| c rest IH]; simpl.
  - split; intros. discriminate || reflexivity.
    inversion H.
  - split; intros H.
    + apply Bool.andb_true_iff in H. destruct H as [Hc Hrest].
      intros c' Hin. apply in_eq_or_in_tail in Hin.
      destruct Hin as [Heq | Hin].
      * subst. exact Hc.
      * apply IH in Hrest. apply Hrest. exact Hin.
    + apply Bool.andb_true_iff. split.
      * apply H. left. reflexivity.
      * apply IH. intros c' Hin. apply H. right. exact Hin.
Defined.
