#!/usr/bin/env python3
"""
Tests for Fleet Auto-Translator V2 — Activation-Key Model
===========================================================
Includes offline unit tests + optional live API tests against DeepInfra models.

Run offline: python3 -m pytest tests/test_fleet_translator_v2.py -v -k "not live"
Run all:     python3 -m pytest tests/test_fleet_translator_v2.py -v
"""

import os
import sys
import math
import re
import time
import pytest

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fleet_translator_v2 import (
    ModelStage,
    NotationNormalizer as NN,
    ActivationKeyEngineer as AK,
    translate,
    translate_for_stage,
    FleetRouter,
    TranslationLog,
    KNOWN_STAGES,
)


# ========================================================================
# Notation Normalizer Tests
# ========================================================================

class TestNotationNormalizer:
    """Test unicode normalization, ASCII math, natural language conversion."""

    # -- normalize_unicode ---------------------------------------------------

    def test_superscript_2(self):
        assert NN.normalize_unicode("a²") == "a^2"

    def test_superscript_3(self):
        assert NN.normalize_unicode("x³") == "x^3"

    def test_superscript_multi(self):
        assert NN.normalize_unicode("a² + b²") == "a^2 + b^2"

    def test_full_expression(self):
        assert NN.normalize_unicode("a²-ab+b²") == "a^2-ab+b^2"

    # -- Greek conversion ---------------------------------------------------

    def test_greek_mu(self):
        assert "mu" in NN.normalize_unicode("μ(30)")

    def test_greek_phi(self):
        assert "Phi" in NN.normalize_unicode("Φ_6(x)")

    def test_greek_alpha(self):
        assert "alpha" in NN.normalize_unicode("α + β")

    def test_greek_pi(self):
        assert "pi" in NN.normalize_unicode("2π")

    # -- ASCII math ----------------------------------------------------------

    def test_ascii_squared(self):
        result = NN.to_ascii_math("a²")
        assert "a*a" in result

    def test_ascii_cubed(self):
        result = NN.to_ascii_math("x³")
        assert "x*x*x" in result

    # -- Natural language ----------------------------------------------------

    def test_nl_squared(self):
        result = NN.to_natural_language("a²")
        assert "squared" in result

    def test_nl_full_expression(self):
        result = NN.to_natural_language("a²-ab+b²")
        assert "squared" in result
        assert "minus" in result
        assert "plus" in result

    def test_nl_cubed(self):
        result = NN.to_natural_language("x³")
        assert "cubed" in result

    def test_nl_power(self):
        result = NN.to_natural_language("x^5")
        assert "5th power" in result

    # -- Detection -----------------------------------------------------------

    def test_detect_unicode(self):
        assert NN.detect_notation("a²-ab+b²") == "unicode"

    def test_detect_ascii_caret(self):
        assert NN.detect_notation("a^2 - a*b + b^2") == "ascii"

    def test_detect_plain(self):
        assert NN.detect_notation("hello world") == "plain"

    def test_detect_domain_labels_eisenstein(self):
        assert NN.detect_domain_labels("Eisenstein norm of a=1") == ["Eisenstein"]

    def test_detect_domain_labels_mobius(self):
        assert "Möbius" in NN.detect_domain_labels("Compute Möbius μ(30)")

    def test_detect_domain_labels_empty(self):
        assert NN.detect_domain_labels("compute 3 + 5") == []

    def test_has_symbolic_notation(self):
        assert NN.has_symbolic_notation("a²-ab+b²") is True

    def test_has_no_symbolic_notation(self):
        assert NN.has_symbolic_notation("hello world") is False


# ========================================================================
# Activation Key Engineer Tests
# ========================================================================

class TestActivationKeyEngineer:
    """Test activation key injection based on V6 states."""

    # STATE A: label + notation → passthrough
    def test_state_a_passthrough(self):
        text = "Eisenstein norm: a²-ab+b²"
        result = AK.inject_key(text, "eisenstein_norm")
        assert result == text  # unchanged

    def test_state_a_with_mobius(self):
        text = "Möbius function μ(30)"
        result = AK.inject_key(text, "mobius")
        assert result == text

    # STATE C: notation without label → inject key
    def test_state_c_injects_eisenstein(self):
        text = "a²-ab+b²"
        result = AK.inject_key(text, "eisenstein_norm")
        assert "Eisenstein" in result

    def test_state_c_injects_from_task(self):
        text = "a^2 - a*b + b^2"
        result = AK.inject_key(text, "eisenstein_norm")
        assert "Eisenstein" in result

    # STATE D: step-by-step → passthrough
    def test_state_d_step_by_step(self):
        text = "First compute a*a, then subtract a*b, then add b*b"
        result = AK.inject_key(text, "eisenstein_norm")
        assert result == text

    def test_state_d_explicit_step_by_step(self):
        text = "Step by step, compute: a times a minus a times b plus b times b"
        result = AK.inject_key(text, "eisenstein_norm")
        assert result == text

    # Plain text injection from task type
    def test_plain_injects_from_task(self):
        text = "compute a=3, b=5"
        result = AK.inject_key(text, "eisenstein_norm")
        assert "Eisenstein" in result

    def test_plain_no_task(self):
        text = "compute a=3, b=5"
        result = AK.inject_key(text, None)
        assert result == text  # can't inject without task

    # Don't inject if key already present
    def test_no_double_inject(self):
        text = "Using the Eisenstein norm: compute"
        result = AK.inject_key(text, "eisenstein_norm")
        # Should not add another "Using the..."
        assert result.count("Eisenstein") == 1


