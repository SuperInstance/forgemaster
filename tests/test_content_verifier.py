#!/usr/bin/env python3
"""
Tests for content_verifier — Tier-1 Ground Truth Oracle.

Tests specifically target the 3 undetected attacks from Study 68:
1. Mimic: exact fleet-average copying
2. Burst errors: 10% intermittent wrong answers
3. Coupling mimic: 8% consistent deviation with normal structure

Plus tests for the integration layer and triple-voting system.
"""

import math
import random
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_verifier import (
    CanaryChecker,
    CanaryDifficulty,
    CanaryTile,
    ContentDetectionResult,
    ContentFlag,
    ContentFlagType,
    ContentVerificationDetector,
    ContentVerifierConfig,
    CrossValidationMixin,
    CrossValidationResult,
    SpotCheckResult,
    SpotCheckVerifier,
    AgentContentStats,
    build_canary_library,
    check_canary_answer,
    create_triple_detector,
    semantic_similarity,
    _normalize_answer,
    _extract_numeric,
)

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


def assert_true(name, got):
    assert_eq(name, got, True)


def assert_false(name, got):
    assert_eq(name, got, False)


def assert_approx(name, got, expected, tol=0.05):
    global passed, failed
    if abs(got - expected) <= tol:
        passed += 1
        print(f"  ✅ {name} ({got:.4f} ≈ {expected:.4f})")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got:      {got:.4f}\n     expected: {expected:.4f} (tol={tol})")


def assert_contains(name, got, substring):
    global passed, failed
    if substring in got:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     missing: {substring!r}")


def assert_gt(name, got, threshold):
    global passed, failed
    if got > threshold:
        passed += 1
        print(f"  ✅ {name} ({got} > {threshold})")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got:      {got}\n     expected: > {threshold}")


def assert_lt(name, got, threshold):
    global passed, failed
    if got < threshold:
        passed += 1
        print(f"  ✅ {name} ({got} < {threshold})")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got:      {got}\n     expected: < {threshold}")


def assert_in(name, got, collection):
    global passed, failed
    if got in collection:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     got: {got!r}\n     not in: {collection!r}")


def assert_not_in(name, item, collection):
    global passed, failed
    if item not in collection:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name}\n     item: {item!r}\n     unexpectedly in: {collection!r}")


# =========================================================================
# 1. Semantic similarity tests
# =========================================================================

print("\n=== 1. Semantic Similarity ===")

assert_approx("exact match", semantic_similarity("42", "42"), 1.0)
assert_approx("exact match with text", semantic_similarity("The answer is 42", "42"), 1.0)
assert_approx("numeric close", semantic_similarity("42", "42.01"), 0.95, tol=0.1)
assert_approx("numeric far", semantic_similarity("42", "100"), 0.0, tol=0.5)
assert_approx("same text", semantic_similarity("hello world", "hello world"), 1.0)
assert_approx("contains (normalizes to exact)", semantic_similarity("42", "The answer is 42"), 1.0)
assert_approx("completely different", semantic_similarity("42", "banana"), 0.0, tol=0.2)
assert_approx("zero values", semantic_similarity("0", "0"), 1.0)
assert_approx("negative numbers", semantic_similarity("-5", "-5"), 1.0)
assert_approx("one zero one nonzero", semantic_similarity("0", "42"), 0.0, tol=0.1)

# =========================================================================
# 2. Answer normalization tests
# =========================================================================

print("\n=== 2. Answer Normalization ===")

assert_eq("normalize strip whitespace", _normalize_answer("  42  "), "42")
assert_eq("normalize strip prefix", _normalize_answer("The answer is 42"), "42")
assert_eq("normalize lowercase", _normalize_answer("FORTY TWO"), "forty two")
assert_eq("normalize trailing punct", _normalize_answer("42."), "42")

# =========================================================================
# 3. Numeric extraction tests
# =========================================================================

print("\n=== 3. Numeric Extraction ===")

