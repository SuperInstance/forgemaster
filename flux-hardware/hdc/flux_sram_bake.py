#!/usr/bin/env python3
"""
flux_sram_bake.py — The "Metal Bake" Pipeline

Converts repository knowledge into a cache-aligned SRAM image
that agents can memory-map for instant constraint checking.

The pipeline:
  1. SCAN: Walk repo files, extract constraint definitions
  2. HASH: Generate 1024-bit hypervectors with semantic features
  3. BUNDLE: Create holographic superposition for instant query
  4. FOLD: Compress to 128-bit for edge deployment
  5. ALIGN: 64-byte cache line alignment
  6. EXPORT: SRAM binary image + C header

The "Copper" analogy:
  SCAN  = WAIT (prepare for data)
  HASH  = MOVE (write the register)
  FOLD  = The compression trick
  ALIGN = Cache line = scanline timing
  EXPORT = The copper list is ready
"""

import os
import sys
import struct
import hashlib
import json
import time

CACHE_LINE = 64

# ============================================================================
# Semantic Feature Hashing
# ============================================================================

def extract_features(text):
    """Extract semantic features from constraint text.
    
    Features are Boolean properties:
    - is_range: constraint involves range checking
    - is_domain: constraint involves domain/mask checking
    - is_low_zero: lower bound is 0 (strength reduction applies)
    - is_8bit: values fit in 8 bits
    - is_16bit: values fit in 16 bits
    - is_32bit: values need 32 bits
    - is_safety: constraint is safety-critical
    - is_performance: constraint is performance-related
    
    These features create the "Semantic Bit-Mask" from the conversation.
    """
    features = {}
    text_lower = text.lower()
    
    # Type features
    features['is_range'] = ' in [' in text_lower or 'range' in text_lower
    features['is_domain'] = 'domain' in text_lower or 'mask' in text_lower
    features['is_exact'] = 'exact' in text_lower or 'equals' in text_lower
    
    # Numeric features
    import re
    numbers = [int(x) for x in re.findall(r'\d+', text)]
    if numbers:
        features['is_low_zero'] = min(numbers) == 0
        features['is_8bit'] = max(numbers) < 256
        features['is_16bit'] = max(numbers) < 65536
        features['is_32bit'] = max(numbers) >= 65536
        features['magnitude_small'] = max(numbers) < 100
        features['magnitude_medium'] = 100 <= max(numbers) < 10000
        features['magnitude_large'] = max(numbers) >= 10000
    else:
        features['is_low_zero'] = False
        features['is_8bit'] = True
        features['is_16bit'] = False
        features['is_32bit'] = False
        features['magnitude_small'] = True
        features['magnitude_medium'] = False
        features['magnitude_large'] = False
    
    # Semantic features
    safety_words = ['safe', 'critical', 'danger', 'limit', 'threshold', 'emergency']
    perf_words = ['speed', 'fast', 'throughput', 'latency', 'bandwidth']
    features['is_safety'] = any(w in text_lower for w in safety_words)
    features['is_performance'] = any(w in text_lower for w in perf_words)
    
    return features


def features_to_hypervector(features, dim=1024):
    """Convert feature dict to 1024-bit hypervector.
    
    Each feature maps to a deterministic region of the hypervector.
    Similar features → similar regions → high similarity.
    This is how "range:0:99" matches "range:0:100":
    they share is_range=True, is_low_zero=True, is_8bit=True, etc.
    """
    import random
    vector = [0] * dim
    feature_names = sorted(features.keys())
    
    for fname in feature_names:
        if features[fname]:
            # Each feature has its own deterministic sub-vector
            seed = int(hashlib.sha256(f"feature:{fname}".encode()).hexdigest(), 16)
            rng = random.Random(seed)
            # Set a region of bits (bundle this feature's pattern)
            for i in range(dim):
                if rng.random() < 0.6:  # 60% density per feature
                    vector[i] = (vector[i] + 1) % 2  # XOR-style bundling
    
    return vector


# ============================================================================
# SRAM Record Format
# ============================================================================

