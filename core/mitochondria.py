#!/usr/bin/env python3
"""
Mitochondrial Benchmarking System — Concrete model profiling and comparison.

Not metaphor. This measures which models are fast/cheap/available (mitochondrial)
vs slow/expensive/powerful (nuclear), then runs head-to-head comparisons.

The Incubator uses mitochondrial models for rapid exploration and nuclear models
for heavy reasoning, with comparison as the developmental signal.
"""

import json
import time
import statistics
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple

# ─── Thresholds ───────────────────────────────────────────────────────────────

MITO_LATENCY_MS = 5000       # <5s is mitochondrial
MITO_COST_PER_1K = 0.01      # <$0.01/1k tokens is mitochondrial
MITO_RELIABILITY = 0.85      # >85% success rate required

# ─── API Endpoints ────────────────────────────────────────────────────────────

DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
ZAI_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
# Note: z.ai endpoint may require different auth; fallback to DeepInfra nuclear models


# ─── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class ModelProfile:
    """Concrete profile of a model's mitochondrial vs nuclear characteristics."""
    model_id: str
    provider: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    cost_per_1k_tokens: float
    reliability: float  # success rate 0-1
    is_mitochondrial: bool
    tokens_per_second: float = 0.0
    avg_output_tokens: float = 0.0
    sample_responses: List[str] = field(default_factory=list)

    def summary(self) -> str:
        kind = "MITOCHONDRIAL ⚡" if self.is_mitochondrial else "NUCLEAR ☢️"
        return (
            f"[{kind}] {self.model_id} ({self.provider})\n"
            f"  Latency: avg={self.avg_latency_ms:.0f}ms p50={self.p50_latency_ms:.0f}ms p95={self.p95_latency_ms:.0f}ms\n"
            f"  Throughput: {self.tokens_per_second:.1f} tok/s\n"
            f"  Cost: ${self.cost_per_1k_tokens:.4f}/1k tokens\n"
            f"  Reliability: {self.reliability:.0%}\n"
            f"  Avg output: {self.avg_output_tokens:.0f} tokens"
        )


@dataclass
class ComparisonPoint:
    """Single comparison between nuclear and mitochondrial on one prompt."""
    prompt: str
    nuclear_response: str
    mito_response: str
    nuclear_latency_ms: float
    mito_latency_ms: float
    agreement_score: float  # 0-1, how similar the responses are
    category: str  # "agreement", "divergence", "mito_wins", "mito_failure"


@dataclass
class ComparisonReport:
    """Conscious comparison between nuclear and mitochondrial model."""
    nuclear_profile: ModelProfile
    mito_profile: ModelProfile
    agreements: List[ComparisonPoint] = field(default_factory=list)
    divergences: List[ComparisonPoint] = field(default_factory=list)
    mito_wins: List[ComparisonPoint] = field(default_factory=list)
    mito_failures: List[ComparisonPoint] = field(default_factory=list)

    def summary(self) -> str:
        total = len(self.agreements) + len(self.divergences) + len(self.mito_wins) + len(self.mito_failures)
        return (
            f"═══ COMPARISON REPORT ═══\n"
            f"  Nuclear: {self.nuclear_profile.model_id}\n"
            f"  Mito:    {self.mito_profile.model_id}\n"
            f"  Total prompts: {total}\n"
            f"  ✅ Agreements:    {len(self.agreements)} (convergence = high confidence)\n"
            f"  ⚠️  Divergences:   {len(self.divergences)} (signal about difficulty)\n"
            f"  🏆 Mito wins:     {len(self.mito_wins)} (mitochondrial specialization)\n"
            f"  💀 Mito failures:  {len(self.mito_failures)} (operating envelope)\n"
        )