assert_eq("extract integer", _extract_numeric("42"), 42.0)
assert_eq("extract decimal", _extract_numeric("3.14"), 3.14)
assert_eq("extract negative", _extract_numeric("-5"), -5.0)
assert_eq("extract from text", _extract_numeric("the answer is 42"), 42.0)
assert_eq("extract none", _extract_numeric("no number here"), None)

# =========================================================================
# 4. Canary answer checking tests
# =========================================================================

print("\n=== 4. Canary Answer Checking ===")

canary_exact = CanaryTile(
    canary_id="test", difficulty=CanaryDifficulty.TIER_1,
    prompt="test", correct_answer="42", answer_type="exact",
)
assert_true("canary exact match", check_canary_answer(canary_exact, "42"))
assert_true("canary exact match normalized", check_canary_answer(canary_exact, "The answer is 42"))
assert_false("canary exact mismatch", check_canary_answer(canary_exact, "43"))

canary_numeric = CanaryTile(
    canary_id="test", difficulty=CanaryDifficulty.TIER_1,
    prompt="test", correct_answer="3.14159", answer_type="numeric",
    tolerance=0.01,
)
assert_true("canary numeric close", check_canary_answer(canary_numeric, "3.14"))
assert_false("canary numeric far", check_canary_answer(canary_numeric, "3.5"))

canary_contains = CanaryTile(
    canary_id="test", difficulty=CanaryDifficulty.TIER_1,
    prompt="test", correct_answer="prime", answer_type="contains",
)
assert_true("canary contains match", check_canary_answer(canary_contains, "It is a prime number"))
assert_false("canary contains miss", check_canary_answer(canary_contains, "It is composite"))

# =========================================================================
# 5. Canary library tests
# =========================================================================

print("\n=== 5. Canary Library ===")

library = build_canary_library()
assert_gt("library not empty", len(library), 50)

tier1 = [c for c in library if c.difficulty == CanaryDifficulty.TIER_1]
tier2 = [c for c in library if c.difficulty == CanaryDifficulty.TIER_2]
tier3 = [c for c in library if c.difficulty == CanaryDifficulty.TIER_3]

assert_gt("tier1 canaries exist", len(tier1), 20)
assert_gt("tier2 canaries exist", len(tier2), 10)
assert_gt("tier3 canaries exist", len(tier3), 3)

# Verify specific known answers
eisenstein_1_1 = [c for c in library if c.canary_id == "canary-t1-eisenstein-1-1"]
if eisenstein_1_1:
    assert_eq("eisenstein(1,1)=1", eisenstein_1_1[0].correct_answer, "1")

mobius_30 = [c for c in library if c.canary_id == "canary-t2-mobius-30"]
if mobius_30:
    assert_eq("mobius(30)=-1", mobius_30[0].correct_answer, "-1")

mobius_4 = [c for c in library if c.canary_id == "canary-t2-mobius-4"]
if mobius_4:
    assert_eq("mobius(4)=0", mobius_4[0].correct_answer, "0")

# =========================================================================
# 6. SpotCheckVerifier tests
# =========================================================================

print("\n=== 6. SpotCheckVerifier ===")

config = ContentVerifierConfig(spot_check_rate=1.0)
spot = SpotCheckVerifier(config)

# Submit a tile — should always be selected at 100% rate
req = spot.submit_tile("agent1", "Compute 2+2", "4")
assert_true("spot submit selected", req is not None)
assert_eq("spot tile has id", "tile_id" in (req or {}), True)

# Verify with matching answer → not flagged
result = spot.verify("t1", "agent1", "Compute 2+2", "4", "4", "agent2")
assert_false("spot verify match not flagged", result.flagged)
assert_approx("spot verify similarity", result.similarity, 1.0)

# Verify with divergent answer → flagged
result = spot.verify("t2", "agent1", "Compute 2+2", "4", "99", "agent2")
assert_true("spot verify divergence flagged", result.flagged)
assert_lt("spot verify low similarity", result.similarity, 0.5)

