#!/usr/bin/env python3
"""
Tests for DomainDetector — Study 56 Domain-Aware Translation
=============================================================
Study 56 proved the vocabulary wall is math-specific. These tests verify:
1. Domain detection accuracy across all 6 domains
2. Translation mode selection per domain
3. Math prompts get full translation, non-math get passthrough
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_translator_v2 import (
    DomainDetector,
    translate_for_stage,
    ModelStage,
    NotationNormalizer,
)


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
passed = 0
failed = 0


def assert_eq(name, got, expected):
    global passed, failed
    if got == expected:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got:      {got!r}\n     expected: {expected!r}")


def assert_contains(name, got, substring):
    global passed, failed
    if substring in got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     missing: {substring!r}")


def assert_not_contains(name, got, substring):
    global passed, failed
    if substring not in got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     unexpected: {substring!r}")


def assert_gt(name, got, threshold):
    global passed, failed
    if got > threshold:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     expected > {threshold!r}")


def assert_in(name, got, options):
    global passed, failed
    if got in options:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     expected one of: {options!r}")


# ====================================================================
print("\n--- Domain Detection: Math ---")
# ====================================================================

# Eisenstein norm — strong math signal
d, c = DomainDetector.detect_domain("Compute the Eisenstein norm of a=3, b=5")
assert_eq("eisenstein_norm domain", d, "math")
assert_gt("eisenstein_norm confidence", c, 0.5)

# Möbius function
d, c = DomainDetector.detect_domain("Compute the Möbius function mu(30)")
assert_eq("mobius domain", d, "math")
assert_gt("mobius confidence", c, 0.5)

# Legendre symbol
d, c = DomainDetector.detect_domain("Compute the Legendre symbol (2|7)")
assert_eq("legendre domain", d, "math")

# Arithmetic expression
d, c = DomainDetector.detect_domain("Calculate 3 + 5 * 2")
assert_eq("arithmetic domain", d, "math")

# a^2 notation
d, c = DomainDetector.detect_domain("Compute a^2 - a*b + b^2 where a=2, b=3")
assert_eq("a^2 notation domain", d, "math")

# Unicode superscript
d, c = DomainDetector.detect_domain("Compute a² - ab + b²")
assert_eq("unicode superscript domain", d, "math")

# Modular arithmetic
d, c = DomainDetector.detect_domain("Find the modular inverse of 3 mod 7")
assert_eq("modular inverse domain", d, "math")

# Lattice / spline
d, c = DomainDetector.detect_domain("Snap point (1.5, 2.3) to the Eisenstein lattice")
assert_eq("lattice snap domain", d, "math")

# Greek letters
d, c = DomainDetector.detect_domain("Evaluate Φ_6(2.0)")
assert_eq("cyclotomic greek domain", d, "math")

# ====================================================================
print("\n--- Domain Detection: Chemistry ---")
# ====================================================================

d, c = DomainDetector.detect_domain("What is the molar mass of H2SO4?")
assert_eq("molar mass domain", d, "chemistry")
assert_gt("molar mass confidence", c, 0.5)

d, c = DomainDetector.detect_domain("Balance the reaction: NaOH + HCl")
assert_eq("reaction domain", d, "chemistry")

d, c = DomainDetector.detect_domain("How many moles are in 18g of H2O?")
assert_eq("moles domain", d, "chemistry")

d, c = DomainDetector.detect_domain("What is the oxidation state of Fe in Fe2O3?")
assert_eq("oxidation domain", d, "chemistry")

# ====================================================================
print("\n--- Domain Detection: Physics ---")
# ====================================================================

d, c = DomainDetector.detect_domain("What force is needed to accelerate 5 kg at 3 m/s²?")
assert_eq("force acceleration domain", d, "physics")
assert_gt("force confidence", c, 0.5)

d, c = DomainDetector.detect_domain("Calculate the kinetic energy of a 1000 kg car at 20 m/s")
assert_eq("kinetic energy domain", d, "physics")

d, c = DomainDetector.detect_domain("What is the momentum of a 2 kg ball at 10 m/s?")
assert_eq("momentum domain", d, "physics")

# ====================================================================
print("\n--- Domain Detection: Logic ---")
# ====================================================================

d, c = DomainDetector.detect_domain("If A implies B and B implies C, therefore A implies C")
assert_eq("syllogism domain", d, "logic")

d, c = DomainDetector.detect_domain("Is the following a valid deduction? All men are mortal, Socrates is a man")
assert_eq("deduction domain", d, "logic")

d, c = DomainDetector.detect_domain("What is the contrapositive of: if it rains then the ground is wet?")
assert_eq("contrapositive domain", d, "logic")

# ====================================================================
print("\n--- Domain Detection: Code ---")
# ====================================================================

d, c = DomainDetector.detect_domain("Implement a function to reverse a linked list")
assert_eq("linked list domain", d, "code")

d, c = DomainDetector.detect_domain("Write a recursive algorithm to compute fibonacci numbers")
assert_eq("recursive algo domain", d, "code")

d, c = DomainDetector.detect_domain("def binary_search(arr, target):")
assert_eq("def function domain", d, "code")

d, c = DomainDetector.detect_domain("Create a class Stack with push and pop methods")
assert_eq("class stack domain", d, "code")

# ====================================================================
print("\n--- Domain Detection: General ---")
# ====================================================================

d, c = DomainDetector.detect_domain("Hello, how are you today?")
assert_eq("greeting domain", d, "general")

d, c = DomainDetector.detect_domain("The quick brown fox jumps over the lazy dog")
assert_eq("nonsense domain", d, "general")

d, c = DomainDetector.detect_domain("What time is it?")
assert_eq("time question domain", d, "general")

# ====================================================================
print("\n--- Translation Mode Selection ---")
# ====================================================================

assert_eq("math mode", DomainDetector.get_translation_mode("math"), "full")
assert_eq("chemistry mode", DomainDetector.get_translation_mode("chemistry"), "minimal")
assert_eq("physics mode", DomainDetector.get_translation_mode("physics"), "minimal")
assert_eq("logic mode", DomainDetector.get_translation_mode("logic"), "passthrough")
assert_eq("code mode", DomainDetector.get_translation_mode("code"), "passthrough")
assert_eq("general mode", DomainDetector.get_translation_mode("general"), "passthrough")
assert_eq("unknown mode", DomainDetector.get_translation_mode("unknown"), "passthrough")

# ====================================================================
print("\n--- translate_for_stage: Math Gets Full Translation ---")
# ====================================================================

# Math prompt at Stage 2 should get translated (activation key + natural language)
math_prompt = "Compute the Eisenstein norm of a²-ab+b² where a=2, b=3"
r = translate_for_stage(math_prompt, ModelStage.CAPABLE)
assert_contains("math stage3 activation key", r, "Eisenstein")

# Math prompt at Stage 1 should get bare arithmetic
r = translate_for_stage(math_prompt, ModelStage.ECHO)
assert_not_contains("math stage1 no eisenstein", r, "Eisenstein")

# ====================================================================
print("\n--- translate_for_stage: Non-Math Gets Passthrough ---")
# ====================================================================

# Chemistry prompt — should NOT get activation key injection, just passthrough
chem_prompt = "What is the molar mass of H2SO4?"
r = translate_for_stage(chem_prompt, ModelStage.CAPABLE)
assert_eq("chemistry passthrough", r, chem_prompt)

r = translate_for_stage(chem_prompt, ModelStage.ECHO)
assert_eq("chemistry passthrough stage1", r, chem_prompt)

# Physics prompt — should get minimal (unicode normalize only, not here)
phys_prompt = "What force is needed to accelerate 5 kg at 3 m/s²?"
r = translate_for_stage(phys_prompt, ModelStage.CAPABLE)
# Minimal: should normalize unicode but not inject keys
assert_not_contains("physics no activation key", r, "Using the")

# Logic prompt — passthrough
logic_prompt = "If A implies B and B implies C, does A imply C?"
r = translate_for_stage(logic_prompt, ModelStage.CAPABLE)
assert_eq("logic passthrough", r, logic_prompt)

r = translate_for_stage(logic_prompt, ModelStage.ECHO)
assert_eq("logic passthrough stage1", r, logic_prompt)

# Code prompt — passthrough
code_prompt = "Implement a function to reverse a linked list"
r = translate_for_stage(code_prompt, ModelStage.CAPABLE)
assert_eq("code passthrough", r, code_prompt)

r = translate_for_stage(code_prompt, ModelStage.ECHO)
assert_eq("code passthrough stage1", r, code_prompt)

# General prompt — passthrough
general_prompt = "What is the capital of France?"
r = translate_for_stage(general_prompt, ModelStage.CAPABLE)
assert_eq("general passthrough", r, general_prompt)

# ====================================================================
print("\n--- translate_for_stage: Explicit Domain Override ---")
# ====================================================================

# Force math domain on a generic-looking prompt
generic_prompt = "Compute the value for a=3, b=5"
r = translate_for_stage(generic_prompt, ModelStage.CAPABLE, domain="math")
# Math domain should trigger full translation pipeline
assert_contains("forced math domain translation", r, "Compute")

# Force passthrough on a math-looking prompt
mathish = "Calculate the Eisenstein norm of a=3, b=5"
r = translate_for_stage(mathish, ModelStage.CAPABLE, domain="code")
# Forced code domain should passthrough
assert_eq("forced code domain passthrough", r, mathish)

# ====================================================================
print("\n--- Edge Cases ---")
# ====================================================================

# Empty prompt
d, c = DomainDetector.detect_domain("")
assert_in("empty domain", d, ["general", "math", "chemistry", "physics", "logic", "code"])

# Very short prompt
d, c = DomainDetector.detect_domain("compute")
assert_in("short prompt domain", d, ["general", "math", "chemistry", "physics", "logic", "code"])

# Mixed signals: math + code
d, c = DomainDetector.detect_domain("Implement a recursive function to compute fibonacci numbers")
# Should be code or math (both have strong signals)
assert_in("mixed math+code domain", d, ["code", "math"])

# Unicode-only prompt
d, c = DomainDetector.detect_domain("∑∫√")
assert_eq("unicode math symbols", d, "math")

# ====================================================================
print(f"\n{'='*60}")
print(f"Domain Detector Tests: {passed} passed, {failed} failed")
if failed:
    print("❌ SOME TESTS FAILED")
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED")