def make_sram_record(concept_id, name, features, hypervector, description=""):
    """Build a 64-byte cache-aligned SRAM record.
    
    Layout:
      [0:8]   fingerprint (uint64) — fast identity check
      [8:24]  folded_vector (uint64×2) — 128-bit folded HDC
      [24:28] concept_id (uint32)
      [28:32] feature_mask (uint32) — feature bits packed
      [32:36] flags (uint32) — type flags
      [36:64] padding — cache line alignment
    """
    # Fingerprint
    fp = int(hashlib.sha256(name.encode()).hexdigest()[:16], 16)
    
    # Fold hypervector to 128 bits
    folded = hypervector[:]
    while len(folded) > 128:
        half = len(folded) // 2
        folded = [folded[i] ^ folded[i + half] for i in range(half)]
    
    # Pack folded vector into 2 × uint64
    packed = []
    for i in range(0, 128, 64):
        chunk = folded[i:i+64]
        val = 0
        for bit in chunk:
            val = (val << 1) | bit
        packed.append(val)
    
    # Feature mask (pack boolean features into bits)
    feature_mask = 0
    feature_names = sorted(features.keys())
    for idx, fname in enumerate(feature_names):
        if features[fname] and idx < 32:
            feature_mask |= (1 << idx)
    
    # Type flags
    flags = 0
    if features.get('is_range'): flags |= 1
    if features.get('is_domain'): flags |= 2
    if features.get('is_exact'): flags |= 4
    if features.get('is_safety'): flags |= 8
    if features.get('is_low_zero'): flags |= 16
    
    # Build record
    record = struct.pack("<Q", fp)                    # fingerprint
    record += struct.pack("<Q", packed[0])            # folded_vector[0]
    record += struct.pack("<Q", packed[1])            # folded_vector[1]
    record += struct.pack("<I", concept_id)           # concept_id
    record += struct.pack("<I", feature_mask)         # feature_mask
    record += struct.pack("<I", flags)                # flags
    # Pad to 64 bytes
    padding_needed = CACHE_LINE - len(record)
    if padding_needed > 0:
        record += b'\x00' * padding_needed
    
    assert len(record) == CACHE_LINE, f"Record is {len(record)} bytes, expected {CACHE_LINE}"
    
    return record


# ============================================================================
# Scan & Bake Pipeline
# ============================================================================

def scan_guard_files(directory):
    """Walk directory and find all .guard files."""
    guard_files = []
    for root, dirs, files in os.walk(directory):
        for f in files:
            if f.endswith('.guard'):
                guard_files.append(os.path.join(root, f))
    return guard_files


def parse_guard_file(filepath):
    """Parse a GUARD file into constraint definitions."""
    constraints = []
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('constraint '):
                line = line[len('constraint '):]
            if ' in [' in line:
                # Extract name and range
                parts = line.split(' in [')
                name = parts[0].strip()
                bounds = parts[1].rstrip(']').split(',')
                lo = int(bounds[0].strip())
                hi = int(bounds[1].strip())
                constraints.append({
                    'type': 'range',
                    'name': name,
                    'params': {'lo': lo, 'hi': hi},
                    'text': line,
                })
            elif ' in domain ' in line:
                parts = line.split(' in domain ')
                name = parts[0].strip()
                mask = int(parts[1].strip(), 16)
                constraints.append({
                    'type': 'domain',
                    'name': name,
                    'params': {'mask': mask},
                    'text': line,
                })
    return constraints


def bake_sram(constraints, output_path):
    """The full bake pipeline: constraints → SRAM image."""
    records = []
    metadata = []
    
    for idx, c in enumerate(constraints):
        # Extract features
        features = extract_features(c['text'])
        
        # Generate hypervector from features (semantic, not text-based)
        hv = features_to_hypervector(features)
        
        # Build SRAM record
        record = make_sram_record(idx, c['name'], features, hv, c['text'])
        records.append(record)
        
        # Metadata for the index
        metadata.append({
            'id': idx,
            'name': c['name'],
            'type': c['type'],
            'params': c['params'],
            'features': features,
        })
    
    # Write SRAM image
    with open(output_path, 'wb') as f:
        # Header: magic + version + count
        f.write(struct.pack("<4sII", b'FLUX', 1, len(records)))
        for record in records:
            f.write(record)
    
    # Write metadata JSON
    meta_path = output_path.replace('.sram', '.json')
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    return len(records)