# Same agent as verifier → skip (not flagged, sim=1.0)
result = spot.verify("t3", "agent1", "Compute 2+2", "4", "4", "agent1")
assert_false("spot same agent not flagged", result.flagged)

# Stats
stats = spot.get_agent_stats("agent1")
assert_gt("spot stats checks", stats.spot_checks, 0)

flags = spot.get_flags("agent1")
assert_gt("spot flags for agent1", len(flags), 0)
assert_eq("spot flag type", flags[0].flag_type, ContentFlagType.SPOT_CHECK_DIVERGENCE)

# Test with 0% rate
config_low = ContentVerifierConfig(spot_check_rate=0.0)
spot_low = SpotCheckVerifier(config_low)
req = spot_low.submit_tile("agent1", "Compute 2+2", "4")
assert_true("spot 0% rate not selected", req is None)

# =========================================================================
# 7. CrossValidationMixin tests
# =========================================================================

print("\n=== 7. CrossValidationMixin ===")

config = ContentVerifierConfig(
    cross_validation_rate=1.0,
    disagreement_threshold=0.3,
)
cross = CrossValidationMixin(config)

# All agree → not flagged
result = cross.cross_validate("t1", {
    "agent1": "42",
    "agent2": "42",
    "agent3": "42",
})
assert_false("cross all agree not flagged", result.flagged)
assert_approx("cross agreement rate", result.agreement_rate, 1.0)

# Two agree, one clearly disagrees → flagged
result = cross.cross_validate("t2", {
    "agent1": "42",
    "agent2": "42",
    "agent3": "99",
})
assert_true("cross one disagree flagged", result.flagged)
assert_gt("cross disagreement rate", result.disagreement_rate, 0.3)

# With arbiter: 3 agents, one clearly wrong
result = cross.cross_validate("t3", {
    "agent1": "42",
    "agent2": "42",
    "agent3": "10",
}, arbiter_answer="42")
assert_true("cross arbiter marks divergent", result.flagged)

# High disagreement agents
high_dis = cross.get_high_disagreement_agents()
assert_in("agent3 high disagreement", "agent3", high_dis)

# Too few agents → skip (not flagged)
result = cross.cross_validate("t4", {"agent1": "42"})
assert_false("cross single agent not flagged", result.flagged)

# =========================================================================
# 8. CanaryChecker tests
# =========================================================================

print("\n=== 8. CanaryChecker ===")

config = ContentVerifierConfig(canary_interval=1, canary_fail_threshold=2)
canary = CanaryChecker(config)

# Should inject every tile at interval=1
assert_true("canary should inject", canary.should_inject())

# Inject a canary
tile = canary.inject_canary(CanaryDifficulty.TIER_1)
assert_true("canary inject returns tile", tile is not None)
assert_eq("canary tier 1", tile.difficulty, CanaryDifficulty.TIER_1)

# Correct response → not flagged
result = canary.check_response(tile, "agent1", tile.correct_answer)
assert_true("canary correct", result["correct"])

# Wrong response → failure tracking
wrong_tile = CanaryTile(
    canary_id="test-wrong",
    difficulty=CanaryDifficulty.TIER_1,
    prompt="What is 1+1?",
    correct_answer="2",
    answer_type="exact",
)
result = canary.check_response(wrong_tile, "agent2", "3")
assert_false("canary wrong answer", result["correct"])

# Second wrong → flag (threshold=2)
result = canary.check_response(wrong_tile, "agent2", "5")
stats = canary.get_agent_stats("agent2")
assert_gt("canary consecutive fails", stats.consecutive_canary_fails, 0)

flags = canary.get_flags("agent2")
assert_gt("canary flags after 2 fails", len(flags), 0)
assert_eq("canary flag type", flags[0].flag_type, ContentFlagType.CANARY_FAILURE)