@dataclass
class EmbryoState:
    """State of a developing task through the incubator."""
    task: str
    stage: str  # "zygote", "morula", "blastula", "gastrula", "organogenesis", "fledged"
    mito_explorations: List[Dict] = field(default_factory=list)
    convergence_zones: List[str] = field(default_factory=list)
    divergence_points: List[str] = field(default_factory=list)
    nuclear_interventions: List[Dict] = field(default_factory=list)
    final_output: Optional[str] = None
    total_mito_calls: int = 0
    total_nuclear_calls: int = 0
    total_cost: float = 0.0


# ─── API Layer ────────────────────────────────────────────────────────────────

def _call_api(url: str, api_key: str, model: str, messages: List[Dict],
              max_tokens: int = 256, temperature: float = 0.3,
              timeout: float = 30.0) -> Tuple[Optional[str], float, int]:
    """Make an API call. Returns (response_text, latency_ms, output_tokens) or (None, latency, 0)."""
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }).encode()

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    start = time.time()
    try:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            elapsed_ms = (time.time() - start) * 1000
            text = body.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = body.get("usage", {})
            out_tokens = usage.get("completion_tokens", len(text.split()))
            return text, elapsed_ms, out_tokens
    except Exception as e:
        elapsed_ms = (time.time() - start) * 1000
        return None, elapsed_ms, 0


def _similarity(s1: str, s2: str) -> float:
    """Rough text similarity score based on token overlap."""
    if not s1 or not s2:
        return 0.0
    words1 = set(s1.lower().split())
    words2 = set(s2.lower().split())
    if not words1 or not words2:
        return 0.0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)


