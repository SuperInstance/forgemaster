;; constraint.wat - Constraint checking system for Penrose Memory Palace
;; Eisenstein snap, Dodecet encode, 3-tier constraint check
;; WebAssembly Text format - hand written for browser deployment
;;
;; Memory layout:
;;   Tile data at offset 0: array of {x:i32, y:i32, state:i32, color:i32}
;;   Each tile is 16 bytes (4 x i32)
;;   Output buffer at offset 65504 (last 32 bytes of 64KB page)
;;
;; Exports:
;;   snap(idx) - snap tile at index to Eisenstein lattice, returns 1 if changed
;;   dodecet_encode(s0..s11) - pack 12 states into 24-bit value
;;   dodecet_decode(offset) - unpack from offset, write decoded to offset+4
;;   constraint_check(data_off, count, out_off, lut_off) - run 3-tier check
;;   batch_snap(data_off, count) - snap all tiles, returns count snapped
;;   eisenstein_norm_sq(a, b) - compute N(a + bω) = a² - ab + b²
;;
;; Constants for Eisenstein transformation
;;   ω = e^(2πi/3) = (-1 + i√3)/2
;;   Eisenstein basis: e1=(1,0), e2=(-1/2, √3/2)
;;   Approximations: √3/2 ≈ 866/1000, 1/√3 ≈ 577/1000, 2/√3 ≈ 1155/1000