# Correct answer resets consecutive fails
result = canary.check_response(wrong_tile, "agent2", "2")
stats = canary.get_agent_stats("agent2")
assert_eq("canary reset consecutive", stats.consecutive_canary_fails, 0)


# =========================================================================
# 9. STUDY 68 ATTACK 1: Mimic Detection
# =========================================================================

print("\n=== 9. Study 68 Attack: Mimic ===")

# Mimic copies fleet answers. If fleet is wrong, mimic propagates the error.
# Spot-check catches when mimic's copied answer differs from a Tier-1 verifier.

config = ContentVerifierConfig(spot_check_rate=1.0, similarity_threshold=0.7)
spot_mimic = SpotCheckVerifier(config)

# Mimic copies correct answer → not flagged (correct behavior)
result = spot_mimic.verify("m1", "mimic-agent", "Compute...", "19", "19", "verifier")
assert_false("mimic correct copy → not flagged", result.flagged)

# Mimic copies wrong fleet answer → flagged by spot-check
result = spot_mimic.verify("m2", "mimic-agent", "Compute...", "5", "19", "verifier")
assert_true("mimic wrong copy → flagged by spot-check", result.flagged)

# Cross-validation catches mimic: 3 honest + 1 mimic, mimic clearly wrong
cross_mimic = CrossValidationMixin(config)
result = cross_mimic.cross_validate("m3", {
    "honest1": "19", "honest2": "19", "honest3": "19", "mimic": "5",
})
assert_true("mimic caught by cross-validation", result.flagged)

# Canary catches mimic that can't compute independently
canary_mimic = CanaryChecker(ContentVerifierConfig(canary_fail_threshold=1))
tile = CanaryTile(
    canary_id="mimic-test", difficulty=CanaryDifficulty.TIER_1,
    prompt="Compute 7 * 6", correct_answer="42", answer_type="numeric",
)
result = canary_mimic.check_response(tile, "mimic-agent", "41")
assert_false("mimic gets canary wrong", result["correct"])
flags = canary_mimic.get_flags("mimic-agent")
assert_gt("mimic canary flagged", len(flags), 0)

print("  ✅ Mimic: detected by spot-check + cross-validation + canary")

# =========================================================================
# 10. STUDY 68 ATTACK 2: Burst Errors Detection
# =========================================================================

print("\n=== 10. Study 68 Attack: Burst Errors ===")

random.seed(42)

# Burst errors: intermittent wrong answers. Canaries are the primary defense
# because they inject known-answer tiles that burst-error agents will sometimes fail.

# Canary-based detection of burst errors
canary_burst = CanaryChecker(ContentVerifierConfig(canary_fail_threshold=2))
burst_fails = 0
for i in range(100):
    tile = canary_burst.inject_canary(CanaryDifficulty.TIER_1)
    if tile:
        # 90% correct, 10% wrong
        if random.random() < 0.9:
            resp = tile.correct_answer
        else:
            resp = "wrong"
            burst_fails += 1
        canary_burst.check_response(tile, "burst-agent", resp)

stats = canary_burst.get_agent_stats("burst-agent")
print(f"  ℹ️  Burst canary failures: {stats.canary_failures}/{stats.canary_attempts}")

# Even at 10% error rate, over 100 canaries expect ~10 failures
# With canary_fail_threshold=2, agent should be flagged
burst_flags = canary_burst.get_flags("burst-agent")
if stats.canary_failures >= 2:
    assert_gt("burst agent canary flagged", len(burst_flags), 0)
else:
    print(f"  ⚠️  Burst agent had {stats.canary_failures} failures (< threshold 2), not flagged")

# Spot-check catches burst errors when it samples a wrong answer
spot_burst = SpotCheckVerifier(ContentVerifierConfig(spot_check_rate=0.5))
for i in range(200):
    if random.random() < 0.9:
        answer = "19"
    else:
        answer = "5"  # clearly wrong
    req = spot_burst.submit_tile("burst-agent", f"tile {i}", answer, f"bt{i}")
    if req:
        spot_burst.verify(f"bt{i}", "burst-agent", f"tile {i}", answer, "19", "verifier")

