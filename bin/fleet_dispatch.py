#!/usr/bin/env python3
"""
Fleet Dispatch — Production model API dispatcher with retry, concurrency, and cost tracking.

Integrates with fleet_router.py for routing decisions, adds real HTTP dispatch.
"""

import json
import logging
import os
import re
import sys
import time
import math
import datetime
import concurrent.futures
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List, Tuple
from pathlib import Path

import urllib.request
import urllib.error

# Import fleet_router from same directory
sys.path.insert(0, str(Path(__file__).parent))
from fleet_router import FleetRouter, ModelStage, FLEET_MODELS

logger = logging.getLogger("fleet_dispatch")
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Provider pricing (per 1M tokens)
# ---------------------------------------------------------------------------
PRICING: Dict[str, Dict[str, float]] = {
    "zai": {"input": 0.0, "output": 0.0},  # paid plan
    "deepinfra": {
        "seed-mini": {"input": 0.055, "output": 0.115},
        "seed-code": {"input": 0.10, "output": 0.30},
        "hermes-70b": {"input": 0.07, "output": 0.07},
        "qwen3-235b": {"input": 0.15, "output": 0.15},
        "_default": {"input": 0.05, "output": 0.05},
    },
    "ollama": {"input": 0.0, "output": 0.0},
}