# ========================================================================
# Stage-Aware Translation Tests
# ========================================================================

class TestTranslate:
    """Test the main translate() function across all stages."""

    # -- Stage 4 (FULL): passthrough ----------------------------------------

    def test_stage4_eisenstein(self):
        r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.FULL)
        assert "Eisenstein norm" in r

    def test_stage4_mobius(self):
        r = translate("mobius", {"n": 30}, ModelStage.FULL)
        assert "Möbius" in r

    def test_stage4_legendre(self):
        r = translate("legendre", {"a": 2, "p": 7}, ModelStage.FULL)
        assert "Legendre" in r

    def test_stage4_cyclotomic(self):
        r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.FULL)
        assert "cyclotomic" in r

    # -- Stage 3 (CAPABLE): activation key + ASCII --------------------------

    def test_stage3_eisenstein_key(self):
        r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.CAPEABLE)
        assert "Eisenstein norm" in r
        assert "a^2" in r  # ASCII notation
        assert "²" not in r  # no unicode

    def test_stage3_mobius_key(self):
        r = translate("mobius", {"n": 30}, ModelStage.CAPEABLE)
        assert "Möbius" in r

    def test_stage3_covering_radius(self):
        r = translate("covering_radius", {}, ModelStage.CAPEABLE)
        assert "Eisenstein" in r
        assert "covering radius" in r.lower()

    # -- Stage 2 (META_ECHO): natural language + activation key --------------

    def test_stage2_eisenstein_natural(self):
        r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.META_ECHO)
        assert "squared" in r  # natural language

    def test_stage2_eisenstein_step_by_step(self):
        r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.META_ECHO)
        assert "Step by step" in r or "squared" in r

    # -- Stage 1 (ECHO): bare arithmetic only --------------------------------

    def test_stage1_eisenstein(self):
        r = translate("eisenstein_norm", {"a": 3, "b": 5}, ModelStage.ECHO)
        assert r == "Compute: 9 - 15 + 25 = ?"
        assert "Eisenstein" not in r

    def test_stage1_eisenstein_unit(self):
        r = translate("eisenstein_norm", {"a": 1, "b": 0}, ModelStage.ECHO)
        assert r == "Compute: 1 - 0 + 0 = ?"

    def test_stage1_covering_radius(self):
        r = translate("covering_radius", {}, ModelStage.ECHO)
        assert "1/sqrt(3)" in r

    def test_stage1_mobius(self):
        r = translate("mobius", {"n": 30}, ModelStage.ECHO)
        assert "(-1)^3" in r  # 30 = 2×3×5, 3 distinct primes

    def test_stage1_mobius_squared_factor(self):
        r = translate("mobius", {"n": 4}, ModelStage.ECHO)
        assert "0" in r  # 4 = 2², squared factor

    def test_stage1_legendre(self):
        r = translate("legendre", {"a": 2, "p": 7}, ModelStage.ECHO)
        assert "quadratic residues" in r

    def test_stage1_modular_inverse(self):
        r = translate("modular_inverse", {"a": 3, "m": 7}, ModelStage.ECHO)
        assert "3^5" in r  # Fermat: 3^(7-2) mod 7

    def test_stage1_modular_inverse_no_inverse(self):
        r = translate("modular_inverse", {"a": 2, "m": 4}, ModelStage.ECHO)
        assert "no modular inverse" in r

    def test_stage1_cyclotomic(self):
        r = translate("cyclotomic_eval", {"n": 6, "x": 2.0}, ModelStage.ECHO)
        assert "product over d dividing 6" in r

    # -- Unknown task type ---------------------------------------------------

    def test_unknown_task_raises(self):
        with pytest.raises(ValueError, match="Unknown task_type"):
            translate("bogus_task", {}, ModelStage.ECHO)

    def test_unknown_task_stage4_raises(self):
        with pytest.raises(ValueError, match="Unknown task_type"):
            translate("bogus_task", {}, ModelStage.FULL)


