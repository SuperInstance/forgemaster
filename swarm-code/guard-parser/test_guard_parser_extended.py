"""
Extended tests for guard_parser.py — generated from 5,500 test vectors.
Tests parsing and structural correctness of GUARD DSL expressions.
"""

import pytest
from guard_parser import tokenize, parse_guard, ExprNode


def _flatten(node):
    """Recursively flatten an ExprNode tree into a list of all nodes."""
    from guard_parser import ExprNode
    result = [node]
    for arg in getattr(node, 'args', []):
        if isinstance(arg, ExprNode):
            result.extend(_flatten(arg))
    return result


VECTORS = [
    # [1] adv_dead_code_elim (adversarial_constraints)
    {
        "name": 'adv_dead_code_elim',
        "src": 'constraint dead_code { expr: (x > 0 && false) || (x <= 0 && true), inputs: [x: i32] }',
        "inputs": [-5],
        "expected": [True],
    },
    # [2] adv_jit_boundary_44 (adversarial_constraints)
    {
        "name": 'adv_jit_boundary_44',
        "src": 'constraint adv_jit_boundary_44 { expr: x >= -128 && x <= 127 && x == x && x <= x && x >= x, inputs: [x: i32] }',
        "inputs": [-69],
        "expected": [True],
    },
    # [3] adv_associative_227 (adversarial_constraints)
    {
        "name": 'adv_associative_227',
        "src": 'constraint adv_associative_227 { expr: (x + y) + z == x + (y + z), inputs: [x: i32, y: i32, z: i32] }',
        "inputs": [-44, -35, 0],
        "expected": [True],
    },
    # [4] adv_abs_10 (adversarial_constraints)
    {
        "name": 'adv_abs_10',
        "src": 'constraint adv_abs_10 { expr: x >= 0 || (-x) > 0, inputs: [x: i32] }',
        "inputs": [-43],
        "expected": [True],
    },
    # [5] adv_tautology_455 (adversarial_constraints)
    {
        "name": 'adv_tautology_455',
        "src": 'constraint adv_tautology_455 { expr: x > 0 || x <= 0, inputs: [x: i32] }',
        "inputs": [-129],
        "expected": [True],
    },
    # [6] adv_shortcircuit_4 (adversarial_constraints)
    {
        "name": 'adv_shortcircuit_4',
        "src": 'constraint adv_shortcircuit_4 { expr: x == 0 || (100 / x) > 0, inputs: [x: i32] }',
        "inputs": [0],
        "expected": [True],
    },
    # [7] adv_div_self_31 (adversarial_constraints)
    {
        "name": 'adv_div_self_31',
        "src": 'constraint adv_div_self_31 { expr: x != 0 && x / x == 1, inputs: [x: i32] }',
        "inputs": [-73],
        "expected": [True],
    },
    # [8] adv_algebraic_0 (adversarial_constraints)
    {
        "name": 'adv_algebraic_0',
        "src": 'constraint adv_algebraic_0 { expr: (x + y) - y == x, inputs: [x: i32, y: i32] }',
        "inputs": [-73, -79],
        "expected": [True],
    },
    # [9] adv_signed_cmp_12 (adversarial_constraints)
    {
        "name": 'adv_signed_cmp_12',
        "src": 'constraint adv_signed_cmp_12 { expr: x < y, inputs: [x: i32, y: i32] }',
        "inputs": [-128, 127],
        "expected": [True],
    },
    # [10] adv_const_fold_trap (adversarial_constraints)
    {
        "name": 'adv_const_fold_trap',
        "src": 'constraint const_fold { expr: x * 0 == 0 && x + 0 == x, inputs: [x: i32] }',
        "inputs": [127],
        "expected": [True],
    },
    # [11] stress_balanced_or_99 (stress_patterns)
    {
        "name": 'stress_balanced_or_99',
        "src": 'constraint stress_balanced_or_99 { expr: ((((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))))) || (((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))))), inputs: [x: i32] }',
        "inputs": [1],
        "expected": [True],
    },
    # [12] stress_balanced_and_110 (stress_patterns)
    {
        "name": 'stress_balanced_and_110',
        "src": 'constraint stress_balanced_and_110 { expr: ((((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))))) && (((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))))), inputs: [x: i32] }',
        "inputs": [1],
        "expected": [True],
    },
    # [13] stress_balanced_or_15 (stress_patterns)
    {
        "name": 'stress_balanced_or_15',
        "src": 'constraint stress_balanced_or_15 { expr: (((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))))), inputs: [x: i32] }',
        "inputs": [1],
        "expected": [True],
    },
    # [14] stress_balanced_and_170 (stress_patterns)
    {
        "name": 'stress_balanced_and_170',
        "src": 'constraint stress_balanced_and_170 { expr: (((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))))), inputs: [x: i32] }',
        "inputs": [1],
        "expected": [True],
    },
    # [15] stress_and_chain_d50_252 (stress_patterns)
    {
        "name": 'stress_and_chain_d50_252',
        "src": 'constraint stress_and_chain_d50_252 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45 && x > 46 && x > 47 && x > 48 && x > 49, inputs: [x: i32] }',
        "inputs": [59],
        "expected": [True],
    },
    # [16] stress_and_chain_d49_204 (stress_patterns)
    {
        "name": 'stress_and_chain_d49_204',
        "src": 'constraint stress_and_chain_d49_204 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45 && x > 46 && x > 47 && x > 48, inputs: [x: i32] }',
        "inputs": [51],
        "expected": [True],
    },
    # [17] stress_or_chain_d48_337 (stress_patterns)
    {
        "name": 'stress_or_chain_d48_337',
        "src": 'constraint stress_or_chain_d48_337 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45 || x < 46 || x < 47, inputs: [x: i32] }',
        "inputs": [25],
        "expected": [True],
    },
    # [18] stress_or_chain_d47_97 (stress_patterns)
    {
        "name": 'stress_or_chain_d47_97',
        "src": 'constraint stress_or_chain_d47_97 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45 || x < 46, inputs: [x: i32] }',
        "inputs": [20],
        "expected": [True],
    },
    # [19] stress_or_chain_d46_13 (stress_patterns)
    {
        "name": 'stress_or_chain_d46_13',
        "src": 'constraint stress_or_chain_d46_13 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45, inputs: [x: i32] }',
        "inputs": [9],
        "expected": [True],
    },
    # [20] stress_and_chain_d46_144 (stress_patterns)
    {
        "name": 'stress_and_chain_d46_144',
        "src": 'constraint stress_and_chain_d46_144 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45, inputs: [x: i32] }',
        "inputs": [48],
        "expected": [True],
    },
    # [21] boundary_compound_19 (boundary_values)
    {
        "name": 'boundary_compound_19',
        "src": 'constraint boundary_compound_19 { expr: (x >= -128 && x <= 127) || (x == 200), inputs: [x: i32] }',
        "inputs": [200],
        "expected": [False],
    },
    # [22] boundary_range_min_8 (boundary_values)
    {
        "name": 'boundary_range_min_8',
        "src": 'constraint boundary_range_min_8 { expr: x >= -128 && x <= -100, inputs: [x: i32] }',
        "inputs": [-128],
        "expected": [True],
    },
    # [23] int8_min_exact (boundary_values)
    {
        "name": 'int8_min_exact',
        "src": 'constraint min_check { expr: x >= -128, inputs: [x: i32] }',
        "inputs": [-128],
        "expected": [True],
    },
    # [24] int8_underflow_by_one (boundary_values)
    {
        "name": 'int8_underflow_by_one',
        "src": 'constraint underflow_check { expr: x >= -128, inputs: [x: i32] }',
        "inputs": [-129],
        "expected": [False],
    },
    # [25] boundary_exact_min_1 (boundary_values)
    {
        "name": 'boundary_exact_min_1',
        "src": 'constraint boundary_exact_min_1 { expr: x >= -128, inputs: [x: i32] }',
        "inputs": [-128],
        "expected": [True],
    },
    # [26] boundary_underflow_1_3 (boundary_values)
    {
        "name": 'boundary_underflow_1_3',
        "src": 'constraint boundary_underflow_1_3 { expr: x > -129, inputs: [x: i32] }',
        "inputs": [-129],
        "expected": [False],
    },
    # [27] boundary_eq_min_15 (boundary_values)
    {
        "name": 'boundary_eq_min_15',
        "src": 'constraint boundary_eq_min_15 { expr: x == -128, inputs: [x: i32] }',
        "inputs": [-128],
        "expected": [True],
    },
    # [28] boundary_strict_gt_min_17 (boundary_values)
    {
        "name": 'boundary_strict_gt_min_17',
        "src": 'constraint boundary_strict_gt_min_17 { expr: x > -128, inputs: [x: i32] }',
        "inputs": [-128],
        "expected": [False],
    },
    # [29] boundary_near_zero_neg_6 (boundary_values)
    {
        "name": 'boundary_near_zero_neg_6',
        "src": 'constraint boundary_near_zero_neg_6 { expr: x > -2 && x < 0, inputs: [x: i32] }',
        "inputs": [-1],
        "expected": [True],
    },
    # [30] boundary_range_max_7 (boundary_values)
    {
        "name": 'boundary_range_max_7',
        "src": 'constraint boundary_range_max_7 { expr: x >= 100 && x <= 127, inputs: [x: i32] }',
        "inputs": [127],
        "expected": [True],
    },
    # [31] fuzz_nested_random_002 (random_fuzzing)
    {
        "name": 'fuzz_nested_random_002',
        "src": 'constraint fuzz_002 { expr: (x > 0 || y < 0) && (x + y > 10), inputs: [x: i32, y: i32] }',
        "inputs": [-129, 177],
        "expected": [False],
    },
    # [32] fuzz_high_entropy_005 (random_fuzzing)
    {
        "name": 'fuzz_high_entropy_005',
        "src": 'constraint fuzz_005 { expr: a > 10 && b < 90 && c >= 20 && d <= 80 && a + b > c + d, inputs: [a: i32, b: i32, c: i32, d: i32] }',
        "inputs": [79, -156, 102, 16],
        "expected": [None],
    },
    # [33] fuzz_edge_random_004 (random_fuzzing)
    {
        "name": 'fuzz_edge_random_004',
        "src": 'constraint fuzz_004 { expr: x >= -128 && x <= 127 && x != 0, inputs: [x: i32] }',
        "inputs": [0],
        "expected": [False],
    },
    # [34] fuzz_simple_random_001 (random_fuzzing)
    {
        "name": 'fuzz_simple_random_001',
        "src": 'constraint fuzz_001 { expr: x > 50 && x < 100, inputs: [x: i32] }',
        "inputs": [-86],
        "expected": [False],
    },
    # [35] type_bool_arith_138 (type_confusion)
    {
        "name": 'type_bool_arith_138',
        "src": 'constraint type_bool_arith_138 { expr: (x > 0) + (y > 0) >= 1, inputs: [x: i32, y: i32] }',
        "inputs": [-1, 0],
        "expected": [False],
    },
    # [36] type_widening_narrowing (type_confusion)
    {
        "name": 'type_widening_narrowing',
        "src": 'constraint type_wide { expr: (x + y) >= -128 && (x + y) <= 127, inputs: [x: i32, y: i32] }',
        "inputs": [100, 100],
        "expected": [False],
    },
    # [37] type_mul_overflow_10 (type_confusion)
    {
        "name": 'type_mul_overflow_10',
        "src": 'constraint type_mul_overflow_10 { expr: (x * y) <= 127 && (x * y) >= -128, inputs: [x: i32, y: i32] }',
        "inputs": [16, 13],
        "expected": [False],
    },
    # [38] type_complex_11 (type_confusion)
    {
        "name": 'type_complex_11',
        "src": 'constraint type_complex_11 { expr: (x + y) > z && z >= -128 && z <= 127, inputs: [x: i32, y: i32, z: i32] }',
        "inputs": [10, 20, 30],
        "expected": [True],
    },
    # [39] type_promote_cmp_5 (type_confusion)
    {
        "name": 'type_promote_cmp_5',
        "src": 'constraint type_promote_cmp_5 { expr: x == (x / 2) * 2, inputs: [x: i32] }',
        "inputs": [-117],
        "expected": [True],
    },
    # [40] type_signed_unsigned_mix (type_confusion)
    {
        "name": 'type_signed_unsigned_mix',
        "src": 'constraint type_sign { expr: x >= 0 && x <= 255, inputs: [x: i32] }',
        "inputs": [-1],
        "expected": [False],
    },
    # [41] type_neg_overflow_1 (type_confusion)
    {
        "name": 'type_neg_overflow_1',
        "src": 'constraint type_neg_overflow_1 { expr: x >= -128, inputs: [x: i32] }',
        "inputs": [-672],
        "expected": [False],
    },
    # [42] type_mixed_arith_4 (type_confusion)
    {
        "name": 'type_mixed_arith_4',
        "src": 'constraint type_mixed_arith_4 { expr: (x + y) < 128, inputs: [x: i32, y: i32] }',
        "inputs": [75, 71],
        "expected": [False],
    },
    # [43] type_unsigned_signed_38 (type_confusion)
    {
        "name": 'type_unsigned_signed_38',
        "src": 'constraint type_unsigned_signed_38 { expr: x <= 127, inputs: [x: i32] }',
        "inputs": [128],
        "expected": [False],
    },
    # [44] type_int8_vs_int16_overflow (type_confusion)
    {
        "name": 'type_int8_vs_int16_overflow',
        "src": 'constraint type_i8_i16 { expr: x >= -128 && x <= 127, inputs: [x: i32] }',
        "inputs": [200],
        "expected": [False],
    },
    # [45] conc_multidevice_92 (concurrency_scenarios)
    {
        "name": 'conc_multidevice_92',
        "src": 'constraint conc_multidevice_92 { expr: val_cpu == val_gpu && val_gpu == val_fpga, inputs: [val_cpu: i32, val_gpu: i32, val_fpga: i32], coherent: true }',
        "inputs": [-128, -128, -128],
        "expected": [True],
    },
    # [46] conc_snapshot_isolation (concurrency_scenarios)
    {
        "name": 'conc_snapshot_isolation',
        "src": 'constraint snapshot { expr: x >= 0 && x <= 127 && y >= 0 && y <= 127, inputs: [x: i32, y: i32], snapshot: true }',
        "inputs": [100, 50],
        "expected": [True],
    },
    # [47] conc_time_based_4 (concurrency_scenarios)
    {
        "name": 'conc_time_based_4',
        "src": 'constraint conc_time_based_4 { expr: now >= start && now <= deadline, inputs: [now: i32, start: i32, deadline: i32], monotonic: true }',
        "inputs": [500, 0, 1000],
        "expected": [True],
    },
    # [48] conc_tx_rollback_11 (concurrency_scenarios)
    {
        "name": 'conc_tx_rollback_11',
        "src": 'constraint conc_tx_rollback_11 { expr: committed || original_value == current_value, inputs: [committed: i32, original_value: i32, current_value: i32] }',
        "inputs": [0, 72, 58],
        "expected": [False],
    },
    # [49] conc_cpugpu_sync_8 (concurrency_scenarios)
    {
        "name": 'conc_cpugpu_sync_8',
        "src": 'constraint conc_cpugpu_sync_8 { expr: gpu_val == cpu_val, inputs: [gpu_val: i32, cpu_val: i32], sync_point: true }',
        "inputs": [93, -68],
        "expected": [False],
    },
    # [50] conc_atomic_read (concurrency_scenarios)
    {
        "name": 'conc_atomic_read',
        "src": 'constraint atomic_read { expr: x >= 0 && x <= 100, inputs: [x: i32], volatile: true }',
        "inputs": [50],
        "expected": [True],
    },
]