burst_spot_flags = spot_burst.get_flags("burst-agent")
print(f"  ℹ️  Burst spot-check flags: {len(burst_spot_flags)}")
assert_gt("burst caught by spot-check", len(burst_spot_flags), 0)

# Cross-validation catches burst when honest majority disagrees
cross_burst = CrossValidationMixin(ContentVerifierConfig(disagreement_threshold=0.3))
cross_flags_count = 0
for i in range(50):
    if random.random() < 0.1:
        burst_answer = "5"
    else:
        burst_answer = "19"
    result = cross_burst.cross_validate(f"bt{i}", {
        "honest1": "19", "honest2": "19", "burst-agent": burst_answer,
    })
    if result.flagged:
        cross_flags_count += 1

assert_gt("burst errors caught by cross-validation", cross_flags_count, 0)

print("  ✅ Burst errors: detected by canary + spot-check + cross-validation")

# =========================================================================
# 11. STUDY 68 ATTACK 3: Coupling Mimic Detection
# =========================================================================

print("\n=== 11. Study 68 Attack: Coupling Mimic ===")

random.seed(123)

# Coupling mimic: 8% consistent deviation. This is the hardest attack.
# Canary tiles with numeric tolerance are the primary defense.

# Canary with 1% tolerance catches 8% deviation
canary_coupling = CanaryChecker(ContentVerifierConfig(canary_fail_threshold=1))
tile = CanaryTile(
    canary_id="coupling-test", difficulty=CanaryDifficulty.TIER_1,
    prompt="What is 100?", correct_answer="100", answer_type="numeric",
    tolerance=0.05,  # 5% tolerance
)
# 8% deviation: 108 vs 100 → 8% error > 5% tolerance → FAIL
result = canary_coupling.check_response(tile, "coupling-agent", "108")
assert_false("coupling mimic fails canary (8% > 5% tol)", result["correct"])
flags = canary_coupling.get_flags("coupling-agent")
assert_gt("coupling canary flagged", len(flags), 0)

# Canary with 10% tolerance: 8% deviation would PASS
canary_loose = CanaryChecker(ContentVerifierConfig(canary_fail_threshold=1))
tile_loose = CanaryTile(
    canary_id="coupling-loose", difficulty=CanaryDifficulty.TIER_1,
    prompt="What is 100?", correct_answer="100", answer_type="numeric",
    tolerance=0.10,  # 10% tolerance
)
result = canary_loose.check_response(tile_loose, "coupling-agent", "108")
assert_true("coupling mimic passes canary (8% < 10% tol)", result["correct"])

# With tighter similarity threshold, spot-check catches 8% deviation
spot_tight = SpotCheckVerifier(ContentVerifierConfig(similarity_threshold=0.9))
# sim(100, 108) = 1 - 8/108 ≈ 0.926 > 0.9 → barely passes
result = spot_tight.verify("cm1", "coupling-agent", "Compute", "108", "100", "verifier")
print(f"  ℹ️  Coupling mimic spot-check sim(108,100) = {result.similarity:.3f} (threshold 0.9)")
# With threshold 0.9, 0.926 barely passes. With 0.95 it would fail.
assert_false("coupling 8% deviation passes spot-check at 0.9 threshold", result.flagged)

# With very tight threshold (0.95), spot-check catches it
spot_vtight = SpotCheckVerifier(ContentVerifierConfig(similarity_threshold=0.95))
result = spot_vtight.verify("cm2", "coupling-agent", "Compute", "108", "100", "verifier")
assert_true("coupling 8% caught by spot-check at 0.95 threshold", result.flagged)

