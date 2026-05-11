#!/usr/bin/env python3
"""
inspect_ptx.py — Parse and analyze .ptx files for SnapKit CUDA kernels.

Extracts:
- Instruction types used
- Register counts per kernel
- Memory access patterns
- Rounding modes (cvt.rni vs others)
- fma usage
- Compute capabilities targeted
"""

import re
import os
import sys

# ======================================================================
# PTX Instruction Taxonomy
# ======================================================================

INSTRUCTION_CATEGORIES = {
    'arithmetic': {
        'patterns': [
            r'\badd\.', r'\bsub\.', r'\bmul\.', r'\bdiv\.',
            r'\bfma\.', r'\bmad\.', r'\bneg\.', r'\babs\.',
        ],
        'label': 'Arithmetic'
    },
    'rounding': {
        'patterns': [
            r'\bcvt\.rni\.', r'\bcvt\.rn\.', r'\bcvt\.ru\.', r'\bcvt\.rd\.',
            r'\bcvt\.rz\.', r'\bround\.',
        ],
        'label': 'Rounding/Conversion'
    },
    'comparison': {
        'patterns': [
            r'\bsetp\.', r'\bset\.', r'\bselp\.',
        ],
        'label': 'Comparison/Select'
    },
    'memory_load': {
        'patterns': [
            r'\bld\.', r'\bload\.',
        ],
        'label': 'Memory Load'
    },
    'memory_store': {
        'patterns': [
            r'\bst\.', r'\bstore\.',
        ],
        'label': 'Memory Store'
    },
    'control_flow': {
        'patterns': [
            r'\bret\b', r'\bbra\b', r'\bcall\b', r'\bjmp\b',
            r'\bexit\b', r'\bbar\b',
        ],
        'label': 'Control Flow'
    },
    'synchronization': {
        'patterns': [
            r'\bbar\.sync\b', r'\bmembar\b', r'\bfence\b',
        ],
        'label': 'Sync/Fence'
    },
    'warp_intrinsic': {
        'patterns': [
            r'\bshfl\b', r'\bvote\b', r'\bmatch\b',
        ],
        'label': 'Warp Intrinsic'
    },
    'special_function': {
        'patterns': [
            r'\bsqrt\.', r'\brsqrt\.', r'\bsin\b', r'\bcos\b',
            r'\blg2\b', r'\bex2\b', r'\bpow\b',
        ],
        'label': 'Special Function'
    },
    'conversion': {
        'patterns': [
            r'\bcvt\b(?!\.(rni|rn|ru|rd|rz))',
        ],
        'label': 'Other Conversion'
    },
    'data_movement': {
        'patterns': [
            r'\bmov\.', r'\bsel\.',
        ],
        'label': 'Data Movement'
    },
    'atomic': {
        'patterns': [
            r'\batom\.', r'\bred\.',
        ],
        'label': 'Atomic'
    },
}

CATEGORY_ORDER = [
    'arithmetic', 'rounding', 'special_function', 'comparison',
    'memory_load', 'memory_store', 'atomic',
    'synchronization', 'warp_intrinsic', 'control_flow',
    'data_movement', 'conversion',
]

# ======================================================================
# PTX Parser
# ======================================================================