def bake_c_header(constraints, output_path, var_name="flux_kb"):
    """Generate C header from constraints."""
    lines = [
        '/* FLUX Constraint Knowledge Base — Auto-generated by flux_sram_bake */',
        '/* Cache-line aligned for zero-copy memory-mapped access */',
        '',
        '#ifndef FLUX_KB_H',
        '#define FLUX_KB_H',
        '#include <stdint.h>',
        '',
        f'#define FLUX_KB_COUNT {len(constraints)}',
        '',
        'typedef struct __attribute__((aligned(64))) {',
        '    uint64_t fingerprint;',
        '    uint64_t folded_hdc[2];',
        '    uint32_t concept_id;',
        '    uint32_t feature_mask;',
        '    uint32_t flags;',
        '    uint8_t padding[28];',
        '} FluxKBRecord;',
        '',
        'static inline float flux_kb_similarity(const FluxKBRecord* r, uint64_t q[2]) {',
        '    int match = 0;',
        '    match += __builtin_popcountll(~(r->folded_hdc[0] ^ q[0]));',
        '    match += __builtin_popcountll(~(r->folded_hdc[1] ^ q[1]));',
        '    return (float)match / 128.0f;',
        '}',
        '',
        'static inline const FluxKBRecord* flux_kb_query(const FluxKBRecord* kb,',
        '    int n, uint64_t query[2], float threshold) {',
        '    float best_sim = 0;',
        '    const FluxKBRecord* best = 0;',
        '    for (int i = 0; i < n; i++) {',
        '        float sim = flux_kb_similarity(&kb[i], query);',
        '        if (sim > best_sim) { best_sim = sim; best = &kb[i]; }',
        '    }',
        '    return (best_sim >= threshold) ? best : 0;',
        '}',
        '',
        f'static const FluxKBRecord {var_name}[FLUX_KB_COUNT] = {{',
    ]
    
    for idx, c in enumerate(constraints):
        features = extract_features(c['text'])
        hv = features_to_hypervector(features)
        record = make_sram_record(idx, c['name'], features, hv)
        # Parse the record
        fp = struct.unpack("<Q", record[0:8])[0]
        fh0 = struct.unpack("<Q", record[8:16])[0]
        fh1 = struct.unpack("<Q", record[16:24])[0]
        cid = struct.unpack("<I", record[24:28])[0]
        fm = struct.unpack("<I", record[28:32])[0]
        fl = struct.unpack("<I", record[32:36])[0]
        lines.append(f'    {{0x{fp:016X}ULL, {{0x{fh0:016X}ULL, 0x{fh1:016X}ULL}}, {cid}, 0x{fm:08X}, 0x{fl:08X}}},  /* {c["name"]} */')
    
    lines.append('};')
    lines.append('#endif')
    
    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))


# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    # Bake from the guard files we created earlier
    constraints = []
    for gf in ['/tmp/temp_guard.guard', '/tmp/flight_guard.guard']:
        if os.path.exists(gf):
            constraints.extend(parse_guard_file(gf))
    
    if not constraints:
        print("No .guard files found. Creating example constraints...")
        constraints = [
            {'type': 'range', 'name': 'temp', 'params': {'lo': 0, 'hi': 100}, 'text': 'temp in [0, 100]'},
            {'type': 'range', 'name': 'altitude', 'params': {'lo': 0, 'hi': 45000}, 'text': 'altitude in [0, 45000]'},
            {'type': 'range', 'name': 'speed', 'params': {'lo': 60, 'hi': 350}, 'text': 'speed in [60, 350]'},
            {'type': 'domain', 'name': 'flags', 'params': {'mask': 0x3F}, 'text': 'flags in domain 0x3F'},
        ]
    
    print(f"Baking {len(constraints)} constraints...")
    
    # Bake SRAM
    n = bake_sram(constraints, '/tmp/flux_kb.sram')
    print(f"  SRAM: {n} records → /tmp/flux_kb.sram")
    
    # Bake C header
    bake_c_header(constraints, '/tmp/flux_kb.h')
    print(f"  C header → /tmp/flux_kb.h")
    
    # Test semantic matching
    print("\n--- Semantic Matching Test ---")
    for c in constraints[:4]:
        features = extract_features(c['text'])
        hv = features_to_hypervector(features)
        print(f"  {c['name']:15s}: features = {', '.join(k for k,v in features.items() if v)}")
    
    # Test that similar constraints match
    print("\n--- Cross-Constraint Similarity ---")
    hvs = []
    for c in constraints:
        features = extract_features(c['text'])
        hvs.append((c['name'], features_to_hypervector(features)))
    
    # Compare each pair
    for i in range(min(4, len(hvs))):
        for j in range(i+1, min(6, len(hvs))):
            sim = sum(1 for a,b in zip(hvs[i][1], hvs[j][1]) if a==b) / len(hvs[i][1])
            print(f"  {hvs[i][0]:15s} ↔ {hvs[j][0]:15s}: {sim:.4f}")
    
    print("\nDone. SRAM image ready for mmap() deployment.")