print("  ✅ Coupling mimic: canary tiles (5% tol) and tight spot-check (0.95) catch 8% deviation")
print("  ℹ️  8% is in the detection boundary — tolerance/threshold tuning matters")

# =========================================================================
# 12. ContentVerificationDetector integration
# =========================================================================

print("\n=== 12. ContentVerificationDetector Integration ===")

config = ContentVerifierConfig()
detector = ContentVerificationDetector(config)

# Submit tiles
for i in range(20):
    detector.submit_tile("agent1", f"Compute {i}", str(i * 2), f"t{i}")

# Simulate verification: one divergence
detector.process_spot_verification("t0", "agent1", "Compute 0", "0", "0", "verifier")
detector.process_spot_verification("t1", "agent1", "Compute 1", "2", "99", "verifier")  # divergence

# Detection without structural flags → investigate
result = detector.detect(gl9_faulty=[], hebbian_anomalies=[])
assert_contains("detector recommendation investigate", result.recommendation, "INVESTIGATE")

# Detection WITH structural flags → quarantine
result = detector.detect(gl9_faulty=["agent1"], hebbian_anomalies=[])
assert_in("agent1 flagged", "agent1", result.flagged_agents)

# Status check
status = detector.get_status()
assert_gt("status spot checker total", status["spot_checker"]["total_tiles"], 0)

# =========================================================================
# 13. Triple-voting detector
# =========================================================================

print("\n=== 13. Triple-Voting Detector ===")

from dual_fault_detector import DualFaultDetector

dual = DualFaultDetector()
triple = create_triple_detector(dual)

# No faults → healthy
result = triple["detect"]([], [])
assert_contains("triple healthy", result["recommendation"], "HEALTHY")

# Content fault only → investigate, NOT quarantine
content = triple["content"]
content.process_spot_verification(
    "tv1", "agent1", "Compute", "5", "42", "verifier",  # clearly wrong
)
result = triple["detect"]([], [])
assert_in("agent1 investigate (content only)", "agent1", result["investigate"])
assert_not_in("agent1 not quarantined (content only)", "agent1", result["quarantine"])

# Content + structural → quarantine
result = triple["detect"](gl9_faulty=["agent1"], hebbian_anomalies=[])
assert_in("agent1 quarantined (content+structural)", "agent1", result["quarantine"])

print("  ✅ Triple voting: content alone investigates, content+structural quarantines")

# =========================================================================
# 14. ContentFlag weight calculation
# =========================================================================

print("\n=== 14. ContentFlag Weight ===")

flag = ContentFlag(agent_id="test", flag_type=ContentFlagType.CANARY_FAILURE, confidence=1.0)
assert_approx("canary flag weight", flag.weight, 1.0)

flag = ContentFlag(agent_id="test", flag_type=ContentFlagType.SPOT_CHECK_DIVERGENCE, confidence=0.8)
assert_approx("spot flag weight", flag.weight, 0.7 * 0.8, tol=0.1)

flag = ContentFlag(agent_id="test", flag_type=ContentFlagType.CROSS_VALIDATION_DISAGREEMENT, confidence=0.5)
assert_approx("cross flag weight", flag.weight, 0.5 * 0.5, tol=0.1)

# =========================================================================
# 15. Configuration defaults
# =========================================================================

print("\n=== 15. Configuration Defaults ===")

config = ContentVerifierConfig()
assert_approx("default spot check rate", config.spot_check_rate, 0.10)
assert_approx("default cross validation rate", config.cross_validation_rate, 0.05)
assert_eq("default canary interval", config.canary_interval, 50)
assert_approx("default disagreement threshold", config.disagreement_threshold, 0.3)
assert_true("default content requires structural", config.content_quarantine_requires_structural)

# =========================================================================
# 16. Canary library correctness verification
# =========================================================================

print("\n=== 16. Canary Library Correctness ===")

library = build_canary_library()