def parse_ptx_file(filepath):
    """Parse a .ptx file and extract kernel information."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    info = {
        'filepath': filepath,
        'filename': os.path.basename(filepath),
        'version': None,
        'target': None,
        'address_size': None,
        'kernels': [],
        'constants': [],
        'metadata': [],
    }
    
    # Parse header
    version_match = re.search(r'\.version\s+([\d.]+)', content)
    if version_match:
        info['version'] = version_match.group(1)
    
    target_match = re.search(r'\.target\s+(\S+)', content)
    if target_match:
        info['target'] = target_match.group(1)
    
    addr_match = re.search(r'\.address_size\s+(\d+)', content)
    if addr_match:
        info['address_size'] = int(addr_match.group(1))
    
    # Parse each kernel entry
    kernel_pattern = re.compile(
        r'\.visible\s+\.entry\s+(\w+)\s*\((.*?)\)\s*\{(.*?)\}',
        re.DOTALL
    )
    
    for match in kernel_pattern.finditer(content):
        kernel_name = match.group(1)
        kernel_params = match.group(2).strip()
        kernel_body = match.group(3)
        
        kernel_info = analyze_kernel(kernel_name, kernel_params, kernel_body)
        info['kernels'].append(kernel_info)
    
    # Parse named constants
    const_matches = re.finditer(
        r'\.reg\s+\.f32\s+(\w+)\s*=\s*(0x[0-9a-fA-F]+)f?',
        content
    )
    for match in const_matches:
        name = match.group(1)
        hex_val = match.group(2)
        import struct
        try:
            float_val = struct.unpack('>f', bytes.fromhex(hex_val[2:].zfill(8)))[0]
        except:
            float_val = None
        info['constants'].append({'name': name, 'hex': hex_val, 'float': float_val})
    
    return info


def classify_instructions(body):
    """Classify all instructions in a kernel body."""
    categories = {}
    for cat_id, cat_info in CATEGORY_CATEGORIES.items():
        categories[cat_id] = set()
    
    lines = body.split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('/*'):
            continue
        
        # Remove inline comments
        line_clean = re.sub(r'//.*', '', line).strip()
        
        for cat_id, cat_info in CATEGORY_CATEGORIES.items():
            for pattern in cat_info['patterns']:
                if re.search(pattern, line_clean):
                    # Extract the instruction mnemonic
                    inst_match = re.match(r'(@\w+\s+)?(\w+)', line_clean)
                    if inst_match:
                        mnemonic = inst_match.group(2)
                        categories[cat_id].add(mnemonic)
    
    return categories


# Fix the reference
CATEGORY_CATEGORIES = INSTRUCTION_CATEGORIES


def count_instructions(body):
    """Count non-comment, non-directive PTX instructions."""
    count = 0
    for line in body.split('\n'):
        line = line.strip()
        if not line or line.startswith('//') or line.startswith('/*') or line.endswith('*/'):
            continue
        # Skip PTX directives starting with .
        if line.startswith('.'):
            continue
        # Count lines with PTX instructions
        if re.match(r'(\@[\w.p]+\s+)?[a-z]', line):
            count += 1
    return count


def count_register_usage(body):
    """Estimate register usage from .reg declarations."""
    reg_usage = {
        'f32': 0,
        'f64': 0,
        'u32': 0,
        'u64': 0,
        's32': 0,
        's64': 0,
        'pred': 0,
        'b32': 0,
        'b64': 0,
    }
    
    for line in body.split('\n'):
        line = line.strip()
        reg_match = re.match(r'\.reg\.(\w+)\s+(.+?)(?:;|$)', line)
        if reg_match:
            reg_type = reg_match.group(1)
            reg_list = reg_match.group(2)
            # Count named registers (not inline)
            named_regs = re.findall(r'\b([a-zA-Z_]\w*)\b', reg_list)
            count = len(named_regs)
            
            if reg_type in reg_usage:
                reg_usage[reg_type] += count
    
    # Estimate physical register count (approximate)
    phys_regs = sum(reg_usage.values())
    return reg_usage, phys_regs


def analyze_memory_patterns(body):
    """Analyze memory load/store patterns."""
    patterns = {
        'global_coalesced': 0,
        'global_random': 0,
        'shared': 0,
        'constant': 0,
        'texture': 0,
        'local': 0,
        'caching': {'ca': 0, 'cg': 0, 'cs': 0, 'cv': 0},
    }
    
    for line in body.split('\n'):
        line = line.strip()
        
        # Coalesced L1 cache
        if re.search(r'ld\.global\.ca', line):
            patterns['global_coalesced'] += 1
            patterns['caching']['ca'] += 1
        elif re.search(r'ld\.global\.cs', line):
            patterns['global_coalesced'] += 1
            patterns['caching']['cs'] += 1
        elif re.search(r'ld\.global\.cg', line):
            patterns['global_random'] += 1
            patterns['caching']['cg'] += 1
        elif re.search(r'ld\.global\.cv', line):
            patterns['global_random'] += 1
            patterns['caching']['cv'] += 1
        elif re.search(r'ld\.shared', line):
            patterns['shared'] += 1
        elif re.search(r'ld\.const', line):
            patterns['constant'] += 1
        elif re.search(r'ld\.param', line):
            patterns['constant'] += 1
        elif re.search(r'st\.global\.cs', line):
            patterns['global_coalesced'] += 1
        elif re.search(r'st\.global', line):
            patterns['global_coalesced'] += 1
        elif re.search(r'st\.shared', line):
            patterns['shared'] += 1
    
    return patterns


def analyze_rounding_modes(body):
    """Analyze cvt instruction rounding modes."""
    rounding = {
        'rni': 0,   # round-to-nearest-even (banker's)
        'rn': 0,    # round-to-nearest
        'ru': 0,    # round-up (ceil)
        'rd': 0,    # round-down (floor)
        'rz': 0,    # round-toward-zero (truncate)
        'other': 0,
    }
    
    for line in body.split('\n'):
        for mode in ['rni', 'rn', 'ru', 'rd', 'rz']:
            if re.search(r'cvt\.' + mode, line):
                rounding[mode] += 1
    
    return rounding


def analyze_fma_usage(body):
    """Analyze FMA instruction usage."""
    fma_count = 0
    fma_sp = 0
    fma_dp = 0
    
    for line in body.split('\n'):
        if re.search(r'\bfma\.', line):
            fma_count += 1
        if re.search(r'\bfma\.rn\.f32\b', line) or re.search(r'\bfma\.rn\.f32x2\b', line):
            fma_sp += 1
        if re.search(r'\bfma\.rn\.f64\b', line):
            fma_dp += 1
    
    return {
        'total_fma': fma_count,
        'single_precision': fma_sp,
        'double_precision': fma_dp,
    }


def analyze_kernel(name, params, body):
    """Full analysis of a single PTX kernel entry."""
    inst_categories = classify_instructions(body)
    inst_count_total = count_instructions(body)
    reg_types, reg_count = count_register_usage(body)
    mem_patterns = analyze_memory_patterns(body)
    rounding = analyze_rounding_modes(body)
    fma = analyze_fma_usage(body)
    
    # Count loads/stores
    loads_total = (mem_patterns['global_coalesced'] + mem_patterns['global_random'] + 
                    mem_patterns['shared'] + mem_patterns['constant'])
    stores_total = mem_patterns['global_coalesced'] + mem_patterns['shared']
    
    # Generate category summary
    category_counts = {}
    for cat_id in CATEGORY_ORDER:
        cat_info = CATEGORY_CATEGORIES[cat_id]
        instrs = inst_categories.get(cat_id, set())
        if instrs:
            category_counts[cat_id] = len(instrs)
    
    return {
        'name': name,
        'params': params,
        'instruction_count': inst_count_total,
        'register_estimate': reg_count,
        'registers': reg_types,
        'memory_patterns': mem_patterns,
        'loads_total': loads_total,
        'stores_total': stores_total,
        'rounding_modes': rounding,
        'fma': fma,
        'category_counts': category_counts,
    }


# ======================================================================
# Reporting
# ======================================================================

def generate_report(ptx_files):
    """Generate comprehensive PTX quality report."""
    report_lines = [
        "╔══════════════════════════════════════════════════════════════════╗",
        "║         SnapKit CUDA — PTX Instruction Analysis Report          ║",
        "╚══════════════════════════════════════════════════════════════════╝",
        "",
    ]
    
    for ptx_info in ptx_files:
        report_lines.append(f"## File: {ptx_info['filename']}")
        report_lines.append("")
        report_lines.append(f"  PTX Version:     {ptx_info['version']}")
        report_lines.append(f"  Target Arch:     {ptx_info['target']}")
        report_lines.append(f"  Address Size:    {ptx_info['address_size']}-bit")
        report_lines.append(f"  Kernels Found:   {len(ptx_info['kernels'])}")
        report_lines.append("")
        
        if ptx_info['constants']:
            report_lines.append("  Named Constants:")
            for c in ptx_info['constants']:
                val_str = f"{c['float']:.6f}" if c['float'] else '?'
                report_lines.append(f"    {c['name']:20s} = {c['hex']:12s}  ({val_str})")
            report_lines.append("")
        
        for i, kernel in enumerate(ptx_info['kernels']):
            report_lines.append(f"  --- Kernel {i+1}: {kernel['name']} ---")
            report_lines.append("")
            report_lines.append(f"    Parameters:   {kernel['params'][:60]}...")
            report_lines.append(f"    Instruction Count: {kernel['instruction_count']}")
            report_lines.append(f"    Est. Registers:    {kernel['register_estimate']}")
            report_lines.append("")
            
            # Instruction category breakdown
            report_lines.append("    Instruction Categories:")
            for cat_id in CATEGORY_ORDER:
                cat_info = CATEGORY_CATEGORIES[cat_id]
                count = kernel['category_counts'].get(cat_id, 0)
                if count > 0:
                    bar = '█' * count
                    report_lines.append(f"      {cat_info['label']:20s} [{count:3d}] {bar}")
            report_lines.append("")
            
            # Memory access pattern
            mp = kernel['memory_patterns']
            total_ldst = max(mp['global_coalesced'] + mp['global_random'] + mp['shared'], 1)
            coalesced_pct = mp['global_coalesced'] / total_ldst * 100 if total_ldst > 0 else 0
            report_lines.append("    Memory Access Patterns:")
            report_lines.append(f"      Global (coalesced):  {mp['global_coalesced']}")
            report_lines.append(f"      Global (random):     {mp['global_random']}")
            report_lines.append(f"      Shared:              {mp['shared']}")
            report_lines.append(f"      Constant:            {mp['constant']}")
            report_lines.append(f"      Coalesced ratio:     {coalesced_pct:.0f}%")
            if mp['caching']['ca'] > 0:
                report_lines.append(f"      L1 cache reads (ca): {mp['caching']['ca']}")
            if mp['caching']['cs'] > 0:
                report_lines.append(f"      Streaming stores:  {mp['caching']['cs']}")
            report_lines.append("")
            
            # Rounding modes
            rm = kernel['rounding_modes']
            report_lines.append("    Rounding/Conversion Modes:")
            for mode, count in rm.items():
                if count > 0:
                    desc = {
                        'rni': 'Round Nearest Even (banker\'s rounding)',
                        'rn': 'Round Nearest',
                        'ru': 'Round Up (ceil)',
                        'rd': 'Round Down (floor)',
                        'rz': 'Round Toward Zero (truncate)',
                    }.get(mode, mode)
                    report_lines.append(f"      cvt.{mode:3s} {count:3d} — {desc}")
            report_lines.append("")
            
            # FMA analysis
            fma = kernel['fma']
            report_lines.append("    FMA Usage:")
            report_lines.append(f"      Total FMA:          {fma['total_fma']}")
            if fma['single_precision'] > 0:
                report_lines.append(f"      Single Precision:   {fma['single_precision']}")
            if fma['double_precision'] > 0:
                report_lines.append(f"      Double Precision:   {fma['double_precision']}")
            report_lines.append("")
            
            # Quality assessment
            issues = []
            if kernel['register_estimate'] > 32:
                issues.append(f"⚠ High register usage ({kernel['register_estimate']} regs) may limit occupancy")
            if coalesced_pct < 80:
                issues.append(f"⚠ Memory access is not fully coalesced ({coalesced_pct:.0f}%)")
            if kernel['rounding_modes'].get('rni', 0) == 0 and kernel['rounding_modes'].get('rn', 0) == 0:
                issues.append("ℹ No rounding instructions found (may use hardware intrinsics)")
            if kernel['fma']['total_fma'] > 0:
                report_lines.append(f"    ✓ Uses FMA for precision-critical operations")
            if kernel['memory_patterns']['caching']['ca'] > 0:
                report_lines.append(f"    ✓ Uses L1-cached loads for read performance")
            if kernel['memory_patterns']['caching']['cs'] > 0:
                report_lines.append(f"    ✓ Uses streaming stores to reduce L1 pollution")
            
            if issues:
                report_lines.append("")
                for issue in issues:
                    report_lines.append(f"    {issue}")
            else:
                report_lines.append("    ✓ No significant issues detected")
            
            report_lines.append("")
    
    # Cross-file comparison
    report_lines.append("")  
    report_lines.append("## Cross-File Comparison")
    report_lines.append("")
    
    for ptx_info in ptx_files:
        for kernel in ptx_info['kernels']:
            name = f"{ptx_info['filename']}:{kernel['name']}"
            report_lines.append(
                f"  {name:60s}  |  "
                f"Inst: {kernel['instruction_count']:4d}  |  "
                f"Regs: {kernel['register_estimate']:2d}  |  "
                f"FMA: {kernel['fma']['total_fma']:3d}  |  "
                f"rni: {kernel['rounding_modes']['rni']:2d}"
            )
    report_lines.append("")
    
    report_lines.append("## Summary")
    report_lines.append("")
    
    # Aggregate statistics
    total_inst = sum(k['instruction_count'] for p in ptx_files for k in p['kernels'])
    total_fma = sum(k['fma']['total_fma'] for p in ptx_files for k in p['kernels'])
    total_rni = sum(k['rounding_modes']['rni'] for p in ptx_files for k in p['kernels'])
    
    report_lines.append(f"  Total instructions across all kernels: {total_inst}")
    report_lines.append(f"  Total FMA instructions:                {total_fma}")
    report_lines.append(f"  Total cvt.rni rounding instructions:   {total_rni}")
    report_lines.append("")
    
    # Quality checks
    all_checks_passed = True
    for ptx_info in ptx_files:
        for kernel in ptx_info['kernels']:
            if kernel['register_estimate'] > 64:
                report_lines.append(f"  ✗ {kernel['name']}: Register pressure HIGH ({kernel['register_estimate']} regs)")
                all_checks_passed = False
            if kernel['fma']['total_fma'] == 0:
                report_lines.append(f"  ⚠ {kernel['name']}: No FMA instructions (possible precision loss)")
            if kernel['rounding_modes']['rni'] == 0:
                report_lines.append(f"  ⚠ {kernel['name']}: No cvt.rni instructions (using alternative rounding)")
    
    if all_checks_passed:
        report_lines.append("  ✓ All kernels pass basic quality checks")
    
    report_lines.append("")
    report_lines.append("=" * 72)
    
    return '\n'.join(report_lines)


# ======================================================================
# Main
# ======================================================================

def main():
    ptx_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'ptx')
    
    if not os.path.isdir(ptx_dir):
        print(f"PTX directory not found: {ptx_dir}")
        return 1
    
    ptx_files = []
    for f in sorted(os.listdir(ptx_dir)):
        if f.endswith('.ptx'):
            filepath = os.path.join(ptx_dir, f)
            try:
                info = parse_ptx_file(filepath)
                ptx_files.append(info)
                print(f"  ✓ Parsed: {f}")
            except Exception as e:
                print(f"  ✗ Failed to parse {f}: {e}")
    
    if not ptx_files:
        print("No PTX files found to analyze.")
        return 1
    
    report = generate_report(ptx_files)
    print("\n" + report)
    
    # Save report
    report_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                'tests', 'PTX_INSPECTION_REPORT.md')
    with open(report_path, 'w') as f:
        f.write(report)
    print(f"\nReport saved to: {report_path}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