# ========================================================================
# Stage Gradient Tests
# ========================================================================

class TestStageGradient:
    """Verify that the same task gets progressively more translated at lower stages."""

    def test_eisenstein_gradient(self):
        params = {"a": 2, "b": 3}
        r4 = translate("eisenstein_norm", params, ModelStage.FULL)
        r3 = translate("eisenstein_norm", params, ModelStage.CAPEABLE)
        r2 = translate("eisenstein_norm", params, ModelStage.META_ECHO)
        r1 = translate("eisenstein_norm", params, ModelStage.ECHO)

        # Stage 4 has domain vocab
        assert "Eisenstein" in r4
        # Stage 3 has domain vocab but ASCII notation
        assert "Eisenstein" in r3
        assert "²" not in r3
        # Stage 2 uses natural language
        assert "squared" in r2
        # Stage 1 is bare arithmetic
        assert "Eisenstein" not in r1
        assert "Compute:" in r1

    def test_mobius_gradient(self):
        params = {"n": 30}
        r4 = translate("mobius", params, ModelStage.FULL)
        r1 = translate("mobius", params, ModelStage.ECHO)

        assert "Möbius" in r4
        # Stage 1 should have pre-computed factorization
        assert "(-1)^3" in r1


# ========================================================================
# FleetRouter Tests
# ========================================================================

class TestFleetRouter:
    """Test the V2 router with stage-aware routing and batching."""

    def setup_method(self):
        self.router = FleetRouter()
        self.router.register("Seed-2.0-mini", ModelStage.FULL)
        self.router.register("hermes-405b", ModelStage.CAPEABLE)
        self.router.register("deepseek-chat", ModelStage.META_ECHO)
        self.router.register("tinyllama", ModelStage.ECHO)

    def test_route_full(self):
        p = self.router.route("Seed-2.0-mini", "eisenstein_norm", {"a": 3, "b": 5})
        assert "Eisenstein norm" in p

    def test_route_capable(self):
        p = self.router.route("hermes-405b", "eisenstein_norm", {"a": 3, "b": 5})
        assert "Eisenstein norm" in p
        assert "²" not in p

    def test_route_echo(self):
        p = self.router.route("tinyllama", "eisenstein_norm", {"a": 3, "b": 5})
        assert "Compute: 9" in p

    def test_route_meta_echo(self):
        p = self.router.route("deepseek-chat", "eisenstein_norm", {"a": 3, "b": 5})
        assert "squared" in p

    def test_unknown_model_defaults_capable(self):
        p = self.router.route("unknown-model", "eisenstein_norm", {"a": 1, "b": 1})
        assert "Eisenstein" in p  # Stage 3 gets activation key

    def test_log_entries(self):
        self.router.route("Seed-2.0-mini", "eisenstein_norm", {"a": 3, "b": 5})
        self.router.route("tinyllama", "eisenstein_norm", {"a": 3, "b": 5})
        assert len(self.router.log) == 2
        assert self.router.log[0].stage == ModelStage.FULL
        assert self.router.log[1].stage == ModelStage.ECHO

    def test_activation_key_logging(self):
        self.router.route("hermes-405b", "eisenstein_norm", {"a": 3, "b": 5})
        assert self.router.log[0].activation_key_injected is True

    def test_no_key_logging_for_stage1(self):
        self.router.route("tinyllama", "eisenstein_norm", {"a": 3, "b": 5})
        assert self.router.log[0].activation_key_injected is False

    def test_batch_routing(self):
        items = [
            ("eisenstein_norm", {"a": 1, "b": 0}),
            ("eisenstein_norm", {"a": 2, "b": 3}),
            ("mobius", {"n": 30}),
        ]
        results = self.router.route_batch("hermes-405b", items)
        assert len(results) == 3
        assert "Eisenstein" in results[0]
        assert "Eisenstein" in results[1]
        assert "Möbius" in results[2]

    def test_audit_summary(self):
        self.router.route("Seed-2.0-mini", "eisenstein_norm", {"a": 3, "b": 5})
        summary = self.router.audit_summary()
        assert "Total translations:" in summary
        assert "Fleet Auto-Translator V2" in summary

    def test_send_to_model_no_key_raises(self):
        with pytest.raises(RuntimeError, match="No DeepInfra API key"):
            self.router.send_to_model("test-model", "eisenstein_norm", {"a": 3, "b": 5})


# ========================================================================
# translate_for_stage (generic prompt) Tests
# ========================================================================

