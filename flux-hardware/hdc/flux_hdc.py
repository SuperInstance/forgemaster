#!/usr/bin/env python3
"""
flux_hdc.py — Hyperdimensional Computing for Constraint Matching (v3)

FIXED: Multi-scale semantic encoding replaces naive text hashing.
Uses THREE complementary encoding strategies, each occupying a portion
of the D-bit hypervector, combined for robust similarity:

1. LOG-UNIFORM RANDOM THRESHOLD (D/2 bits):
   - Each bit has a random threshold drawn from log-uniform [1, MAX]
   - bit = 1 if threshold ∈ [lo, hi]
   - Log-uniform gives equal weight across all orders of magnitude
   - range(0,100) vs range(0,99): ~0.999 similar (share ~all thresholds)
   - range(0,100) vs range(1000,50000): ~0.25 (thresholds don't overlap)

2. SCALAR LEVEL ENCODING — center (D/4 bits):
   - Encode log(center) using correlated level hypervectors
   - Adjacent levels share ~93% bits → nearby centers are similar
   - Distinguishes range(0,100) center=50 from range(50,150) center=100

3. SCALAR LEVEL ENCODING — span (D/4 bits):
   - Encode log(hi-lo) using correlated level hypervectors
   - Distinguishes wide ranges from narrow ones

Type discrimination: XOR upper D/2 bits with constraint-type key.
"""

import hashlib
import struct
import random
import time
import os
import json
import math

# ============================================================================
# Constants
# ============================================================================

D = 1024
MAX_VALUE = 65536
NUM_LEVELS = 256          # Levels for scalar encoding
FLIP_RATE = 0.07          # 7% bit flip between adjacent levels → 93% similarity
LN_MAX = math.log(MAX_VALUE)

# ============================================================================
# Pre-computed encoding tables (generated once, deterministic)
# ============================================================================

def _generate_log_thresholds(dim, seed=42):
    """Generate log-uniform random thresholds for interval encoding."""
    rng = random.Random(seed)
    thresholds = []
    for _ in range(dim):
        # Log-uniform: threshold = exp(uniform(0, ln(MAX)))
        t = math.exp(rng.random() * LN_MAX)
        thresholds.append(t)
    return thresholds

def _generate_level_vectors(num_levels, dim, seed=1234):
    """Generate correlated level hypervectors for scalar encoding.
    
    Adjacent levels differ by FLIP_RATE fraction of bits.
    This creates a smooth gradient in Hamming space:
    level[i] vs level[j] similarity ≈ (1-FLIP_RATE)^|i-j|
    """
    rng = random.Random(seed)
    flip_count = max(1, int(dim * FLIP_RATE))
    
    levels = []
    # Start with a random base vector (~50% ones)
    base = [rng.randint(0, 1) for _ in range(dim)]
    levels.append(list(base))
    
    for i in range(1, num_levels):
        prev = levels[-1]
        # Flip FLIP_RATE of bits to get next level
        indices = rng.sample(range(dim), flip_count)
        new_level = list(prev)
        for idx in indices:
            new_level[idx] = 1 - new_level[idx]
        levels.append(new_level)
    
    return levels

# Lazy-initialized globals
_LOG_THRESHOLDS = None
_LEVEL_VECTORS_CENTER = None
_LEVEL_VECTORS_SPAN = None
_TYPE_KEYS = {}