# Verify Eisenstein norm canaries: a²-ab+b²
for c in library:
    if c.canary_id.startswith("canary-t1-eisenstein-"):
        parts = c.canary_id.split("-")
        a, b = int(parts[-2]), int(parts[-1])
        expected = a * a - a * b + b * b
        assert_eq(f"eisenstein({a},{b})", c.correct_answer, str(expected))

# Verify multiplication canaries
for c in library:
    if c.canary_id.startswith("canary-t1-mul-"):
        parts = c.canary_id.split("-")
        x, y = int(parts[-2]), int(parts[-1])
        assert_eq(f"mul({x},{y})", c.correct_answer, str(x * y))

# Verify Möbius canaries
for c in library:
    if c.canary_id.startswith("canary-t2-mobius-"):
        n = int(c.canary_id.split("-")[-1])
        # Compute correct Möbius value
        factors = []
        m = n
        d = 2
        has_squared = False
        while d * d <= m:
            cnt = 0
            while m % d == 0:
                m //= d
                cnt += 1
            if cnt > 1:
                has_squared = True
                break
            if cnt == 1:
                factors.append(d)
            d += 1
        if not has_squared and m > 1:
            factors.append(m)
        if n == 1:
            expected = 1
        elif has_squared:
            expected = 0
        else:
            expected = (-1) ** len(factors)
        assert_eq(f"mobius({n})", c.correct_answer, str(expected))

# =========================================================================
# 17. Edge cases
# =========================================================================

print("\n=== 17. Edge Cases ===")

# Empty answers
assert_approx("empty vs empty", semantic_similarity("", ""), 1.0)
assert_approx("empty vs something", semantic_similarity("", "42"), 0.0)

# Spot check with no prior submissions
spot_empty = SpotCheckVerifier()
flags = spot_empty.get_flags()
assert_eq("empty spot flags", len(flags), 0)

# Cross validate with exactly 2 agents agreeing
cross2 = CrossValidationMixin()
result = cross2.cross_validate("e1", {"a": "42", "b": "42"})
assert_false("2 agents agree", result.flagged)

# Cross validate with exactly 2 agents disagreeing clearly
result = cross2.cross_validate("e2", {"a": "42", "b": "1"})
assert_true("2 agents disagree", result.flagged)

# Canary with zero answer
canary_zero = CanaryTile(
    canary_id="zero-test", difficulty=CanaryDifficulty.TIER_1,
    prompt="What is 0?", correct_answer="0", answer_type="numeric",
)
assert_true("canary zero correct", check_canary_answer(canary_zero, "0"))
assert_false("canary zero wrong", check_canary_answer(canary_zero, "1"))

# Canary checker library has all difficulties
lib = build_canary_library()
difficulties = set(c.difficulty for c in lib)
assert_eq("all difficulties present", len(difficulties), 3)

# AgentContentStats computed properties
stats = AgentContentStats(agent_id="test", spot_checks=10, spot_flags=3)
assert_approx("spot flag rate", stats.spot_flag_rate, 0.3, tol=0.01)
stats2 = AgentContentStats(agent_id="test2")
assert_approx("empty spot flag rate", stats2.spot_flag_rate, 0.0)


# =========================================================================
# Summary
# =========================================================================

print(f"\n{'='*60}")
print(f"Results: {passed} passed, {failed} failed")
if failed:
    print("❌ SOME TESTS FAILED")
    sys.exit(1)
else:
    print("✅ ALL TESTS PASSED")
    print("\nStudy 68 gap analysis:")
    print("  ✅ Mimic: caught by spot-check + cross-validation + canary")
    print("  ✅ Burst errors: caught by canary + spot-check + cross-validation")
    print("  ✅ Coupling mimic: caught by canary (5% tol) + tight spot-check (0.95)")
    print("  ✅ Triple voting: content+structural → quarantine, content alone → investigate")
    print("\nKey insight: Canary tiles with numeric tolerance are the most reliable")
    print("defense against the 3 undetected Study 68 attacks.")