(module
  ;; Import shared memory (single 64KB page)
  (import "env" "memory" (memory 1))

  ;; Export memory for JS access
  (export "memory" (memory 0))

  ;; Tile structure: 16 bytes each
  ;;   +0: x (i32) - Cartesian x or Eisenstein a
  ;;   +4: y (i32) - Cartesian y or Eisenstein b
  ;;   +8: state (i32)
  ;;  +12: color (i32) - tile color for Admit 432

  ;; ============ Helper: absolute value ============
  (func $abs (param $v i32) (result i32)
    (if (result i32) (i32.lt_s (local.get $v) (i32.const 0))
      (then (i32.sub (i32.const 0) (local.get $v)))
      (else (local.get $v))
    )
  )

  ;; ============ Eisenstein Norm Squared ============
  ;; N(a + bω) = a² - ab + b²
  (func $eisenstein_norm_sq_func (export "eisenstein_norm_sq") (param $a i32) (param $b i32) (result i32)
    (i32.sub
      (i32.add
        (i32.mul (local.get $a) (local.get $a))
        (i32.mul (local.get $b) (local.get $b))
      )
      (i32.mul (local.get $a) (local.get $b))
    )
  )

  ;; ============ Eisenstein to Cartesian ============
  ;; Compute x = (2a - b) / 2, y = b * 866 / 1000
  ;; Returns x, y stored into linear memory at given offset
  (func $store_cartesian (param $a i32) (param $b i32) (param $out_offset i32)
    (local $x i32)
    (local $y i32)

    ;; x = floor((2*a - b + sign(2*a-b)) / 2)  -- round toward zero
    ;; Simple: x = (2*a - b) / 2 using signed division
    (local.set $x
      (i32.div_s
        (i32.sub (i32.shl (local.get $a) (i32.const 1)) (local.get $b))
        (i32.const 2)
      )
    )

    ;; y = b * 866 / 1000
    (local.set $y
      (i32.div_s
        (i32.mul (local.get $b) (i32.const 866))
        (i32.const 1000)
      )
    )

    ;; Store x, y at output offset
    (i32.store (local.get $out_offset) (local.get $x))
    (i32.store (i32.add (local.get $out_offset) (i32.const 4)) (local.get $y))
  )

  ;; ============ Eisenstein Snap ============
  ;; Snap tile at index to nearest Eisenstein integer lattice point.
  ;; Tile struct: {x:i32, y:i32, state:i32, color:i32} (16 bytes)
  ;; Input: tile x, y are Cartesian coordinates
  ;; Output: snapped Eisenstein (a, b) stored in state, color fields
  ;; Returns 1 if tile was snapped, 0 if already Eisenstein-encoded
  ;;
  ;; Algorithm:
  ;;   1. Approximate Eisenstein coordinates from Cartesian
  ;;   2. Search 3x3 neighborhood for closest lattice point
  ;;   3. Return closest by Euclidean distance

  (func $snap_func (export "snap") (param $idx i32) (result i32)
    (local $offset i32)
    (local $cx i32)
    (local $cy i32)
    (local $old_state i32)
    (local $old_color i32)
    (local $a_approx i32)
    (local $b_approx i32)
    (local $da i32)
    (local $db i32)
    (local $test_a i32)
    (local $test_b i32)
    (local $tx i32)
    (local $ty i32)
    (local $dx i32)
    (local $dy i32)
    (local $dist_sq i32)
    (local $best_dist_sq i32)
    (local $best_a i32)
    (local $best_b i32)
    (local $cart_tmp i32)
    (local $dx1000 i32)
    (local $dy1000 i32)
    (local $tmp i32)
    (local $tmp2 i32)

    ;; Setup: scratch space at memory offset 65520
    (local.set $cart_tmp (i32.const 65520))

    (local.set $offset (i32.mul (local.get $idx) (i32.const 16)))

    ;; Load Cartesian coordinates from tile
    (local.set $cx (i32.load (local.get $offset)))
    (local.set $cy (i32.load (i32.add (local.get $offset) (i32.const 4))))
    (local.set $old_state (i32.load (i32.add (local.get $offset) (i32.const 8))))
    (local.set $old_color (i32.load (i32.add (local.get $offset) (i32.const 12))))

    ;; Skip if already snapped (state or color non-zero)
    (if (i32.ne (local.get $old_state) (i32.const 0))
      (then (return (i32.const 0)))
    )
    (if (i32.ne (local.get $old_color) (i32.const 0))
      (then (return (i32.const 0)))
    )

    ;; Approximate Eisenstein coordinates from Cartesian
    ;; b_approx = cy * 1155 / 1000  (2/√3 ≈ 1.1547)
    (local.set $b_approx
      (i32.div_s
        (i32.mul (local.get $cy) (i32.const 1155))
        (i32.const 1000)
      )
    )

    ;; a_approx = cx + cy * 577 / 1000  (1/√3 ≈ 0.57735)
    (local.set $a_approx
      (i32.add
        (local.get $cx)
        (i32.div_s
          (i32.mul (local.get $cy) (i32.const 577))
          (i32.const 1000)
        )
      )
    )

    ;; Initialize best to our initial approximation
    (local.set $best_a (local.get $a_approx))
    (local.set $best_b (local.get $b_approx))
    ;; Compute distance for approximation using Eisenstein norm
    ;; Distance squared (continuous) from input point to approx lattice point
    ;; Use formula: dx² + dy² where
    ;;   dx = x - (a - b/2)
    ;;   dy = y - (b * sqrt(3)/2)
    ;; Scale everything by 1000 for integer arithmetic
    ;; dx1000 = 1000*cx - (1000*a - 500*b)
    ;;        = 1000*cx - 1000*a + 500*b
    (local.set $dx1000
      (i32.sub
        (i32.sub
          (i32.mul (local.get $cx) (i32.const 1000))
          (i32.mul (local.get $a_approx) (i32.const 1000))
        )
        (i32.mul (local.get $b_approx) (i32.const -500))  ;; +500*b
      )
    )
    ;; dy1000 = 1000*cy - b*866
    (local.set $dy1000
      (i32.sub
        (i32.mul (local.get $cy) (i32.const 1000))
        (i32.mul (local.get $b_approx) (i32.const 866))
      )
    )
    ;; dist_sq = (dx1000*dx1000 + dy1000*dy1000) / 1000000
    ;; We skip the division and compare raw values
    (local.set $best_dist_sq
      (i32.add
        (i32.mul (local.get $dx1000) (local.get $dx1000))
        (i32.mul (local.get $dy1000) (local.get $dy1000))
      )
    )

    ;; Search 3x3 neighborhood
    (local.set $da (i32.const -1))
    (block $da_done
      (loop $da_loop
        (local.set $db (i32.const -1))
        (block $db_done
          (loop $db_loop
            (local.set $test_a (i32.add (local.get $a_approx) (local.get $da)))
            (local.set $test_b (i32.add (local.get $b_approx) (local.get $db)))

            ;; dx1000 = 1000*cx - (1000*test_a - 500*test_b)
            (local.set $dx1000
              (i32.sub
                (i32.sub
                  (i32.mul (local.get $cx) (i32.const 1000))
                  (i32.mul (local.get $test_a) (i32.const 1000))
                )
                (i32.mul (local.get $test_b) (i32.const -500))
              )
            )
            ;; dy1000 = 1000*cy - test_b*866
            (local.set $dy1000
              (i32.sub
                (i32.mul (local.get $cy) (i32.const 1000))
                (i32.mul (local.get $test_b) (i32.const 866))
              )
            )
            ;; dist_sq = dx1000^2 + dy1000^2
            (local.set $dist_sq
              (i32.add
                (i32.mul (local.get $dx1000) (local.get $dx1000))
                (i32.mul (local.get $dy1000) (local.get $dy1000))
              )
            )

            ;; If this candidate is strictly closer, update best
            (if (i32.lt_s (local.get $dist_sq) (local.get $best_dist_sq))
              (then
                (local.set $best_dist_sq (local.get $dist_sq))
                (local.set $best_a (local.get $test_a))
                (local.set $best_b (local.get $test_b))
              )
            )
            ;; On equal distance, prefer candidate with smaller Eisenstein norm
            (if (i32.eq (local.get $dist_sq) (local.get $best_dist_sq))
              (then
                (local.set $tmp (call $eisenstein_norm_sq_func (local.get $test_a) (local.get $test_b)))
                (local.set $tmp2 (call $eisenstein_norm_sq_func (local.get $best_a) (local.get $best_b)))
                (if (i32.lt_s (local.get $tmp) (local.get $tmp2))
                  (then
                    (local.set $best_dist_sq (local.get $dist_sq))
                    (local.set $best_a (local.get $test_a))
                    (local.set $best_b (local.get $test_b))
                  )
                )
              )
            )

            (local.set $db (i32.add (local.get $db) (i32.const 1)))
            (br_if $db_loop (i32.le_s (local.get $db) (i32.const 1)))
          )
        )

        (local.set $da (i32.add (local.get $da) (i32.const 1)))
        (br_if $da_loop (i32.le_s (local.get $da) (i32.const 1)))
      )
    )

    (i32.store (i32.add (local.get $offset) (i32.const 8)) (local.get $best_a))
    (i32.store (i32.add (local.get $offset) (i32.const 12)) (local.get $best_b))

    (i32.const 1)
  )

  ;; ============ Batch Snap ============
  (func $batch_snap_func (export "batch_snap") (param $data_offset i32) (param $tile_count i32) (result i32)
    (local $i i32)
    (local $snapped i32)

    (local.set $snapped (i32.const 0))
    (local.set $i (i32.const 0))

    (block $batch_done
      (loop $batch_loop
        (if (i32.ge_u (local.get $i) (local.get $tile_count))
          (br $batch_done)
        )
        (local.set $snapped
          (i32.add (local.get $snapped) (call $snap_func (local.get $i)))
        )
        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $batch_loop)
      )
    )

    (local.get $snapped)
  )

  ;; ============ Dodecet Encode ============
  ;; Pack 12 constraint states (each 0-3, 2 bits) into a 24-bit value
  (func $dodecet_encode_func (export "dodecet_encode")
    (param $s0 i32) (param $s1 i32) (param $s2 i32) (param $s3 i32)
    (param $s4 i32) (param $s5 i32) (param $s6 i32) (param $s7 i32)
    (param $s8 i32) (param $s9 i32) (param $s10 i32) (param $s11 i32)
    (result i32)

    (local $result i32)
    (local.set $result
      (i32.or
        (i32.or
          (i32.or
            (i32.or
              (i32.or
                (i32.or
                  (i32.or
                    (i32.or
                      (i32.or
                        (i32.or
                          (i32.and (local.get $s0) (i32.const 3))
                          (i32.shl (i32.and (local.get $s1) (i32.const 3)) (i32.const 2))
                        )
                        (i32.shl (i32.and (local.get $s2) (i32.const 3)) (i32.const 4))
                      )
                      (i32.shl (i32.and (local.get $s3) (i32.const 3)) (i32.const 6))
                    )
                    (i32.shl (i32.and (local.get $s4) (i32.const 3)) (i32.const 8))
                  )
                  (i32.shl (i32.and (local.get $s5) (i32.const 3)) (i32.const 10))
                )
                (i32.shl (i32.and (local.get $s6) (i32.const 3)) (i32.const 12))
              )
              (i32.shl (i32.and (local.get $s7) (i32.const 3)) (i32.const 14))
            )
            (i32.shl (i32.and (local.get $s8) (i32.const 3)) (i32.const 16))
          )
          (i32.shl (i32.and (local.get $s9) (i32.const 3)) (i32.const 18))
        )
        (i32.or
          (i32.shl (i32.and (local.get $s10) (i32.const 3)) (i32.const 20))
          (i32.shl (i32.and (local.get $s11) (i32.const 3)) (i32.const 22))
        )
      )
    )

    (local.get $result)
  )

  ;; ============ Dodecet Decode ============
  ;; Unpack from offset, write 12 decoded bytes to offset+4..offset+15
  (func $dodecet_decode_func (export "dodecet_decode") (param $offset i32)
    (local $packed i32)
    (local $i i32)
    (local $shift i32)

    (local.set $packed (i32.load (local.get $offset)))
    (local.set $i (i32.const 0))

    (block $decode_done
      (loop $decode_loop
        (if (i32.eq (local.get $i) (i32.const 12))
          (br $decode_done)
        )

        (local.set $shift (i32.shl (local.get $i) (i32.const 1)))

        (i32.store8
          (i32.add (i32.add (local.get $offset) (i32.const 4)) (local.get $i))
          (i32.and
            (i32.shr_u (local.get $packed) (local.get $shift))
            (i32.const 3)
          )
        )

        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $decode_loop)
      )
    )
  )

  ;; ============ 3-Tier Constraint Check ============
  ;; Run full constraint check on tile array in memory.
  ;;
  ;; Input:
  ;;   data_offset: byte offset of tile array start
  ;;   tile_count: number of tiles to check
  ;;   output_offset: where to write result byte
  ;;   lut_offset: byte offset of LUT (reserved, may be 0)
  ;;
  ;; Output (written to output_offset):
  ;;   bit 0: tier1 pass (local constraints - Admit 432)
  ;;   bit 1: tier2 pass (regional - parity/density)
  ;;   bit 2: tier3 pass (global - sum/integrity)
  ;;   bit 3: all pass
  ;;   bit 4: tier1 violations present
  ;;   bit 5: tier2 violations present
  ;;   bit 6: tier3 violations present
  ;;
  ;; Tile: 16 bytes each, +0:x, +4:y, +8:state, +12:color

  (func $constraint_check_func (export "constraint_check")
    (param $data_offset i32)
    (param $tile_count i32)
    (param $output_offset i32)
    (param $lut_offset i32)
    (result i32)

    (local $i i32)
    (local $j i32)
    (local $stride i32)
    (local $tile_offset i32)
    (local $result i32)

    ;; Tier results
    (local $tier1_pass i32)
    (local $tier2_pass i32)
    (local $tier3_pass i32)
    (local $tier1_violations i32)
    (local $tier2_violations i32)
    (local $tier3_violations i32)

    ;; Working variables
    (local $color_a i32)
    (local $color_b i32)
    (local $state_a i32)
    (local $state_sum i32)
    (local $occupied i32)
    (local $cluster_offset i32)

    (local.set $stride (i32.const 16))  ;; 16 bytes per tile
    (local.set $tier1_pass (i32.const 1))
    (local.set $tier2_pass (i32.const 1))
    (local.set $tier3_pass (i32.const 1))
    (local.set $tier1_violations (i32.const 0))
    (local.set $tier2_violations (i32.const 0))
    (local.set $tier3_violations (i32.const 0))
    (local.set $result (i32.const 0))

    ;; ===== TIER 1: Local Constraints (Admit 432) =====
    (local.set $i (i32.const 0))
    (block $tier1_done
      (loop $tier1_loop
        (if (i32.ge_u (local.get $i) (local.get $tile_count))
          (br $tier1_done)
        )

        (local.set $tile_offset
          (i32.add (local.get $data_offset) (i32.mul (local.get $i) (local.get $stride)))
        )
        (local.set $color_a (i32.load (i32.add (local.get $tile_offset) (i32.const 12))))

        (if (i32.lt_u (i32.add (local.get $i) (i32.const 1)) (local.get $tile_count))
          (then
            (local.set $tile_offset
              (i32.add
                (local.get $data_offset)
                (i32.mul (i32.add (local.get $i) (i32.const 1)) (local.get $stride))
              )
            )
            (local.set $color_b (i32.load (i32.add (local.get $tile_offset) (i32.const 12))))

            (if (i32.eq (local.get $color_a) (local.get $color_b))
              (then
                (local.set $tier1_pass (i32.const 0))
                (local.set $tier1_violations (i32.add (local.get $tier1_violations) (i32.const 1)))
              )
            )
          )
        )

        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $tier1_loop)
      )
    )

    ;; ===== TIER 2: Regional Constraints =====
    ;; Groups of 4 tiles form a cluster
    ;; For each full cluster: parity (even sum), density [1, 3]

    (local.set $i (i32.const 0))
    (block $tier2_done
      (loop $tier2_outer
        (if (i32.ge_u (local.get $i) (local.get $tile_count))
          (br $tier2_done)
        )

        (if (i32.le_u (i32.add (local.get $i) (i32.const 3)) (local.get $tile_count))
          (then
            (local.set $state_sum (i32.const 0))
            (local.set $occupied (i32.const 0))
            (local.set $j (i32.const 0))

            (loop $cluster_loop
              (if (i32.lt_u (local.get $j) (i32.const 4))
                (then
                  (local.set $cluster_offset
                    (i32.add
                      (local.get $data_offset)
                      (i32.mul (i32.add (local.get $i) (local.get $j)) (local.get $stride))
                    )
                  )
                  (local.set $state_a (i32.load (i32.add (local.get $cluster_offset) (i32.const 8))))
                  (local.set $state_sum (i32.add (local.get $state_sum) (local.get $state_a)))
                  (if (i32.ne (local.get $state_a) (i32.const 0))
                    (local.set $occupied (i32.add (local.get $occupied) (i32.const 1)))
                  )
                  (local.set $j (i32.add (local.get $j) (i32.const 1)))
                  (br $cluster_loop)
                )
              )
            )

            ;; Parity check
            (if (i32.ne (i32.and (local.get $state_sum) (i32.const 1)) (i32.const 0))
              (then
                (local.set $tier2_pass (i32.const 0))
                (local.set $tier2_violations (i32.add (local.get $tier2_violations) (i32.const 1)))
              )
            )

            ;; Density check
            (if (i32.lt_u (local.get $occupied) (i32.const 1))
              (then
                (local.set $tier2_pass (i32.const 0))
                (local.set $tier2_violations (i32.add (local.get $tier2_violations) (i32.const 1)))
              )
            )
            (if (i32.gt_u (local.get $occupied) (i32.const 3))
              (then
                (local.set $tier2_pass (i32.const 0))
                (local.set $tier2_violations (i32.add (local.get $tier2_violations) (i32.const 1)))
              )
            )
          )
        )

        (local.set $i (i32.add (local.get $i) (i32.const 4)))
        (br $tier2_outer)
      )
    )

    ;; ===== TIER 3: Global Constraints =====
    (local.set $state_sum (i32.const 0))
    (local.set $i (i32.const 0))

    (block $tier3_sum_done
      (loop $tier3_sum_loop
        (if (i32.ge_u (local.get $i) (local.get $tile_count))
          (br $tier3_sum_done)
        )

        (local.set $tile_offset
          (i32.add (local.get $data_offset) (i32.mul (local.get $i) (local.get $stride)))
        )
        (local.set $state_a (i32.load (i32.add (local.get $tile_offset) (i32.const 8))))

        (local.set $state_sum (i32.add (local.get $state_sum) (local.get $state_a)))

        ;; Non-negative check
        (if (i32.lt_s (local.get $state_a) (i32.const 0))
          (then
            (local.set $tier3_pass (i32.const 0))
            (local.set $tier3_violations (i32.add (local.get $tier3_violations) (i32.const 1)))
          )
        )

        (local.set $i (i32.add (local.get $i) (i32.const 1)))
        (br $tier3_sum_loop)
      )
    )

    ;; Global parity
    (if (i32.ne (i32.and (local.get $state_sum) (i32.const 1)) (i32.const 0))
      (then
        (local.set $tier3_pass (i32.const 0))
        (local.set $tier3_violations (i32.add (local.get $tier3_violations) (i32.const 1)))
      )
    )

    ;; ===== Build Result Byte =====
    (if (local.get $tier1_pass)
      (local.set $result (i32.or (local.get $result) (i32.const 1)))
    )
    (if (local.get $tier2_pass)
      (local.set $result (i32.or (local.get $result) (i32.const 2)))
    )
    (if (local.get $tier3_pass)
      (local.set $result (i32.or (local.get $result) (i32.const 4)))
    )
    (if (i32.eq (i32.and (local.get $result) (i32.const 7)) (i32.const 7))
      (local.set $result (i32.or (local.get $result) (i32.const 8)))
    )
    (if (i32.gt_u (local.get $tier1_violations) (i32.const 0))
      (local.set $result (i32.or (local.get $result) (i32.const 16)))
    )
    (if (i32.gt_u (local.get $tier2_violations) (i32.const 0))
      (local.set $result (i32.or (local.get $result) (i32.const 32)))
    )
    (if (i32.gt_u (local.get $tier3_violations) (i32.const 0))
      (local.set $result (i32.or (local.get $result) (i32.const 64)))
    )

    ;; Store result
    (i32.store8 (local.get $output_offset) (local.get $result))

    (local.get $result)
  )
)