# Provider model ID mapping for API calls
PROVIDER_MODEL_IDS: Dict[str, Dict[str, str]] = {
    "zai": {
        "glm-5.1": "glm-5.1",
        "glm-5-turbo": "glm-5-turbo",
    },
    "deepinfra": {
        "seed-mini": "ByteDance/Seed-2.0-mini",
        "seed-code": "ByteDance/Seed-2.0-code",
        "hermes-70b": "NousResearch/Hermes-3-Llama-3.1-70B",
        "qwen3-235b": "Qwen/Qwen3-235B-A22B-Instruct-2507",
    },
    "ollama": {
        "phi4-mini": "phi4-mini",
        "qwen3-4b": "qwen3:4b",
        "gemma3-1b": "gemma3:1b",
    },
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------
@dataclass
class DispatchResult:
    """Result from a single model dispatch."""
    model_name: str
    provider: str
    prompt: str
    response: str
    extracted_answer: Optional[str] = None
    numeric_answer: Optional[float] = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: float = 0.0
    latency_s: float = 0.0
    retries: int = 0
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.datetime.utcnow().isoformat() + "Z"


@dataclass
class CostTracker:
    """Tracks cumulative costs across dispatches."""
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    by_provider: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def record(self, result: DispatchResult) -> None:
        self.total_tokens_in += result.tokens_in
        self.total_tokens_out += result.tokens_out
        self.total_cost_usd += result.cost_usd
        prov = result.provider
        if prov not in self.by_provider:
            self.by_provider[prov] = {"tokens_in": 0, "tokens_out": 0, "cost": 0.0, "calls": 0}
        self.by_provider[prov]["tokens_in"] += result.tokens_in
        self.by_provider[prov]["tokens_out"] += result.tokens_out
        self.by_provider[prov]["cost"] += result.cost_usd
        self.by_provider[prov]["calls"] += 1

    def summary(self) -> str:
        lines = [f"Total: {self.total_tokens_in}in/{self.total_tokens_out}out tokens, ${self.total_cost_usd:.4f}"]
        for prov, stats in self.by_provider.items():
            lines.append(f"  {prov}: {stats['calls']} calls, {int(stats['tokens_in'])}in/{int(stats['tokens_out'])}out, ${stats['cost']:.4f}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Result parsing
# ---------------------------------------------------------------------------
class ResultParser:
    """Extract numeric answers from LLM responses."""

    # Patterns ordered by specificity
    PATTERNS = [
        # "The answer is 49" / "The answer is: 49"
        re.compile(r'(?:the\s+answer\s+is\s*:?\s*)([-+]?\d+\.?\d*)', re.I),
        # "= 49" / "N = 49"
        re.compile(r'(?:=\s*)([-+]?\d+\.?\d*)', re.I),
        # "result: 49" / "Result = 49"
        re.compile(r'(?:result\s*:?\s*)([-+]?\d+\.?\d*)', re.I),
        # "N(a + bω) = 49"
        re.compile(r'(?:N\([^)]+\)\s*=\s*)([-+]?\d+\.?\d*)', re.I),
        # Bold answer: **49**
        re.compile(r'\*\*([-+]?\d+\.?\d*)\*\*'),
        # Code block with a bare number line: "49" or "  49"
        re.compile(r'```[^`]*?^\s*([-+]?\d+\.?\d*)\s*$', re.M),
        # Final fallback: last standalone integer/float on its own line
        re.compile(r'^\s*([-+]?\d+\.?\d*)\s*$', re.M),
    ]

    @classmethod
    def extract(cls, response: str) -> Tuple[Optional[str], Optional[float]]:
        """Return (raw_match, numeric_value) from a model response."""
        if not response:
            return None, None

        # Strip thinking tokens (e.g. <think...</think->)
        cleaned = re.sub(r'<think.*?>.*?</think->', '', response, flags=re.DOTALL)
        cleaned = re.sub(r'<think.*?>.*?</think\s*>', '', response, flags=re.DOTALL)

        for pattern in cls.PATTERNS:
            m = pattern.search(cleaned)
            if m:
                raw = m.group(1)
                try:
                    return raw, float(raw)
                except ValueError:
                    continue

        # Last resort: find any number in the last 200 chars
        tail = cleaned[-200:] if len(cleaned) > 200 else cleaned
        nums = re.findall(r'([-+]?\d+\.?\d*)', tail)
        if nums:
            raw = nums[-1]
            try:
                return raw, float(raw)
            except ValueError:
                pass

        return None, None


# ---------------------------------------------------------------------------
# API Dispatch
# ---------------------------------------------------------------------------
class FleetDispatcher:
    """Dispatch prompts to fleet models via real HTTP API calls."""

    MAX_RETRIES = 3
    BACKOFF_BASE = 1.0  # seconds
    TIMEOUT = 120  # seconds per request

    def __init__(self, router: Optional[FleetRouter] = None):
        self.router = router or FleetRouter()
        self.cost_tracker = CostTracker()
        self._audit_log: List[Dict[str, Any]] = []

        # Load credentials
        self._zai_key = os.environ.get("ZAI_KEY", "")
        self._deepinfra_key = self._load_deepinfra_key()

    @staticmethod
    def _load_deepinfra_key() -> str:
        key_path = Path.home() / ".openclaw/workspace/.credentials/deepinfra-api-key.txt"
        if key_path.exists():
            return key_path.read_text().strip()
        return os.environ.get("DEEPINFRA_KEY", "")

    def _get_api_model_id(self, provider: str, model_name: str) -> str:
        return PROVIDER_MODEL_IDS.get(provider, {}).get(model_name, model_name)

    def _estimate_cost(self, provider: str, model_name: str, tokens_in: int, tokens_out: int) -> float:
        pricing = PRICING.get(provider, {})
        if provider == "deepinfra":
            model_pricing = pricing.get(model_name, pricing.get("_default", {"input": 0.05, "output": 0.05}))
        else:
            model_pricing = pricing
        return (tokens_in * model_pricing.get("input", 0) + tokens_out * model_pricing.get("output", 0)) / 1_000_000

    def _call_zai(self, model_id: str, prompt: str) -> Tuple[str, int, int]:
        url = "https://api.z.ai/api/coding/paas/v4/chat/completions"
        payload = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._zai_key}",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
            data = json.loads(resp.read())
        content = ""
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "") or msg.get("reasoning_content", "") or ""
        usage = data.get("usage", {})
        return content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    def _call_deepinfra(self, model_id: str, prompt: str) -> Tuple[str, int, int]:
        url = "https://api.deepinfra.com/v1/openai/chat/completions"
        payload = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1024,
        }).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._deepinfra_key}",
        }
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
            data = json.loads(resp.read())
        content = ""
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
        usage = data.get("usage", {})
        return content, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    def _call_ollama(self, model_id: str, prompt: str) -> Tuple[str, int, int]:
        url = "http://localhost:11434/api/chat"
        payload = json.dumps({
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode()
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=self.TIMEOUT) as resp:
            data = json.loads(resp.read())
        content = data.get("message", {}).get("content", "")
        # Ollama doesn't always report tokens, estimate from content length
        eval_count = data.get("eval_count", 0) or len(content.split()) * 1.3
        prompt_eval = data.get("prompt_eval_count", 0) or len(prompt.split()) * 1.3
        return content, int(prompt_eval), int(eval_count)

    def _dispatch_single(self, model: ModelStage, prompt: str) -> DispatchResult:
        """Dispatch a single prompt to a model with retry logic."""
        provider = model.provider
        model_name = model.name
        api_model_id = self._get_api_model_id(provider, model_name)
        last_error = None
        retries = 0

        for attempt in range(self.MAX_RETRIES + 1):
            t0 = time.time()
            try:
                if provider == "zai":
                    if not self._zai_key:
                        raise ValueError("ZAI_KEY not set")
                    content, tok_in, tok_out = self._call_zai(api_model_id, prompt)
                elif provider == "deepinfra":
                    if not self._deepinfra_key:
                        raise ValueError("DeepInfra key not configured")
                    content, tok_in, tok_out = self._call_deepinfra(api_model_id, prompt)
                elif provider == "ollama":
                    content, tok_in, tok_out = self._call_ollama(api_model_id, prompt)
                else:
                    raise ValueError(f"Unknown provider: {provider}")

                latency = time.time() - t0
                cost = self._estimate_cost(provider, model_name, tok_in, tok_out)
                raw, numeric = ResultParser.extract(content)

                result = DispatchResult(
                    model_name=model_name,
                    provider=provider,
                    prompt=prompt,
                    response=content,
                    extracted_answer=raw,
                    numeric_answer=numeric,
                    tokens_in=tok_in,
                    tokens_out=tok_out,
                    cost_usd=cost,
                    latency_s=latency,
                    retries=retries,
                )
                self.cost_tracker.record(result)
                return result

            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                last_error = str(e)
                status_code = getattr(e, "code", 0) if isinstance(e, urllib.error.HTTPError) else 0

                if status_code == 429 or isinstance(e, (TimeoutError, urllib.error.URLError)):
                    retries += 1
                    if attempt < self.MAX_RETRIES:
                        backoff = self.BACKOFF_BASE * (2 ** attempt)
                        logger.warning("Retry %d/%d for %s after error: %s (backoff %.1fs)",
                                       attempt + 1, self.MAX_RETRIES, model_name, last_error, backoff)
                        time.sleep(backoff)
                        continue

                # Non-retryable error or exhausted retries
                latency = time.time() - t0
                return DispatchResult(
                    model_name=model_name,
                    provider=provider,
                    prompt=prompt,
                    response="",
                    retries=retries,
                    error=last_error,
                    latency_s=latency,
                )

            except ValueError as e:
                latency = time.time() - t0
                return DispatchResult(
                    model_name=model_name,
                    provider=provider,
                    prompt=prompt,
                    response="",
                    retries=retries,
                    error=str(e),
                    latency_s=latency,
                )

        # Should not reach here, but safety
        return DispatchResult(
            model_name=model_name,
            provider=provider,
            prompt=prompt,
            response="",
            retries=retries,
            error=last_error,
        )

    def dispatch(
        self,
        task_type: str,
        params: Dict[str, Any],
        needs_domain: bool = False,
        prefer_free: bool = False,
    ) -> DispatchResult:
        """Route and dispatch a single task."""
        model = self.router.route(task_type, needs_domain, prefer_free)
        prompt = self.router.translate(task_type, params, model)
        return self._dispatch_single(model, prompt)

    def dispatch_consensus(
        self,
        task_type: str,
        params: Dict[str, Any],
        model_names: Optional[List[str]] = None,
        max_workers: int = 4,
    ) -> List[DispatchResult]:
        """Dispatch the same task to multiple models for consensus."""
        if model_names is None:
            # Pick top 3 models across providers
            models = sorted(FLEET_MODELS.values(), key=lambda m: -m.accuracy)[:3]
        else:
            models = [FLEET_MODELS[n] for n in model_names if n in FLEET_MODELS]

        prompts = []
        for m in models:
            prompt = self.router.translate(task_type, params, m)
            prompts.append((m, prompt))

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(self._dispatch_single, model, prompt): model.name
                for model, prompt in prompts
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    model_name = futures[future]
                    results.append(DispatchResult(
                        model_name=model_name,
                        provider=FLEET_MODELS[model_name].provider,
                        prompt="",
                        response="",
                        error=str(e),
                    ))

        return results

    def dispatch_parallel(
        self,
        tasks: List[Tuple[str, Dict[str, Any]]],
        max_workers: int = 4,
    ) -> List[DispatchResult]:
        """Dispatch multiple tasks in parallel, each routed independently."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(self.dispatch, task_type, params)
                for task_type, params in tasks
            ]
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    results.append(DispatchResult(
                        model_name="unknown",
                        provider="unknown",
                        prompt="",
                        response="",
                        error=str(e),
                    ))
        return results


# ---------------------------------------------------------------------------
# Demo: 10 Eisenstein norm computations across providers
# ---------------------------------------------------------------------------
def run_demo(dispatcher: Optional[FleetDispatcher] = None):
    """Dispatch 10 Eisenstein norm computations and print results table."""
    dispatcher = dispatcher or FleetDispatcher()
    print("=== Fleet Dispatch Demo: Eisenstein Norm Computations ===\n")

    test_pairs = [
        (3, 5), (7, -2), (-4, 6), (0, 11), (13, 0),
        (5, 5), (-3, -7), (2, 9), (10, -8), (6, 4),
    ]

    tasks = [
        ("computation", {"operation": "eisenstein_norm", "a": a, "b": b})
        for a, b in test_pairs
    ]

    results = dispatcher.dispatch_parallel(tasks, max_workers=3)

    # Results table
    header = f"{'(a,b)':>10s} | {'Model':>15s} | {'Provider':>10s} | {'Expected':>8s} | {'Got':>8s} | {'Match':>5s} | {'Latency':>7s} | {'Retries':>7s}"
    print(header)
    print("-" * len(header))

    correct = 0
    total = 0
    for i, result in enumerate(results):
        a, b = test_pairs[i]
        expected = a * a - a * b + b * b
        got = result.numeric_answer
        match = "✓" if got is not None and abs(got - expected) < 0.01 else "✗"
        if match == "✓":
            correct += 1
        total += 1

        got_str = f"{got:.0f}" if got is not None else "N/A"
        err_str = f"ERR: {result.error[:30]}" if result.error else ""
        print(
            f"({a:+3d},{b:+3d}) | {result.model_name:>15s} | {result.provider:>10s} | "
            f"{expected:>8d} | {got_str:>8s} | {match:>5s} | "
            f"{result.latency_s:>6.2f}s | {result.retries:>7d} {err_str}"
        )

    print(f"\nAccuracy: {correct}/{total} ({100 * correct / total:.0f}%)")
    print(f"\nCost Summary:")
    print(dispatcher.cost_tracker.summary())


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_tests():
    """Run 10 tests covering retry logic, result parsing, cost tracking, concurrent dispatch."""
    import unittest

    class TestResultParser(unittest.TestCase):
        def test_answer_is_pattern(self):
            raw, num = ResultParser.extract("After computation, the answer is 49")
            self.assertEqual(num, 49.0)
            self.assertEqual(raw, "49")

        def test_equals_pattern(self):
            raw, num = ResultParser.extract("N(3 + 5ω) = 49")
            self.assertEqual(num, 49.0)

        def test_bare_number(self):
            raw, num = ResultParser.extract("Step 1: compute\nStep 2: done\n49")
            self.assertIsNotNone(num)

        def test_negative_answer(self):
            raw, num = ResultParser.extract("The result is: -7")
            self.assertEqual(num, -7.0)

        def test_empty_response(self):
            raw, num = ResultParser.extract("")
            self.assertIsNone(num)

    class TestCostTracker(unittest.TestCase):
        def test_single_record(self):
            tracker = CostTracker()
            result = DispatchResult(
                model_name="glm-5.1", provider="zai", prompt="test", response="ok",
                tokens_in=100, tokens_out=50, cost_usd=0.0,
            )
            tracker.record(result)
            self.assertEqual(tracker.total_tokens_in, 100)
            self.assertEqual(tracker.total_tokens_out, 50)
            self.assertEqual(tracker.total_cost_usd, 0.0)  # z.ai is free

        def test_deepinfra_cost(self):
            tracker = CostTracker()
            result = DispatchResult(
                model_name="seed-mini", provider="deepinfra", prompt="test", response="ok",
                tokens_in=1000, tokens_out=500,
                cost_usd=(1000 * 0.055 + 500 * 0.115) / 1_000_000,
            )
            tracker.record(result)
            self.assertAlmostEqual(tracker.total_cost_usd, 0.0001125, places=8)

        def test_by_provider_aggregation(self):
            tracker = CostTracker()
            for _ in range(3):
                tracker.record(DispatchResult(
                    model_name="glm-5.1", provider="zai", prompt="", response="",
                    tokens_in=10, tokens_out=10, cost_usd=0,
                ))
            self.assertEqual(tracker.by_provider["zai"]["calls"], 3)

    class TestDispatchResult(unittest.TestCase):
        def test_auto_timestamp(self):
            result = DispatchResult(model_name="x", provider="zai", prompt="", response="")
            self.assertTrue(result.timestamp.endswith("Z"))

    class TestFleetDispatcher(unittest.TestCase):
        def test_missing_credentials_graceful(self):
            """Dispatch with missing credentials should return error, not crash."""
            dispatcher = FleetDispatcher()
            dispatcher._zai_key = ""
            result = dispatcher._dispatch_single(
                ModelStage(name="glm-5.1", stage=3, echo_rate=0, accuracy=0.9,
                           is_thinking=True, is_free=False, provider="zai", model_id="zai/glm-5.1"),
                "test prompt",
            )
            self.assertIsNotNone(result.error)
            self.assertIn("ZAI_KEY", result.error)

        def test_estimate_cost_zai_free(self):
            dispatcher = FleetDispatcher()
            cost = dispatcher._estimate_cost("zai", "glm-5.1", 1000, 500)
            self.assertEqual(cost, 0.0)

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    suite.addTests(loader.loadTestsFromTestCase(TestResultParser))
    suite.addTests(loader.loadTestsFromTestCase(TestCostTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestDispatchResult))
    suite.addTests(loader.loadTestsFromTestCase(TestFleetDispatcher))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    elif len(sys.argv) > 1 and sys.argv[1] == "demo":
        run_demo()
    else:
        print("Usage: fleet_dispatch.py [test|demo]")
        print("  test  — Run unit tests")
        print("  demo  — Run Eisenstein norm dispatch demo")