def _get_log_thresholds():
    global _LOG_THRESHOLDS
    if _LOG_THRESHOLD is None:
        _LOG_THRESHOLDS = _generate_log_thresholds(D // 2, seed=42)
    return _LOG_THRESHOLDS

def _get_level_vectors_center():
    global _LEVEL_VECTORS_CENTER
    if _LEVEL_VECTORS_CENTER is None:
        _LEVEL_VECTORS_CENTER = _generate_level_vectors(NUM_LEVELS, D // 4, seed=5678)
    return _LEVEL_VECTORS_CENTER

def _get_level_vectors_span():
    global _LEVEL_VECTORS_SPAN
    if _LEVEL_VECTORS_SPAN is None:
        _LEVEL_VECTORS_SPAN = _generate_level_vectors(NUM_LEVELS, D // 4, seed=9012)
    return _LEVEL_VECTORS_SPAN

def _get_type_key(constraint_type):
    if constraint_type not in _TYPE_KEYS:
        seed = int(hashlib.sha256(f"TYPE:{constraint_type}".encode()).hexdigest(), 16)
        _TYPE_KEYS[constraint_type] = generate_hypervector(seed, D // 2)
    return _TYPE_KEYS[constraint_type]


# ============================================================================
# Hypervector Generation (basic operations)
# ============================================================================

def seed_from_text(text):
    return int(hashlib.sha256(text.encode()).hexdigest(), 16)

def generate_hypervector(seed_val, dim=D):
    rng = random.Random(seed_val)
    return [rng.randint(0, 1) for _ in range(dim)]

def generate_bipolar_hypervector(seed_val, dim=D):
    rng = random.Random(seed_val)
    return [rng.choice([-1, 1]) for _ in range(dim)]

# ============================================================================
# HDC Operations
# ============================================================================

def xor_bind(a, b):
    return [x ^ y for x, y in zip(a, b)]

def majority_bundle(vectors):
    n = len(vectors)
    if n == 0:
        return None
    if n == 1:
        return list(vectors[0])
    result = []
    for i in range(len(vectors[0])):
        count = sum(v[i] for v in vectors)
        result.append(1 if count > n / 2 else 0)
    return result

def bipolar_bundle(vectors):
    dim = len(vectors[0])
    result = [0] * dim
    for v in vectors:
        for i in range(dim):
            result[i] += v[i]
    return [1 if x > 0 else -1 for x in result]

def permute(vector, shift=1):
    return vector[shift:] + vector[:shift]

def hamming_distance(a, b):
    return sum(x ^ y for x, y in zip(a, b))

def hamming_similarity(a, b):
    return 1.0 - hamming_distance(a, b) / len(a)

# ============================================================================
# NEW: Semantic Constraint Encoding (v3)
# ============================================================================

def constraint_to_hypervector(constraint_type, lo=None, hi=None, mask=None):
    """Convert a FLUX constraint to a semantically-aware hypervector.
    
    Architecture (D=1024 bits):
    ┌─────────────────────────────────────────────────────┐
    │ Bits 0..511: Log-uniform threshold occupation       │
    │   Each bit: 1 if random threshold ∈ [lo, hi]        │
    │   Type-key XOR-bound into upper 256 bits             │
    │                                                     │
    │ Bits 512..767: Scalar center encoding                │
    │   Level vector for log((lo+hi)/2)                    │
    │   Captures WHERE the range is                        │
    │                                                     │
    │ Bits 768..1023: Scalar span encoding                 │
    │   Level vector for log(hi-lo+1)                      │
    │   Captures HOW WIDE the range is                     │
    └─────────────────────────────────────────────────────┘
    
    Properties:
    - range(0,100) vs range(0,99): ~0.99+ (nearly identical)
    - range(0,100) vs range(50,150): ~0.55 (partial overlap, different center)
    - range(0,100) vs range(1000,50000): ~0.25 (unrelated)
    - Cross-type: XOR type key prevents collision
    """
    if constraint_type == 'range':
        lo = lo if lo is not None else 0
        hi = hi if hi is not None else MAX_VALUE
        return _encode_range(lo, hi)
    elif constraint_type == 'domain':
        mask = mask if mask is not None else 0
        return _encode_domain(mask)
    elif constraint_type == 'exact':
        val = lo if lo is not None else 0
        return _encode_exact(val)
    else:
        raise ValueError(f"Unknown constraint type: {constraint_type}")


def _encode_range(lo, hi):
    """Encode a range constraint using multi-scale semantic encoding."""
    dim_thresh = D // 2       # 512 bits for threshold occupation
    dim_center = D // 4       # 256 bits for center scalar
    dim_span = D // 4         # 256 bits for span scalar
    
    # --- Part 1: Log-uniform threshold occupation ---
    thresholds = _get_log_thresholds()
    occupation = [0] * dim_thresh
    for i in range(dim_thresh):
        t = thresholds[i]
        if lo <= t <= hi:
            occupation[i] = 1
    
    # XOR type key into the upper quarter of threshold bits
    type_key = _get_type_key('range')
    occupation = occupation[:dim_thresh//2] + xor_bind(occupation[dim_thresh//2:], type_key[:dim_thresh//2])
    
    # --- Part 2: Scalar center encoding ---
    center = (lo + hi) / 2.0
    if center < 1:
        center = 1
    log_center = math.log(center) / LN_MAX  # Normalize to [0, 1]
    center_level = min(NUM_LEVELS - 1, max(0, int(log_center * (NUM_LEVELS - 1))))
    
    center_levels = _get_level_vectors_center()
    center_vec = list(center_levels[center_level])
    
    # --- Part 3: Scalar span encoding ---
    span = hi - lo + 1
    if span < 1:
        span = 1
    log_span = math.log(span) / LN_MAX  # Normalize to [0, 1]
    span_level = min(NUM_LEVELS - 1, max(0, int(log_span * (NUM_LEVELS - 1))))
    
    span_levels = _get_level_vectors_span()
    span_vec = list(span_levels[span_level])
    
    return occupation + center_vec + span_vec


def _encode_domain(mask):
    """Encode a domain/bitmask constraint."""
    # Use hash-based encoding for domain masks (bit patterns don't have
    # the same "overlap" semantics as ranges)
    dim_thresh = D // 2
    dim_center = D // 4
    dim_span = D // 4
    
    # Threshold occupation: use bit population pattern
    thresholds = _get_log_thresholds()
    occupation = [0] * dim_thresh
    for i in range(dim_thresh):
        # Use threshold as a bit position test
        bit_pos = int(thresholds[i]) % 64
        if mask & (1 << bit_pos):
            occupation[i] = 1
    
    # XOR type key
    type_key = _get_type_key('domain')
    occupation = occupation[:dim_thresh//2] + xor_bind(occupation[dim_thresh//2:], type_key[:dim_thresh//2])
    
    # Center: encode number of set bits
    popcount = bin(mask).count('1')
    log_pop = math.log(popcount + 1) / math.log(65)  # max 64 bits
    center_level = min(NUM_LEVELS - 1, max(0, int(log_pop * (NUM_LEVELS - 1))))
    center_levels = _get_level_vectors_center()
    center_vec = list(center_levels[center_level])
    
    # Span: encode the mask value itself
    log_mask = math.log(mask + 1) / LN_MAX
    span_level = min(NUM_LEVELS - 1, max(0, int(log_mask * (NUM_LEVELS - 1))))
    span_levels = _get_level_vectors_span()
    span_vec = list(span_levels[span_level])
    
    return occupation + center_vec + span_vec


def _encode_exact(value):
    """Encode an exact value with its own type key (not range)."""
    dim_thresh = D // 2
    dim_center = D // 4
    dim_span = D // 4
    
    # Threshold occupation: only thresholds very close to value are set
    thresholds = _get_log_thresholds()
    occupation = [0] * dim_thresh
    for i in range(dim_thresh):
        t = thresholds[i]
        if abs(t - value) < 1.0:  # Very narrow window
            occupation[i] = 1
    
    # XOR with EXACT type key (different from range key)
    type_key = _get_type_key('exact')
    occupation = occupation[:dim_thresh//2] + xor_bind(occupation[dim_thresh//2:], type_key[:dim_thresh//2])
    
    # Center: encode the value itself
    if value < 1:
        value = 1
    log_val = math.log(value) / LN_MAX
    center_level = min(NUM_LEVELS - 1, max(0, int(log_val * (NUM_LEVELS - 1))))
    center_levels = _get_level_vectors_center()
    center_vec = list(center_levels[center_level])
    
    # Span: encode as zero-width (level 0)
    span_levels = _get_level_vectors_span()
    span_vec = list(span_levels[0])
    
    return occupation + center_vec + span_vec


# ============================================================================
# Bit-Folding
# ============================================================================

def fold_vector(vector, target_bits=128):
    v = list(vector)
    while len(v) > target_bits:
        half = len(v) // 2
        v = [v[i] ^ v[i + half] for i in range(half)]
    return v

def pack_to_uint64(vector):
    result = []
    for i in range(0, len(vector), 64):
        chunk = vector[i:i+64]
        while len(chunk) < 64:
            chunk.append(0)
        val = 0
        for bit in chunk:
            val = (val << 1) | bit
        result.append(val)
    return result

def unpack_from_uint64(words, total_bits):
    vec = []
    for w in words:
        for i in range(63, -1, -1):
            vec.append((w >> i) & 1)
    return vec[:total_bits]

# ============================================================================
# TUTOR-Inspired Constraint Matcher
# ============================================================================

class TUTORConstraintMatcher:
    """The TUTOR approach with semantic constraint encoding."""
    
    def __init__(self, dimension=1024):
        self.dim = dimension
        self.knowledge_base = {}
        self.constraint_meta = {}
    
    def add_concept(self, name, text):
        seed = seed_from_text(text)
        hv = generate_hypervector(seed, self.dim)
        self.knowledge_base[name] = hv
        return hv
    
    def add_range_constraint(self, name, lo, hi):
        hv = constraint_to_hypervector('range', lo=lo, hi=hi)
        self.knowledge_base[name] = hv
        self.constraint_meta[name] = ('range', {'lo': lo, 'hi': hi})
        return hv
    
    def add_domain_constraint(self, name, mask):
        hv = constraint_to_hypervector('domain', mask=mask)
        self.knowledge_base[name] = hv
        self.constraint_meta[name] = ('domain', {'mask': mask})
        return hv
    
    def add_exact_constraint(self, name, value):
        hv = constraint_to_hypervector('exact', lo=value)
        self.knowledge_base[name] = hv
        self.constraint_meta[name] = ('exact', {'lo': value})
        return hv
    
    def query(self, query_hv, threshold=0.7):
        scores = {}
        for name, stored_hv in self.knowledge_base.items():
            sim = hamming_similarity(query_hv, stored_hv)
            scores[name] = sim
        best = max(scores, key=scores.get) if scores else None
        best_sim = scores.get(best, 0)
        return (best, best_sim, scores) if best_sim >= threshold else (None, best_sim, scores)
    
    def query_range(self, lo, hi, threshold=0.7):
        qhv = constraint_to_hypervector('range', lo=lo, hi=hi)
        return self.query(qhv, threshold)
    
    def bundle_all(self):
        if not self.knowledge_base:
            return None
        return majority_bundle(list(self.knowledge_base.values()))
    
    def export_sram(self, output_path, fold_to=128):
        CACHE_LINE = 64
        records = []
        for name, hv in self.knowledge_base.items():
            fp = seed_from_text(name) & 0xFFFFFFFFFFFFFFFF
            folded = fold_vector(hv, fold_to)
            packed = pack_to_uint64(folded)
            record = struct.pack("<Q", fp)
            for val in packed:
                record += struct.pack("<Q", val)
            padding_needed = CACHE_LINE - (len(record) % CACHE_LINE)
            if padding_needed < CACHE_LINE:
                record += b'\x00' * padding_needed
            records.append((name, record))
        with open(output_path, 'wb') as f:
            for name, record in records:
                f.write(record)
        return len(records)
    
    def to_c_header(self, var_name="flux_hdc_kb"):
        lines = [
            '#ifndef FLUX_HDC_KB_H',
            '#define FLUX_HDC_KB_H',
            '#include <stdint.h>',
            '',
            f'#define HDC_DIM {self.dim}',
            f'#define HDC_NUM_CONCEPTS {len(self.knowledge_base)}',
            '',
            'typedef struct __attribute__((aligned(64))) {',
            '    uint64_t fingerprint;',
            '    uint64_t folded_vector[2];  // 128-bit folded HDC',
            '    uint32_t concept_id;',
            '    uint8_t padding[36];',
            '} HdcRecord;',
            '',
            'static inline float hdc_similarity(const HdcRecord* a, uint64_t query[2]) {',
            '    int matching = 0;',
            '    for (int i = 0; i < 2; i++) {',
            '        matching += __builtin_popcountll(~(a->folded_vector[i] ^ query[i]));',
            '    }',
            '    return (float)matching / 128.0f;',
            '}',
            '',
            f'static const HdcRecord {var_name}[HDC_NUM_CONCEPTS] = {{',
        ]
        for idx, (name, hv) in enumerate(self.knowledge_base.items()):
            fp = seed_from_text(name) & 0xFFFFFFFFFFFFFFFF
            folded = fold_vector(hv, 128)
            packed = pack_to_uint64(folded)
            lines.append(f'    {{0x{fp:016X}ULL, {{0x{packed[0]:016X}ULL, 0x{packed[1]:016X}ULL}}, {idx}}},  // {name}')
        lines.append('};')
        lines.append('')
        lines.append('#endif')
        return '\n'.join(lines)
    
    def export_for_verilog(self, output_path, fold_to=128):
        lines = [
            f"// FLUX HDC Knowledge Base — {len(self.knowledge_base)} concepts",
            f"// Each entry: {fold_to}-bit folded hypervector as {fold_to//64} x 64-bit hex words",
            "",
        ]
        for name, hv in self.knowledge_base.items():
            folded = fold_vector(hv, fold_to)
            packed = pack_to_uint64(folded)
            hex_words = [f"64'h{w:016X}" for w in packed]
            lines.append(f"// {name}")
            for i, hw in enumerate(hex_words):
                lines.append(f"{hw},  // word {i}")
            lines.append("")
        with open(output_path, 'w') as f:
            f.write('\n'.join(lines))


# ============================================================================
# SRAM Baker (for CI/CD)
# ============================================================================

def bake_sram_from_kb(hdc_dir, output_path=None):
    if output_path is None:
        output_path = os.path.join(hdc_dir, 'flux_kb.sram')
    kb_path = os.path.join(hdc_dir, 'flux_kb.json')
    if not os.path.exists(kb_path):
        print(f"No knowledge base at {kb_path}")
        return 0
    with open(kb_path) as f:
        constraints = json.load(f)
    matcher = TUTORConstraintMatcher(D)
    for c in constraints:
        ctype = c['type']
        params = c['params']
        if ctype == 'range':
            matcher.add_range_constraint(c['name'], params['lo'], params['hi'])
        elif ctype == 'domain':
            matcher.add_domain_constraint(c['name'], params.get('mask', 0))
        elif ctype == 'exact':
            matcher.add_exact_constraint(c['name'], params.get('lo', 0))
    n = matcher.export_sram(output_path)
    header_path = os.path.join(hdc_dir, 'flux_kb.h')
    with open(header_path, 'w') as f:
        f.write(matcher.to_c_header())
    vinit_path = os.path.join(hdc_dir, 'flux_kb.vhex')
    matcher.export_for_verilog(vinit_path)
    print(f"Baked {n} concepts → {output_path} ({os.path.getsize(output_path)} bytes)")
    return n


# ============================================================================
# Benchmarks & Validation
# ============================================================================

def validate_semantic_encoding():
    print("=" * 70)
    print("SEMANTIC ENCODING VALIDATION — Multi-Scale (v3)")
    print("=" * 70)
    
    test_cases = [
        (0, 100,   0, 99,     "range(0,100) vs range(0,99) — near-identical"),
        (0, 100,   0, 101,    "range(0,100) vs range(0,101) — near-identical"),
        (0, 100,   50, 150,   "range(0,100) vs range(50,150) — partial overlap"),
        (0, 100,   0, 50,     "range(0,100) vs range(0,50) — contained"),
        (0, 100,   100, 200,  "range(0,100) vs range(100,200) — adjacent"),
        (0, 100,   1000, 50000, "range(0,100) vs range(1000,50000) — unrelated"),
        (0, 100,   0, 100,    "range(0,100) vs range(0,100) — identical"),
        (0, 45000, 0, 44000,  "range(0,45000) vs range(0,44000) — large near-identical"),
        (0, 45000, 1000, 50000, "range(0,45000) vs range(1000,50000) — large overlap"),
    ]
    
    for lo1, hi1, lo2, hi2, desc in test_cases:
        hv1 = constraint_to_hypervector('range', lo=lo1, hi=hi1)
        hv2 = constraint_to_hypervector('range', lo=lo2, hi=hi2)
        sim = hamming_similarity(hv1, hv2)
        
        # Classify
        if sim > 0.90:
            grade = "IDENTICAL"
        elif sim > 0.70:
            grade = "SIMILAR"
        elif sim > 0.55:
            grade = "PARTIAL"
        elif sim > 0.45:
            grade = "UNRELATED"
        else:
            grade = "DISSIMILAR"
        
        print(f"  {sim:.4f} [{grade:>10}] {desc}")
    
    print()
    
    # Cross-type checks
    print("--- Cross-Type Discrimination ---")
    hv_range = constraint_to_hypervector('range', lo=0, hi=100)
    hv_domain = constraint_to_hypervector('domain', mask=100)
    hv_exact = constraint_to_hypervector('exact', lo=50)
    
    sim_rd = hamming_similarity(hv_range, hv_domain)
    sim_re = hamming_similarity(hv_range, hv_exact)
    sim_de = hamming_similarity(hv_domain, hv_exact)
    
    print(f"  range(0,100) vs domain(100):  {sim_rd:.4f} (should be ~0.5)")
    print(f"  range(0,100) vs exact(50):    {sim_re:.4f} (should be ~0.5)")
    print(f"  domain(100) vs exact(50):     {sim_de:.4f} (should be ~0.5)")


def benchmark():
    print("=" * 70)
    print("FLUX HDC Constraint Matching — v3 (Multi-Scale Semantic)")
    print("=" * 70)
    print()
    
    validate_semantic_encoding()
    
    # ---- Build knowledge base ----
    print("\n" + "=" * 70)
    print("KNOWLEDGE BASE BUILD & QUERY")
    print("=" * 70)
    
    matcher = TUTORConstraintMatcher(D)
    kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flux_kb.json')
    
    if os.path.exists(kb_path):
        with open(kb_path) as f:
            constraints = json.load(f)
        for c in constraints:
            ctype = c['type']
            params = c['params']
            if ctype == 'range':
                matcher.add_range_constraint(c['name'], params['lo'], params['hi'])
            elif ctype == 'domain':
                matcher.add_domain_constraint(c['name'], params.get('mask', 0))
    else:
        matcher.add_range_constraint("temp_safe", 0, 100)
        matcher.add_range_constraint("temp_warning", 101, 150)
        matcher.add_range_constraint("temp_critical", 151, 300)
        matcher.add_range_constraint("altitude_ok", 0, 45000)
        matcher.add_range_constraint("speed_ok", 60, 350)
        matcher.add_range_constraint("fuel_ok", 100, 2000)
        matcher.add_range_constraint("battery_ok", 22, 29)
        matcher.add_domain_constraint("domain_6bit", 63)
        matcher.add_domain_constraint("domain_8bit", 255)
    
    print("\n--- Range Query Tests ---")
    queries = [
        (0, 99,     "Near temp (0-100)"),
        (0, 101,    "Near temp (0-100)"),
        (50, 150,   "Overlaps temp+warning"),
        (1000, 50000, "Near altitude"),
        (55, 340,   "Near speed (60-350)"),
        (20, 30,    "Near battery (22-29)"),
    ]
    
    for lo, hi, desc in queries:
        best, sim, scores = matcher.query_range(lo, hi, threshold=0.55)
        top3 = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        top3_str = ", ".join(f"{n}={s:.4f}" for n, s in top3)
        match_str = f"{best} ({sim:.4f})" if best else "none"
        print(f"  query({lo:>5},{hi:>5}) → {match_str}  [{desc}]")
        print(f"     top3: {top3_str}")
    
    # ---- Performance ----
    print("\n" + "=" * 70)
    print("PERFORMANCE BENCHMARKS")
    print("=" * 70)
    
    a = constraint_to_hypervector('range', lo=0, hi=100)
    b = constraint_to_hypervector('range', lo=0, hi=99)
    c = constraint_to_hypervector('range', lo=1000, hi=50000)
    
    print(f"\n  range(0,100) vs range(0,99):      {hamming_similarity(a, b):.4f}")
    print(f"  range(0,100) vs range(1000,50000): {hamming_similarity(a, c):.4f}")
    
    t0 = time.perf_counter()
    for _ in range(10000):
        hamming_distance(a, b)
    t1 = time.perf_counter()
    print(f"\n  10k Hamming distances: {(t1-t0)*1000:.1f}ms ({(t1-t0)*1e6/10000:.1f}μs each)")
    
    t0 = time.perf_counter()
    for i in range(1000):
        constraint_to_hypervector('range', lo=i, hi=i+100)
    t1 = time.perf_counter()
    print(f"  1k encodings: {(t1-t0)*1000:.1f}ms ({(t1-t0)*1e6/1000:.1f}μs each)")
    
    # Bit-folding
    print(f"\n--- Bit-Folding ({D} → 128) ---")
    fa = fold_vector(a, 128)
    fb = fold_vector(b, 128)
    fc = fold_vector(c, 128)
    fold_rel = 1.0 - sum(x ^ y for x, y in zip(fa, fb)) / 128
    fold_unrel = 1.0 - sum(x ^ y for x, y in zip(fa, fc)) / 128
    print(f"  Folded related:   {fold_rel:.4f}")
    print(f"  Folded unrelated: {fold_unrel:.4f}")
    
    # Export
    hdc_dir = os.path.dirname(os.path.abspath(__file__))
    sram_path = os.path.join(hdc_dir, 'flux_kb.sram')
    n = matcher.export_sram(sram_path)
    print(f"\n  SRAM: {n} records → {sram_path}")
    
    header_path = os.path.join(hdc_dir, 'flux_kb.h')
    with open(header_path, 'w') as f:
        f.write(matcher.to_c_header())
    
    vhex_path = os.path.join(hdc_dir, 'flux_kb.vhex')
    matcher.export_for_verilog(vhex_path)
    
    print(f"  Header: {header_path}")
    print(f"  Verilog: {vhex_path}")


# Fix the typo in the getter
_LOG_THRESHOLD = None

def _get_log_thresholds():
    global _LOG_THRESHOLD
    if _LOG_THRESHOLD is None:
        _LOG_THRESHOLD = _generate_log_thresholds(D // 2, seed=42)
    return _LOG_THRESHOLD


if __name__ == '__main__':
    benchmark()