def _extract_json_or_code(text: str) -> Optional[str]:
    """Try to extract a JSON block or code block from text."""
    import re
    # Try code block first
    m = re.search(r'```(?:json)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Try raw JSON
    m = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


# ─── MitochondrialBenchmark ──────────────────────────────────────────────────

class MitochondrialBenchmark:
    """Benchmark suite for mitochondrial fitness."""

    def __init__(self, deepinfra_key: str, zai_key: str):
        self.deepinfra_key = deepinfra_key
        self.zai_key = zai_key

    def _get_endpoint_and_key(self, model_id: str) -> Tuple[str, str]:
        if "ByteDance/" in model_id or "Qwen/" in model_id or "NousResearch/" in model_id:
            return DEEPINFRA_URL, self.deepinfra_key
        else:
            return ZAI_URL, self.zai_key

    def profile_model(self, model_id: str, provider: str, n_trials: int = 10) -> ModelProfile:
        """Profile a model through repeated inference calls."""
        url, api_key = self._get_endpoint_and_key(model_id)

        # Cost lookup (approximate)
        cost_map = {
            "ByteDance/Seed-2.0-mini": 0.001,
            "ByteDance/Seed-2.0-code": 0.002,
            "Qwen/Qwen3-235B-A22B": 0.005,
            "glm-5.1": 0.02,
            "glm-5-turbo": 0.015,
            "glm-4.7": 0.01,
            "glm-4.7-flash": 0.005,
        }
        cost = cost_map.get(model_id, 0.01)

        # Standardized profiling prompts
        profile_prompts = [
            "Respond with exactly: {\"status\": \"ok\", \"count\": 42}",
            "What is 17 * 23? Respond with just the number.",
            "Write a Python function that reverses a string. Only output code.",
            "List 3 colors. JSON format: {\"colors\": [...]}",
            "What is the capital of France? One word answer.",
        ]

        latencies = []
        successes = 0
        output_tokens = []
        responses = []

        for i in range(n_trials):
            prompt = profile_prompts[i % len(profile_prompts)]
            messages = [{"role": "user", "content": prompt}]
            text, latency_ms, tokens = _call_api(url, api_key, model_id, messages,
                                                  max_tokens=128, temperature=0.1, timeout=25.0)
            latencies.append(latency_ms)
            if text is not None:
                successes += 1
                output_tokens.append(tokens)
                responses.append(text[:200])
            else:
                output_tokens.append(0)
                responses.append("[FAILED]")

        avg_latency = statistics.mean(latencies)
        sorted_lat = sorted(latencies)
        p50 = sorted_lat[len(sorted_lat) // 2]
        p95 = sorted_lat[int(len(sorted_lat) * 0.95)]
        reliability = successes / n_trials
        avg_tokens = statistics.mean(output_tokens) if output_tokens else 0

        # Tokens per second estimate
        tps = (avg_tokens / (avg_latency / 1000)) if avg_latency > 0 else 0

        is_mito = (avg_latency < MITO_LATENCY_MS and
                   cost < MITO_COST_PER_1K and
                   reliability > MITO_RELIABILITY)

        return ModelProfile(
            model_id=model_id,
            provider=provider,
            avg_latency_ms=avg_latency,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            cost_per_1k_tokens=cost,
            reliability=reliability,
            is_mitochondrial=is_mito,
            tokens_per_second=tps,
            avg_output_tokens=avg_tokens,
            sample_responses=responses[:3],
        )

    def fitness_score(self, profile: ModelProfile) -> float:
        """Score 0-1: how good is this mitochondria?

        Weighted combination of speed, cost, reliability, and throughput.
        """
        if not profile.is_mitochondrial:
            return 0.0

        # Speed score (faster = better, diminishing returns below 500ms)
        speed_score = min(1.0, 500.0 / max(profile.avg_latency_ms, 1.0))

        # Cost score (cheaper = better)
        cost_score = min(1.0, 0.001 / max(profile.cost_per_1k_tokens, 0.0001))

        # Reliability score
        rel_score = profile.reliability

        # Throughput score
        tps_score = min(1.0, profile.tokens_per_second / 100.0)

        return 0.3 * speed_score + 0.2 * cost_score + 0.3 * rel_score + 0.2 * tps_score

    def run_comparison(self, nuclear_model: str, mito_model: str,
                       test_prompts: List[str]) -> ComparisonReport:
        """Run head-to-head comparison on test prompts."""
        nuc_url, nuc_key = self._get_endpoint_and_key(nuclear_model)
        mito_url, mito_key = self._get_endpoint_and_key(mito_model)

        # Quick profile each
        nuc_profile = self.profile_model(nuclear_model, "nuclear", n_trials=3)
        mito_profile = self.profile_model(mito_model, "mitochondrial", n_trials=3)

        report = ComparisonReport(nuclear_profile=nuc_profile, mito_profile=mito_profile)

        for prompt in test_prompts:
            messages = [{"role": "user", "content": prompt}]

            nuc_text, nuc_lat, nuc_tok = _call_api(nuc_url, nuc_key, nuclear_model,
                                                     messages, max_tokens=256, temperature=0.2, timeout=30.0)
            mito_text, mito_lat, mito_tok = _call_api(mito_url, mito_key, mito_model,
                                                        messages, max_tokens=256, temperature=0.2, timeout=25.0)

            nuc_text = nuc_text or "[TIMEOUT/ERROR]"
            mito_text = mito_text or "[TIMEOUT/ERROR]"

            sim = _similarity(nuc_text, mito_text)

            cp = ComparisonPoint(
                prompt=prompt,
                nuclear_response=nuc_text[:300],
                mito_response=mito_text[:300],
                nuclear_latency_ms=nuc_lat,
                mito_latency_ms=mito_lat,
                agreement_score=sim,
                category="agreement",
            )

            # Classify
            if mito_text == "[TIMEOUT/ERROR]":
                cp.category = "mito_failure"
                report.mito_failures.append(cp)
            elif sim > 0.5:
                cp.category = "agreement"
                report.agreements.append(cp)
            elif sim < 0.2:
                cp.category = "divergence"
                report.divergences.append(cp)
            elif mito_lat < nuc_lat * 0.5 and sim > 0.3:
                # Mito was much faster and still somewhat accurate → mito win
                cp.category = "mito_wins"
                report.mito_wins.append(cp)
            else:
                cp.category = "divergence"
                report.divergences.append(cp)

        return report


# ─── Incubator ────────────────────────────────────────────────────────────────

class Incubator:
    """Provisions mitochondrial energy to developing agents.

    Biological analogy (but concrete system):
    - Bootstrap: mitochondrial models rapidly explore task space (cheap, fast)
    - Develop: compare mito outputs, find convergence, bring in nuclear for hard parts
    - Fledge: nuclear takes developed context, produces final output
    """

    def __init__(self, mito_models: List[str], nuclear_models: List[str],
                 deepinfra_key: str, zai_key: str):
        self.mito_models = mito_models
        self.nuclear_models = nuclear_models
        self.deepinfra_key = deepinfra_key
        self.zai_key = zai_key

    def _call(self, model: str, messages: List[Dict], max_tokens: int = 256,
              temperature: float = 0.3, timeout: float = 25.0) -> Tuple[Optional[str], float]:
        if any(k in model for k in ["ByteDance", "Qwen", "NousResearch"]):
            url, key = DEEPINFRA_URL, self.deepinfra_key
        else:
            url, key = ZAI_URL, self.zai_key
        text, lat, _ = _call_api(url, key, model, messages, max_tokens, temperature, timeout)
        return text, lat

    def bootstrap(self, task: str) -> EmbryoState:
        """Stage 1: Rapid mitochondrial exploration of the task."""
        state = EmbryoState(task=task, stage="zygote")

        # Each mito model takes a different angle
        angles = [
            f"Analyze this task and list the key sub-problems: {task}",
            f"What are the edge cases and failure modes for: {task}",
            f"What is the simplest possible solution for: {task}",
        ]

        for i, model in enumerate(self.mito_models):
            angle = angles[i % len(angles)]
            messages = [{"role": "user", "content": angle}]
            text, lat = self._call(model, messages, max_tokens=400, temperature=0.5, timeout=40.0)
            state.total_mito_calls += 1
            state.total_cost += 0.001  # approximate
            state.mito_explorations.append({
                "model": model,
                "angle": ["sub-problems", "edge-cases", "simplest"][i % 3],
                "response": (text or "[FAILED]")[:300],
                "latency_ms": lat,
            })

        state.stage = "morula"
        return state

    def develop(self, state: EmbryoState, n_cycles: int = 3) -> EmbryoState:
        """Stage 2: Compare mito outputs, identify convergence/divergence, nuclear intervention."""
        state.stage = "blastula"

        # Extract key themes from mito explorations
        all_responses = [e["response"] for e in state.mito_explorations]

        # Find convergence: words appearing in multiple responses
        word_counts: Dict[str, int] = {}
        for resp in all_responses:
            seen = set(resp.lower().split())
            for w in seen:
                word_counts[w] = word_counts.get(w, 0) + 1

        convergence_words = [w for w, c in word_counts.items() if c >= 2 and len(w) > 4]
        state.convergence_zones = convergence_words[:10]

        # For each development cycle, go deeper
        for cycle in range(n_cycles):
            state.stage = ["blastula", "gastrula", "organogenesis"][min(cycle, 2)]

            # Mito: drill into convergence zones
            if convergence_words:
                focus = ", ".join(convergence_words[:5])
                mito_prompt = (
                    f"Given the task '{state.task}', and key areas: {focus}.\n"
                    f"Provide a specific, actionable approach. Be concise."
                )
            else:
                mito_prompt = f"For the task '{state.task}', provide a concrete approach."

            for model in self.mito_models:
                text, lat = self._call(model, [{"role": "user", "content": mito_prompt}],
                                        max_tokens=400, temperature=0.4, timeout=40.0)
                state.total_mito_calls += 1
                state.mito_explorations.append({
                    "model": model,
                    "angle": f"develop-cycle-{cycle}",
                    "response": (text or "[FAILED]")[:300],
                    "latency_ms": lat,
                })

            # Nuclear: resolve divergences
            nuc_prompt = (
                f"Task: {state.task}\n"
                f"Exploration so far: {'; '.join(all_responses[-2:])}\n"
                f"What is the correct approach? Identify any errors in the exploration."
            )
            for model in self.nuclear_models:
                text, lat = self._call(model, [{"role": "user", "content": nuc_prompt}],
                                        max_tokens=300, temperature=0.2, timeout=35.0)
                state.total_nuclear_calls += 1
                state.total_cost += 0.01
                if text:
                    state.nuclear_interventions.append({
                        "model": model,
                        "cycle": cycle,
                        "response": text[:400],
                        "latency_ms": lat,
                    })

        return state

    def fledge(self, state: EmbryoState) -> EmbryoState:
        """Stage 3: Nuclear model takes developed context → final output."""
        state.stage = "fledged"

        # Synthesize all context
        mito_summary = "\n".join(
            f"- [{e['model']}] {e['response'][:150]}"
            for e in state.mito_explorations[-5:]
        )
        nuc_summary = "\n".join(
            f"- [{n['model']}] {n['response'][:150]}"
            for n in state.nuclear_interventions[-3:]
        )

        fledge_prompt = (
            f"Task: {state.task}\n\n"
            f"Mitochondrial exploration:\n{mito_summary}\n\n"
            f"Nuclear analysis:\n{nuc_summary}\n\n"
            f"Convergence zones: {', '.join(state.convergence_zones)}\n\n"
            f"Based on all of the above, produce the final, complete solution."
        )

        for model in self.nuclear_models:
            text, lat = self._call(model, [{"role": "user", "content": fledge_prompt}],
                                    max_tokens=256, temperature=0.1, timeout=90.0)
            state.total_nuclear_calls += 1
            state.total_cost += 0.02
            if text:
                state.final_output = text
                break

        # If nuclear failed, try mitochondrial as fallback
        if not state.final_output:
            for model in self.mito_models:
                text, lat = self._call(model, [{"role": "user", "content": fledge_prompt}],
                                        max_tokens=400, temperature=0.2, timeout=40.0)
                state.total_mito_calls += 1
                state.total_cost += 0.001
                if text:
                    state.final_output = f"[MITOCHONDRIAL FALLBACK] {text}"
                    break

        return state


# ─── Demo ─────────────────────────────────────────────────────────────────────

BENCHMARK_PROMPTS = [
    "What is 2^10? Respond with just the number.",
    'Return valid JSON: {"name": "test", "value": 42, "active": true}',
    "Write a Python one-liner that filters even numbers from a list.",
    "Explain recursion in exactly one sentence.",
    "What are the 4 nucleotide bases in DNA? List them.",
]

COMPARISON_PROMPTS = [
    "Implement a binary search function in Python. Output only the function.",
    "Explain the difference between TCP and UDP in 2-3 sentences.",
    "What is 15! (15 factorial)? Just the number.",
    "Write a regex that matches email addresses. Output only the regex.",
    'Parse this into JSON: name=Alice, age=30, city=Seattle',
]


def demo(fallback_nuclear: bool = False):
    """Run the full mitochondrial benchmarking demo."""
    import os

    # Load keys
    deepinfra_key = os.environ.get("DEEPINFRA_KEY", "")
    zai_key = os.environ.get("ZAI_KEY", "")

    # Try loading from files if env vars not set
    if not deepinfra_key:
        key_file = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
        if os.path.exists(key_file):
            deepinfra_key = open(key_file).read().strip()

    if not zai_key:
        # Try to extract from openclaw config
        config_path = os.path.expanduser("~/.openclaw/config.toml")
        if os.path.exists(config_path):
            for line in open(config_path):
                if "api_key" in line and "z.ai" not in line:
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if len(val) > 20:
                        zai_key = val
                        break

    if not deepinfra_key or not zai_key:
        print("⚠️  Missing API keys. Running in MOCK mode.\n")
        mock_demo()
        return

    bench = MitochondrialBenchmark(deepinfra_key, zai_key)

    # ── Phase 1: Profile models ───────────────────────────────────────────
    nuclear_model_id = "glm-5-turbo"
    nuclear_provider = "z.ai"

    # If z.ai auth failed or fallback requested, use DeepInfra nuclear model
    if fallback_nuclear:
        nuclear_model_id = "Qwen/Qwen3-235B-A22B-Instruct-2507"
        nuclear_provider = "DeepInfra"

    print("=" * 60)
    print("PHASE 1: MODEL PROFILING")
    print("=" * 60)

    print(f"\n⚡ Profiling Seed-2.0-mini (mitochondrial candidate)...")
    mito_profile = bench.profile_model("ByteDance/Seed-2.0-mini", "DeepInfra", n_trials=5)
    print(mito_profile.summary())
    print(f"\n  Fitness score: {bench.fitness_score(mito_profile):.2f}")

    print(f"\n☢️  Profiling {nuclear_model_id} (nuclear candidate)...")
    nuc_profile = bench.profile_model(nuclear_model_id, nuclear_provider, n_trials=5)
    print(nuc_profile.summary())
    print(f"\n  Fitness score: {bench.fitness_score(nuc_profile):.2f}")

    # ── Phase 2: Head-to-head comparison ──────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2: HEAD-TO-HEAD COMPARISON")
    print("=" * 60)

    report = bench.run_comparison(nuclear_model_id, "ByteDance/Seed-2.0-mini", COMPARISON_PROMPTS)
    print(report.summary())

    for cp in report.agreements:
        print(f"  ✅ Agreement (sim={cp.agreement_score:.2f}): {cp.prompt[:60]}...")
        print(f"     Nuclear: {cp.nuclear_response[:100]}...")
        print(f"     Mito:    {cp.mito_response[:100]}...")

    for cp in report.divergences:
        print(f"  ⚠️  Divergence (sim={cp.agreement_score:.2f}): {cp.prompt[:60]}...")
        print(f"     Nuclear: {cp.nuclear_response[:100]}...")
        print(f"     Mito:    {cp.mito_response[:100]}...")

    for cp in report.mito_wins:
        print(f"  🏆 Mito wins: {cp.prompt[:60]}...")
        print(f"     Nuclear ({cp.nuclear_latency_ms:.0f}ms): {cp.nuclear_response[:100]}...")
        print(f"     Mito ({cp.mito_latency_ms:.0f}ms):    {cp.mito_response[:100]}...")

    for cp in report.mito_failures:
        print(f"  💀 Mito failure: {cp.prompt[:60]}...")
        print(f"     Mito: {cp.mito_response[:100]}...")

    # ── Phase 3: Incubator cycle ──────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 3: INCUBATOR — BOOTSTRAP → DEVELOP → FLEDGE")
    print("=" * 60)

    incubator = Incubator(
        mito_models=["ByteDance/Seed-2.0-mini"],
        nuclear_models=[nuclear_model_id],
        deepinfra_key=deepinfra_key,
        zai_key=zai_key,
    )

    task = "Design a URL router for a web framework that supports path parameters, wildcards, and middleware chains."

    print(f"\n🥚 Task: {task}\n")

    print("── BOOTSTRAP (mitochondrial exploration) ──")
    state = incubator.bootstrap(task)
    print(f"  Stage: {state.stage}")
    print(f"  Mito calls: {state.total_mito_calls}")
    for e in state.mito_explorations:
        print(f"  [{e['angle']}] {e['response'][:120]}...")

    print("\n── DEVELOP (cycles of mito + nuclear) ──")
    state = incubator.develop(state, n_cycles=2)
    print(f"  Stage: {state.stage}")
    print(f"  Convergence zones: {', '.join(state.convergence_zones[:5])}")
    print(f"  Mito calls: {state.total_mito_calls}, Nuclear calls: {state.total_nuclear_calls}")
    for n in state.nuclear_interventions:
        print(f"  [Nuclear cycle {n['cycle']}] {n['response'][:120]}...")

    print("\n── FLEDGE (nuclear final output) ──")
    state = incubator.fledge(state)
    print(f"  Stage: {state.stage}")
    print(f"  Total mito calls: {state.total_mito_calls}")
    print(f"  Total nuclear calls: {state.total_nuclear_calls}")
    print(f"  Estimated cost: ${state.total_cost:.4f}")
    if state.final_output:
        print(f"\n  Final output:\n  {state.final_output[:500]}")
    else:
        print("\n  ⚠️  No final output (nuclear model failed)")

    print("\n" + "=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


def mock_demo():
    """Demo with mock data when API keys are unavailable."""
    print("Running with MOCK responses to demonstrate architecture.\n")

    bench = MitochondrialBenchmark("mock-key", "mock-key")

    # Mock profiles
    mito_profile = ModelProfile(
        model_id="ByteDance/Seed-2.0-mini",
        provider="DeepInfra",
        avg_latency_ms=1200,
        p50_latency_ms=1100,
        p95_latency_ms=1800,
        cost_per_1k_tokens=0.001,
        reliability=0.95,
        is_mitochondrial=True,
        tokens_per_second=85.0,
        avg_output_tokens=120,
        sample_responses=["Response 1", "Response 2", "Response 3"],
    )

    nuc_profile = ModelProfile(
        model_id="glm-5-turbo",
        provider="z.ai",
        avg_latency_ms=3200,
        p50_latency_ms=2800,
        p95_latency_ms=5500,
        cost_per_1k_tokens=0.015,
        reliability=0.92,
        is_mitochondrial=False,
        tokens_per_second=45.0,
        avg_output_tokens=180,
    )

    print(mito_profile.summary())
    print(f"  Fitness: {bench.fitness_score(mito_profile):.2f}\n")
    print(nuc_profile.summary())
    print(f"  Fitness: {bench.fitness_score(nuc_profile):.2f}\n")

    # Mock comparison
    report = ComparisonReport(
        nuclear_profile=nuc_profile,
        mito_profile=mito_profile,
        agreements=[
            ComparisonPoint("What is 2^10?", "1024", "1024", 3100, 1100, 0.95, "agreement"),
            ComparisonPoint("Capital of France?", "Paris", "Paris", 2800, 900, 0.90, "agreement"),
        ],
        divergences=[
            ComparisonPoint("15 factorial", "1307674368000", "1.307674e12", 3500, 1300, 0.15, "divergence"),
        ],
        mito_wins=[
            ComparisonPoint("Binary search", "def binary_search...", "def binary_search...", 4200, 1500, 0.55, "mito_wins"),
        ],
        mito_failures=[
            ComparisonPoint("Complex multi-step reasoning", "Detailed answer", "[Incomplete]", 3800, 1400, 0.05, "mito_failure"),
        ],
    )
    print(report.summary())

    # Mock incubator
    state = EmbryoState(
        task="Design a URL router",
        stage="fledged",
        total_mito_calls=7,
        total_nuclear_calls=3,
        total_cost=0.037,
        convergence_zones=["router", "parameter", "middleware", "pattern", "handler"],
        final_output="class URLRouter:\n    def __init__(self): self.routes = []\n    def add_route(self, pattern, handler): ...\n    def match(self, path): ...",
    )
    print(f"Incubator result: {state.total_mito_calls} mito + {state.total_nuclear_calls} nuclear = ${state.total_cost:.3f}")
    print(f"Convergence: {state.convergence_zones}")
    print(f"Output: {state.final_output[:200]}")


if __name__ == "__main__":
    demo(fallback_nuclear=True)