@pytest.mark.parametrize("vector", VECTORS, ids=[v["name"] for v in VECTORS])
def test_vector_parses(vector):
    """Each test vector should parse without errors."""
    ast = parse_guard(vector["src"])
    assert ast is not None
    assert ast.name
    assert ast.expr is not None


def test_adv_dead_code_elim():
    """[adversarial_constraints] adv_dead_code_elim"""
    ast = parse_guard('constraint dead_code { expr: (x > 0 && false) || (x <= 0 && true), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_adv_jit_boundary_44():
    """[adversarial_constraints] adv_jit_boundary_44"""
    ast = parse_guard('constraint adv_jit_boundary_44 { expr: x >= -128 && x <= 127 && x == x && x <= x && x >= x, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_adv_associative_227():
    """[adversarial_constraints] adv_associative_227"""
    ast = parse_guard('constraint adv_associative_227 { expr: (x + y) + z == x + (y + z), inputs: [x: i32, y: i32, z: i32] }')
    assert len(ast.inputs) == 3

def test_adv_abs_10():
    """[adversarial_constraints] adv_abs_10"""
    ast = parse_guard('constraint adv_abs_10 { expr: x >= 0 || (-x) > 0, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_adv_tautology_455():
    """[adversarial_constraints] adv_tautology_455"""
    ast = parse_guard('constraint adv_tautology_455 { expr: x > 0 || x <= 0, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_adv_shortcircuit_4():
    """[adversarial_constraints] adv_shortcircuit_4"""
    ast = parse_guard('constraint adv_shortcircuit_4 { expr: x == 0 || (100 / x) > 0, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_adv_div_self_31():
    """[adversarial_constraints] adv_div_self_31"""
    ast = parse_guard('constraint adv_div_self_31 { expr: x != 0 && x / x == 1, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    nodes = _flatten(ast.expr)
    assert len(ast.inputs) == 1

def test_adv_algebraic_0():
    """[adversarial_constraints] adv_algebraic_0"""
    ast = parse_guard('constraint adv_algebraic_0 { expr: (x + y) - y == x, inputs: [x: i32, y: i32] }')
    assert len(ast.inputs) == 2

def test_adv_signed_cmp_12():
    """[adversarial_constraints] adv_signed_cmp_12"""
    ast = parse_guard('constraint adv_signed_cmp_12 { expr: x < y, inputs: [x: i32, y: i32] }')
    assert len(ast.inputs) == 2

def test_adv_const_fold_trap():
    """[adversarial_constraints] adv_const_fold_trap"""
    ast = parse_guard('constraint const_fold { expr: x * 0 == 0 && x + 0 == x, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    nodes = _flatten(ast.expr)
    assert any(n.op == "MUL" for n in nodes), "Expected MUL in expression tree"
    assert len(ast.inputs) == 1

def test_stress_balanced_or_99():
    """[stress_patterns] stress_balanced_or_99"""
    ast = parse_guard('constraint stress_balanced_or_99 { expr: ((((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))))) || (((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))))), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_stress_balanced_and_110():
    """[stress_patterns] stress_balanced_and_110"""
    ast = parse_guard('constraint stress_balanced_and_110 { expr: ((((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))))) && (((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))))), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_stress_balanced_or_15():
    """[stress_patterns] stress_balanced_or_15"""
    ast = parse_guard('constraint stress_balanced_or_15 { expr: (((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0)))) || ((((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))) || (((x > 0 || x > 0) || (x > 0 || x > 0)) || ((x > 0 || x > 0) || (x > 0 || x > 0))))), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_stress_balanced_and_170():
    """[stress_patterns] stress_balanced_and_170"""
    ast = parse_guard('constraint stress_balanced_and_170 { expr: (((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0)))) && ((((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))) && (((x > 0 && x > 0) && (x > 0 && x > 0)) && ((x > 0 && x > 0) && (x > 0 && x > 0))))), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_stress_and_chain_d50_252():
    """[stress_patterns] stress_and_chain_d50_252"""
    ast = parse_guard('constraint stress_and_chain_d50_252 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45 && x > 46 && x > 47 && x > 48 && x > 49, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_stress_and_chain_d49_204():
    """[stress_patterns] stress_and_chain_d49_204"""
    ast = parse_guard('constraint stress_and_chain_d49_204 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45 && x > 46 && x > 47 && x > 48, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_stress_or_chain_d48_337():
    """[stress_patterns] stress_or_chain_d48_337"""
    ast = parse_guard('constraint stress_or_chain_d48_337 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45 || x < 46 || x < 47, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_stress_or_chain_d47_97():
    """[stress_patterns] stress_or_chain_d47_97"""
    ast = parse_guard('constraint stress_or_chain_d47_97 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45 || x < 46, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_stress_or_chain_d46_13():
    """[stress_patterns] stress_or_chain_d46_13"""
    ast = parse_guard('constraint stress_or_chain_d46_13 { expr: x < 0 || x < 1 || x < 2 || x < 3 || x < 4 || x < 5 || x < 6 || x < 7 || x < 8 || x < 9 || x < 10 || x < 11 || x < 12 || x < 13 || x < 14 || x < 15 || x < 16 || x < 17 || x < 18 || x < 19 || x < 20 || x < 21 || x < 22 || x < 23 || x < 24 || x < 25 || x < 26 || x < 27 || x < 28 || x < 29 || x < 30 || x < 31 || x < 32 || x < 33 || x < 34 || x < 35 || x < 36 || x < 37 || x < 38 || x < 39 || x < 40 || x < 41 || x < 42 || x < 43 || x < 44 || x < 45, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 1

def test_stress_and_chain_d46_144():
    """[stress_patterns] stress_and_chain_d46_144"""
    ast = parse_guard('constraint stress_and_chain_d46_144 { expr: x > 0 && x > 1 && x > 2 && x > 3 && x > 4 && x > 5 && x > 6 && x > 7 && x > 8 && x > 9 && x > 10 && x > 11 && x > 12 && x > 13 && x > 14 && x > 15 && x > 16 && x > 17 && x > 18 && x > 19 && x > 20 && x > 21 && x > 22 && x > 23 && x > 24 && x > 25 && x > 26 && x > 27 && x > 28 && x > 29 && x > 30 && x > 31 && x > 32 && x > 33 && x > 34 && x > 35 && x > 36 && x > 37 && x > 38 && x > 39 && x > 40 && x > 41 && x > 42 && x > 43 && x > 44 && x > 45, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_boundary_compound_19():
    """[boundary_values] boundary_compound_19"""
    ast = parse_guard('constraint boundary_compound_19 { expr: (x >= -128 && x <= 127) || (x == 200), inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_boundary_range_min_8():
    """[boundary_values] boundary_range_min_8"""
    ast = parse_guard('constraint boundary_range_min_8 { expr: x >= -128 && x <= -100, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_int8_min_exact():
    """[boundary_values] int8_min_exact"""
    ast = parse_guard('constraint min_check { expr: x >= -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_int8_underflow_by_one():
    """[boundary_values] int8_underflow_by_one"""
    ast = parse_guard('constraint underflow_check { expr: x >= -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_boundary_exact_min_1():
    """[boundary_values] boundary_exact_min_1"""
    ast = parse_guard('constraint boundary_exact_min_1 { expr: x >= -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_boundary_underflow_1_3():
    """[boundary_values] boundary_underflow_1_3"""
    ast = parse_guard('constraint boundary_underflow_1_3 { expr: x > -129, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_boundary_eq_min_15():
    """[boundary_values] boundary_eq_min_15"""
    ast = parse_guard('constraint boundary_eq_min_15 { expr: x == -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_boundary_strict_gt_min_17():
    """[boundary_values] boundary_strict_gt_min_17"""
    ast = parse_guard('constraint boundary_strict_gt_min_17 { expr: x > -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_boundary_near_zero_neg_6():
    """[boundary_values] boundary_near_zero_neg_6"""
    ast = parse_guard('constraint boundary_near_zero_neg_6 { expr: x > -2 && x < 0, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_boundary_range_max_7():
    """[boundary_values] boundary_range_max_7"""
    ast = parse_guard('constraint boundary_range_max_7 { expr: x >= 100 && x <= 127, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_fuzz_nested_random_002():
    """[random_fuzzing] fuzz_nested_random_002"""
    ast = parse_guard('constraint fuzz_002 { expr: (x > 0 || y < 0) && (x + y > 10), inputs: [x: i32, y: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 2

def test_fuzz_high_entropy_005():
    """[random_fuzzing] fuzz_high_entropy_005"""
    ast = parse_guard('constraint fuzz_005 { expr: a > 10 && b < 90 && c >= 20 && d <= 80 && a + b > c + d, inputs: [a: i32, b: i32, c: i32, d: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 4

def test_fuzz_edge_random_004():
    """[random_fuzzing] fuzz_edge_random_004"""
    ast = parse_guard('constraint fuzz_004 { expr: x >= -128 && x <= 127 && x != 0, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    nodes = _flatten(ast.expr)
    assert len(ast.inputs) == 1

def test_fuzz_simple_random_001():
    """[random_fuzzing] fuzz_simple_random_001"""
    ast = parse_guard('constraint fuzz_001 { expr: x > 50 && x < 100, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_type_bool_arith_138():
    """[type_confusion] type_bool_arith_138"""
    ast = parse_guard('constraint type_bool_arith_138 { expr: (x > 0) + (y > 0) >= 1, inputs: [x: i32, y: i32] }')
    assert len(ast.inputs) == 2

def test_type_widening_narrowing():
    """[type_confusion] type_widening_narrowing"""
    ast = parse_guard('constraint type_wide { expr: (x + y) >= -128 && (x + y) <= 127, inputs: [x: i32, y: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 2

def test_type_mul_overflow_10():
    """[type_confusion] type_mul_overflow_10"""
    ast = parse_guard('constraint type_mul_overflow_10 { expr: (x * y) <= 127 && (x * y) >= -128, inputs: [x: i32, y: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    nodes = _flatten(ast.expr)
    assert any(n.op == "MUL" for n in nodes), "Expected MUL in expression tree"
    assert len(ast.inputs) == 2

def test_type_complex_11():
    """[type_confusion] type_complex_11"""
    ast = parse_guard('constraint type_complex_11 { expr: (x + y) > z && z >= -128 && z <= 127, inputs: [x: i32, y: i32, z: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 3

def test_type_promote_cmp_5():
    """[type_confusion] type_promote_cmp_5"""
    ast = parse_guard('constraint type_promote_cmp_5 { expr: x == (x / 2) * 2, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "MUL" for n in nodes), "Expected MUL in expression tree"
    assert len(ast.inputs) == 1

def test_type_signed_unsigned_mix():
    """[type_confusion] type_signed_unsigned_mix"""
    ast = parse_guard('constraint type_sign { expr: x >= 0 && x <= 255, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_type_neg_overflow_1():
    """[type_confusion] type_neg_overflow_1"""
    ast = parse_guard('constraint type_neg_overflow_1 { expr: x >= -128, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_type_mixed_arith_4():
    """[type_confusion] type_mixed_arith_4"""
    ast = parse_guard('constraint type_mixed_arith_4 { expr: (x + y) < 128, inputs: [x: i32, y: i32] }')
    assert len(ast.inputs) == 2

def test_type_unsigned_signed_38():
    """[type_confusion] type_unsigned_signed_38"""
    ast = parse_guard('constraint type_unsigned_signed_38 { expr: x <= 127, inputs: [x: i32] }')
    assert len(ast.inputs) == 1

def test_type_int8_vs_int16_overflow():
    """[type_confusion] type_int8_vs_int16_overflow"""
    ast = parse_guard('constraint type_i8_i16 { expr: x >= -128 && x <= 127, inputs: [x: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1

def test_conc_multidevice_92():
    """[concurrency_scenarios] conc_multidevice_92"""
    ast = parse_guard('constraint conc_multidevice_92 { expr: val_cpu == val_gpu && val_gpu == val_fpga, inputs: [val_cpu: i32, val_gpu: i32, val_fpga: i32], coherent: true }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 3

def test_conc_snapshot_isolation():
    """[concurrency_scenarios] conc_snapshot_isolation"""
    ast = parse_guard('constraint snapshot { expr: x >= 0 && x <= 127 && y >= 0 && y <= 127, inputs: [x: i32, y: i32], snapshot: true }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 2

def test_conc_time_based_4():
    """[concurrency_scenarios] conc_time_based_4"""
    ast = parse_guard('constraint conc_time_based_4 { expr: now >= start && now <= deadline, inputs: [now: i32, start: i32, deadline: i32], monotonic: true }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 3

def test_conc_tx_rollback_11():
    """[concurrency_scenarios] conc_tx_rollback_11"""
    ast = parse_guard('constraint conc_tx_rollback_11 { expr: committed || original_value == current_value, inputs: [committed: i32, original_value: i32, current_value: i32] }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "OR" for n in nodes), "Expected OR in expression tree"
    assert len(ast.inputs) == 3

def test_conc_cpugpu_sync_8():
    """[concurrency_scenarios] conc_cpugpu_sync_8"""
    ast = parse_guard('constraint conc_cpugpu_sync_8 { expr: gpu_val == cpu_val, inputs: [gpu_val: i32, cpu_val: i32], sync_point: true }')
    assert len(ast.inputs) == 2

def test_conc_atomic_read():
    """[concurrency_scenarios] conc_atomic_read"""
    ast = parse_guard('constraint atomic_read { expr: x >= 0 && x <= 100, inputs: [x: i32], volatile: true }')
    nodes = _flatten(ast.expr)
    assert any(n.op == "AND" for n in nodes), "Expected AND in expression tree"
    assert len(ast.inputs) == 1
