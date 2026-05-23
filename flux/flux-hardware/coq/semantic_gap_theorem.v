From mathcomp Require Import all_ssreflect.

(* 1. Inductive flight_command with 7 constructors *)
Inductive flight_command : Set :=
  | Takeoff
  | Land
  | Hover
  | Forward
  | Backward
  | TurnLeft
  | TurnRight.

(* 2. Definition of safe set *)
Definition safe_set : seq flight_command :=
  [:: Takeoff; Land; Hover; Forward].

Definition is_safe (cmd : flight_command) : bool :=
  cmd \in safe_set.

(* 3. Whitelist constraint as membership test *)
Definition whitelist_constraint (cmd : flight_command) : bool :=
  is_safe cmd.

(* 4. Theorem: whitelist_safe *)
Theorem whitelist_safe (cmd : flight_command) :
  whitelist_constraint cmd -> is_safe cmd.
Proof.
  by [].
Qed.

(* 5. Instantiation and proof for eVTOL *)
Definition eVTOL_safe_set : seq flight_command :=
  [:: Takeoff; Land; Hover].

Definition eVTOL_is_safe (cmd : flight_command) : bool :=
  cmd \in eVTOL_safe_set.

Theorem eVTOL_whitelist_safe (cmd : flight_command) :
  eVTOL_is_safe cmd -> is_safe cmd.
Proof.
  rewrite /eVTOL_is_safe /is_safe /safe_set => H.
  apply: mem_subseq H.
  by apply: take_subseq; constructor.
Qed.

(* 6. BitmaskDomain representation (each activation checked against u64 mask) *)
Definition u64 := nat. (* Simplified representation for Coq *)
Definition bitmask : u64 := 15. (* 0b1111 for first 4 commands *)

Definition bitmask_check (cmd : flight_command) : bool :=
  match cmd with
  | Takeoff  => (bitmask / 1) %% 2 == 1
  | Land     => (bitmask / 2) %% 2 == 1
  | Hover    => (bitmask / 4) %% 2 == 1
  | Forward  => (bitmask / 8) %% 2 == 1
  | Backward => false
  | TurnLeft => false
  | TurnRight => false
  end.

(* 7. Theorem: bitmask_whitelist_equivalence for finite domains *)
Theorem bitmask_whitelist_equivalence (cmd : flight_command) :
  whitelist_constraint cmd = bitmask_check cmd.
Proof.
  case: cmd; rewrite /whitelist_constraint /is_safe /safe_set /bitmask_check //=.
  - by rewrite in_cons in_nil.
  - by rewrite in_cons in_cons in_nil.
  - by rewrite in_cons in_cons in_cons in_nil.
  - by rewrite in_cons in_cons in_cons in_cons in_nil.
Qed.

(* Additional lemma: all safe commands pass bitmask check *)
Lemma safe_commands_pass_bitmask (cmd : flight_command) :
  is_safe cmd -> bitmask_check cmd.
Proof.
  move=> H; move: (bitmask_whitelist_equivalence cmd).
  by rewrite H => ->.
Qed.

(* Example usage *)
Example takeoff_is_safe : is_safe Takeoff := by
  rewrite /is_safe /safe_set; apply: mem_head.

Example takeoff_passes_bitmask : bitmask_check Takeoff :=
  safe_commands_pass_bitmask Takeoff takeoff_is_safe.