class TestTranslateForStage:
    """Test the generic translate_for_stage function."""

    def test_stage4_passthrough(self):
        r = translate_for_stage("Eisenstein norm: a²-ab+b²", ModelStage.FULL)
        assert r == "Eisenstein norm: a²-ab+b²"

    def test_stage3_normalizes_unicode(self):
        r = translate_for_stage("a²-ab+b²", ModelStage.CAPEABLE, "eisenstein_norm")
        assert "Eisenstein" in r  # key injected
        assert "²" not in r  # unicode normalized

    def test_stage2_natural_language(self):
        r = translate_for_stage("a²-ab+b²", ModelStage.META_ECHO, "eisenstein_norm")
        assert "Eisenstein" in r or "squared" in r

    def test_stage1_bare_arithmetic(self):
        r = translate_for_stage("Compute the Eisenstein norm of a=3, b=1", ModelStage.ECHO)
        assert "Eisenstein" not in r


# ========================================================================
# Known Stages Registry Tests
# ========================================================================

class TestKnownStages:
    """Test the built-in model stage registry."""

    def test_seed_mini_is_full(self):
        assert KNOWN_STAGES["ByteDance/Seed-2.0-mini"] == ModelStage.FULL

    def test_seed_code_is_full(self):
        assert KNOWN_STAGES["ByteDance/Seed-2.0-code"] == ModelStage.FULL

    def test_hermes_405b_is_capable(self):
        assert KNOWN_STAGES["NousResearch/Hermes-3-Llama-3.1-405B"] == ModelStage.CAPEABLE

    def test_deepseek_chat_is_meta_echo(self):
        assert KNOWN_STAGES["deepseek-chat"] == ModelStage.META_ECHO

    def test_router_uses_known_stages(self):
        router = FleetRouter()
        assert router.get_stage("ByteDance/Seed-2.0-mini") == ModelStage.FULL
        assert router.get_stage("NousResearch/Hermes-3-Llama-3.1-70B") == ModelStage.CAPEABLE


# ========================================================================
# Live API Tests (require DEEPINFRA_KEY)
# ========================================================================

@pytest.fixture
def deepinfra_key():
    key_path = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    if not os.path.exists(key_path):
        pytest.skip("DeepInfra API key not found")
    with open(key_path) as f:
        return f.read().strip()


@pytest.mark.live
class TestLiveAPI:
    """Live tests against DeepInfra models. Run with: pytest -m live"""

    def test_seed_mini_eisenstein(self, deepinfra_key):
        """Seed-2.0-mini (Stage 4) should handle Eisenstein norm directly."""
        router = FleetRouter(deepinfra_key=deepinfra_key)
        router.register("ByteDance/Seed-2.0-mini", ModelStage.FULL)
        resp = router.send_to_model(
            "ByteDance/Seed-2.0-mini",
            "eisenstein_norm",
            {"a": 1, "b": 0},
            temperature=0.0,
        )
        content = resp["choices"][0]["message"]["content"].lower()
        # Should compute Eisenstein norm(1,0) = 1
        assert "1" in content

    def test_hermes_eisenstein_with_key(self, deepinfra_key):
        """Hermes (Stage 3) should get activation key injection."""
        router = FleetRouter(deepinfra_key=deepinfra_key)
        router.register("NousResearch/Hermes-3-Llama-3.1-70B", ModelStage.CAPEABLE)
        resp = router.send_to_model(
            "NousResearch/Hermes-3-Llama-3.1-70B",
            "eisenstein_norm",
            {"a": 2, "b": 1},
            temperature=0.0,
        )
        content = resp["choices"][0]["message"]["content"].lower()
        # Eisenstein norm(2,1) = 4-2+1 = 3
        assert "3" in content

    def test_stage_gradient_eisenstein(self, deepinfra_key):
        """Compare accuracy across stages for Eisenstein norm(2,1)=3."""
        router = FleetRouter(deepinfra_key=deepinfra_key)
        params = {"a": 2, "b": 1}

        models = [
            ("ByteDance/Seed-2.0-mini", ModelStage.FULL),
            ("NousResearch/Hermes-3-Llama-3.1-70B", ModelStage.CAPEABLE),
        ]

        results = {}
        for model_id, stage in models:
            router.register(model_id, stage)
            try:
                resp = router.send_to_model(model_id, "eisenstein_norm", params, temperature=0.0)
                content = resp["choices"][0]["message"]["content"]
                results[model_id] = content
                print(f"\n{model_id}: {content[:200]}")
            except Exception as e:
                results[model_id] = f"ERROR: {e}"

        # At minimum, Seed-2.0-mini should get it right (Stage 4)
        seed_result = results.get("ByteDance/Seed-2.0-mini", "")
        assert "3" in seed_result.lower(), f"Seed-2.0-mini failed: {seed_result}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", *sys.argv[1:]])
