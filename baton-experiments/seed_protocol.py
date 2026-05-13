#!/usr/bin/env python3
"""
SEED PROTOCOL v1.0 — Hypothesis Generation & Knowledge Reconstruction via Small Models

Usage:
    python3 seed_protocol.py --mode gen --domain "constraint theory"
    python3 seed_protocol.py --mode recon --tile tile.txt --source source.txt
    python3 seed_protocol.py --mode cycle --domain "quantum error correction" --max-cycles 5
    python3 seed_protocol.py --mode oracle --results results.json

Requires: DEEPINFRA_API_KEY in env or ~/.openclaw/workspace/.credentials/deepinfra-api-key.txt
"""

import argparse
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError


# ─── Configuration ───────────────────────────────────────────────────────────

SEED_CONFIG = {
    "api_base": "https://api.deepinfra.com/v1/openai",
    "model": "ByteDance/Seed-2.0-mini",
    "temperature": 1.0,
    "max_tokens": 2048,
    "ensemble_size": 3,
    "accept_threshold": 3,       # min score (1-5) on each dimension
    "max_cycles": 5,
    "convergence_window": 3,     # consecutive low-novelty cycles = converged
    "convergence_threshold": 2.5,
    "max_cost_usd": 5.00,
    "quality_gates": True,
    "timeout_s": 60,
}

CREDENTIALS_PATH = Path(
    os.environ.get("SEED_CRED_PATH",
                   "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
).expanduser()


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class Hypothesis:
    id: str
    statement: str
    rationale: str
    falsification: str
    novelty: int          # 1-5
    actionability: int    # 1-5
    falsifiability: int   # 1-5
    accept: bool = False

    def __post_init__(self):
        threshold = SEED_CONFIG["accept_threshold"]
        self.accept = (
            self.novelty >= threshold
            and self.actionability >= threshold
            and self.falsifiability >= threshold
        )


@dataclass
class ReconResult:
    tile: str
    reconstructions: list[str]
    core_facts: list[str] = field(default_factory=list)
    peripheral_facts: list[str] = field(default_factory=list)
    recovery_rate: float = 0.0
    precision: float = 0.0
    hallucination_rate: float = 0.0
    cost_usd: float = 0.0


@dataclass
class CycleResult:
    cycle: int
    hypotheses: list[Hypothesis]
    test_results: list[dict]
    avg_novelty: float
    cost_usd: float
    converged: bool = False


@dataclass
class OracleAnalysis:
    strengths: list[str]
    weaknesses: list[str]
    failure_modes: list[str]
    recommendations: list[str]
    raw_output: str
    cost_usd: float = 0.01


@dataclass
class CostTracker:
    total_usd: float = 0.0
    operations: list[dict] = field(default_factory=list)

    def record(self, op: str, model: str, tokens: int, cost: float):
        self.total_usd += cost
        self.operations.append({
            "op": op, "model": model, "tokens": tokens,
            "cost_usd": round(cost, 6),
            "running_total": round(self.total_usd, 4),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })

    def check_budget(self):
        if self.total_usd >= SEED_CONFIG["max_cost_usd"]:
            raise RuntimeError(
                f"Budget exceeded: ${self.total_usd:.2f} >= ${SEED_CONFIG['max_cost_usd']:.2f}"
            )


# ─── API Client ──────────────────────────────────────────────────────────────

def _get_api_key() -> str:
    key = os.environ.get("DEEPINFRA_API_KEY", "").strip()
    if key:
        return key
    if CREDENTIALS_PATH.exists():
        return CREDENTIALS_PATH.read_text().strip()
    raise RuntimeError(
        f"No DEEPINFRA_API_KEY found. Set env var or populate {CREDENTIALS_PATH}"
    )


def _call_api(messages: list[dict], model: str = None, temperature: float = None,
              max_tokens: int = None) -> dict:
    """Call DeepInfra OpenAI-compatible chat completions endpoint."""
    api_key = _get_api_key()
    model = model or SEED_CONFIG["model"]
    temperature = temperature if temperature is not None else SEED_CONFIG["temperature"]
    max_tokens = max_tokens or SEED_CONFIG["max_tokens"]

    payload = json.dumps({
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()

    req = Request(
        f"{SEED_CONFIG['api_base']}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urlopen(req, timeout=SEED_CONFIG["timeout_s"]) as resp:
            body = json.loads(resp.read())
    except HTTPError as e:
        err_body = e.read().decode(errors="replace")
        raise RuntimeError(f"API error {e.code}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Connection error: {e.reason}") from e

    return body


def _extract_text(response: dict) -> str:
    return response["choices"][0]["message"]["content"]


def _estimate_cost(response: dict, model: str) -> float:
    """Rough cost estimate for DeepInfra models."""
    usage = response.get("usage", {})
    total = usage.get("total_tokens", 0)
    # Seed-2.0-mini: ~$0.01 per 1K tokens (conservative)
    # Other models priced higher
    rates = {
        "ByteDance/Seed-2.0-mini": 0.00001,
        "ByteDance/Seed-2.0-code": 0.00002,
        "ByteDance/Seed-2.0-pro": 0.00005,
        "NousResearch/Hermes-3-Llama-3.1-70B": 0.00005,
        "NousResearch/Hermes-3-Llama-3.1-405B": 0.00015,
    }
    rate = rates.get(model, 0.00002)
    return total * rate


# ─── Quality Gates ───────────────────────────────────────────────────────────

_CRED_PATTERNS = [
    re.compile(r'(?:api[_-]?key|token|secret|password|bearer)\s*[:=]\s*\S{8,}', re.I),
    re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # long hex strings
    re.compile(r'/home/\S+'),              # file paths
]


def gate_credentials(text: str) -> bool:
    """Returns True if text PASSES (no credential leaks detected)."""
    for pat in _CRED_PATTERNS:
        if pat.search(text):
            return False
    return True


_OVERCLAIM_WORDS = re.compile(
    r'\b(proves?|established|confirmed|definitive|undeniable|certain)\b', re.I
)


def gate_overclaim(text: str) -> list[str]:
    """Returns list of overclaim passages (empty = pass)."""
    flagged = []
    for line in text.split("\n"):
        if _OVERCLAIM_WORDS.search(line):
            flagged.append(line.strip())
    return flagged


def gate_citations(text: str) -> list[str]:
    """Returns list of unverifiable citations. All are flagged as unverified."""
    # Simple heuristic: looks like author-year citations
    cites = re.findall(r'\([A-Z][a-z]+(?:\s+et\s+al\.?)?\s*,\s*\d{4}\)', text)
    return cites  # caller decides how to handle


def gate_consistency(text: str, known_facts: list[str] = None) -> list[str]:
    """Basic contradiction check against known facts."""
    contradictions = []
    if not known_facts:
        return contradictions
    # Naive: check if text directly negates a known fact
    negators = ["not ", "never ", "isn't ", "doesn't ", "cannot "]
    for fact in known_facts:
        for neg in negators:
            if neg + fact.lower()[:30] in text.lower():
                contradictions.append(f"Possible contradiction with: {fact}")
    return contradictions


def run_all_gates(text: str, known_facts: list[str] = None) -> dict:
    """Run all quality gates. Returns dict with pass/fail and details."""
    if not SEED_CONFIG["quality_gates"]:
        return {"pass": True, "gates": {}}

    results = {
        "credentials": {"pass": gate_credentials(text)},
        "overclaim": {"pass": len(gate_overclaim(text)) == 0, "flagged": gate_overclaim(text)},
        "citations": {"pass": len(gate_citations(text)) == 0, "found": gate_citations(text)},
        "consistency": {"pass": True, "contradictions": []},
    }

    if known_facts:
        contradictions = gate_consistency(text, known_facts)
        results["consistency"] = {
            "pass": len(contradictions) == 0,
            "contradictions": contradictions,
        }

    overall_pass = all(g["pass"] for g in results.values())
    return {"pass": overall_pass, "gates": results}


# ─── SEED-GEN: Hypothesis Generation ────────────────────────────────────────

GEN_PROMPT = """You are a hypothesis generator. Given the domain, known facts, and unknowns below,
generate {n_hypotheses} novel, falsifiable hypotheses.

DOMAIN: {domain}

KNOWN:
{known}

UNKNOWN:
{unknown}

For each hypothesis:
1. State the hypothesis clearly and concisely
2. Explain WHY it's plausible given the known facts
3. Describe a specific experiment or observation that could FALSIFY it
4. Rate novelty (1-5): how different is this from the obvious explanation?
5. Rate actionability (1-5): how easy would it be to test?
6. Rate falsifiability (1-5): how precisely can it be disproven?

Be creative. Obvious hypotheses are useless. Prioritize novelty over safety.
Output each hypothesis as a JSON object with keys: statement, rationale, falsification, novelty, actionability, falsifiability.
Output a JSON array of these objects."""


class SeedGen:
    def __init__(self, tracker: CostTracker = None):
        self.tracker = tracker or CostTracker()

    def generate(self, domain: str, known: list[str] = None,
                 unknown: list[str] = None, n_hypotheses: int = 5) -> list[Hypothesis]:
        known = known or []
        unknown = unknown or []

        prompt = GEN_PROMPT.format(
            n_hypotheses=n_hypotheses,
            domain=domain,
            known="\n".join(f"- {k}" for k in known) or "None specified",
            unknown="\n".join(f"- {u}" for u in unknown) or "None specified",
        )

        self.tracker.check_budget()
        response = _call_api([{"role": "user", "content": prompt}])
        text = _extract_text(response)
        cost = _estimate_cost(response, SEED_CONFIG["model"])
        self.tracker.record("seed-gen", SEED_CONFIG["model"],
                           response.get("usage", {}).get("total_tokens", 0), cost)

        # Quality gate
        gate_result = run_all_gates(text, known)
        if not gate_result["pass"]:
            print(f"[GATE] Output failed quality gates: {gate_result}", file=sys.stderr)

        # Parse hypotheses
        hypotheses = self._parse_hypotheses(text)
        return hypotheses

    def _parse_hypotheses(self, text: str) -> list[Hypothesis]:
        # Try to extract JSON array from text
        hypotheses = []

        # Find JSON array in response
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            try:
                items = json.loads(json_match.group())
                for i, item in enumerate(items):
                    h = Hypothesis(
                        id=f"H-{i+1:03d}",
                        statement=item.get("statement", ""),
                        rationale=item.get("rationale", ""),
                        falsification=item.get("falsification", ""),
                        novelty=int(item.get("novelty", 3)),
                        actionability=int(item.get("actionability", 3)),
                        falsifiability=int(item.get("falsifiability", 3)),
                    )
                    hypotheses.append(h)
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[PARSE] JSON parse error: {e}", file=sys.stderr)

        # Fallback: parse structured text
        if not hypotheses:
            hypotheses = self._parse_text_hypotheses(text)

        return hypotheses

    def _parse_text_hypotheses(self, text: str) -> list[Hypothesis]:
        """Fallback parser for non-JSON structured output."""
        hypotheses = []
        blocks = re.split(r'\n(?=\d+[\.\)]\s)', text)
        for i, block in enumerate(blocks):
            if not block.strip():
                continue
            # Extract scores
            novelty = self._extract_score(block, "novelty")
            actionability = self._extract_score(block, "actionability")
            falsifiability = self._extract_score(block, "falsifiability")

            h = Hypothesis(
                id=f"H-{i+1:03d}",
                statement=block.strip()[:200],
                rationale="",
                falsification="",
                novelty=novelty,
                actionability=actionability,
                falsifiability=falsifiability,
            )
            hypotheses.append(h)
        return hypotheses

    @staticmethod
    def _extract_score(text: str, dimension: str) -> int:
        m = re.search(rf'{dimension}\s*[:\=]?\s*(\d)', text, re.I)
        return int(m.group(1)) if m else 3


# ─── SEED-RECON: Knowledge Reconstruction ────────────────────────────────────

RECON_PROMPT = """You are a knowledge reconstructor. Given the compressed knowledge tile below,
reconstruct the full knowledge it encodes. Expand every abbreviation, infer
missing connections, and restore the complete picture.

TILE:
{tile}

Reconstruct:
1. All named entities and their relationships
2. All numerical values and their context
3. All causal chains and their steps
4. All domain-specific terminology and definitions
5. All constraints and their implications

Do NOT add information not present in the tile. Mark any inference with [INFERRED].
"""


class SeedRecon:
    def __init__(self, tracker: CostTracker = None):
        self.tracker = tracker or CostTracker()

    def reconstruct(self, tile: str, source: str = None,
                    n_ensemble: int = None) -> ReconResult:
        n_ensemble = n_ensemble or SEED_CONFIG["ensemble_size"]

        prompt = RECON_PROMPT.format(tile=tile)
        reconstructions = []
        total_cost = 0.0

        for i in range(n_ensemble):
            self.tracker.check_budget()
            response = _call_api([{"role": "user", "content": prompt}])
            text = _extract_text(response)
            cost = _estimate_cost(response, SEED_CONFIG["model"])
            self.tracker.record(f"seed-recon-{i+1}", SEED_CONFIG["model"],
                               response.get("usage", {}).get("total_tokens", 0), cost)
            total_cost += cost
            reconstructions.append(text)

        result = ReconResult(
            tile=tile,
            reconstructions=reconstructions,
            cost_usd=round(total_cost, 4),
        )

        if source:
            self._evaluate(result, source)

        return result

    def _evaluate(self, result: ReconResult, source: str):
        """Evaluate reconstruction quality against source."""
        source_facts = self._extract_facts(source)
        all_recovered = set()
        fact_counts = {}  # fact → how many reconstructions include it

        for recon in result.reconstructions:
            recon_facts = self._extract_facts(recon)
            for f in recon_facts:
                fact_counts[f] = fact_counts.get(f, 0) + 1
                all_recovered.add(f)

        n = len(result.reconstructions)
        core = [f for f, c in fact_counts.items() if c > n / 2]
        peripheral = [f for f, c in fact_counts.items() if c <= n / 2]

        result.core_facts = core
        result.peripheral_facts = peripheral

        if source_facts:
            result.recovery_rate = len(all_recovered & source_facts) / max(len(source_facts), 1)
            # Precision: recovered facts that are in source
            result.precision = len(all_recovered & source_facts) / max(len(all_recovered), 1)
            # Hallucinations: recovered facts NOT in source
            hallucinated = all_recovered - source_facts
            result.hallucination_rate = len(hallucinated) / max(len(all_recovered), 1)

    @staticmethod
    def _extract_facts(text: str, min_words: int = 4) -> set[str]:
        """Extract candidate atomic facts as normalized sentences."""
        facts = set()
        for line in text.split("."):
            line = line.strip().lower()
            # Remove markers
            line = re.sub(r'\[inferred\]|\[speculation\]|\[evidence\]', '', line, flags=re.I)
            line = line.strip()
            if len(line.split()) >= min_words:
                facts.add(line)
        return facts


# ─── SEED-CYCLE: Iterative Discovery ────────────────────────────────────────

TEST_CODE_PROMPT = """Write a Python function to test the following hypothesis:

HYPOTHESIS: {hypothesis}

The function should:
1. Return a dict with keys: 'supported' (bool), 'evidence' (str), 'confidence' (float 0-1)
2. Be self-contained (no external dependencies beyond stdlib)
3. Actually test the hypothesis, not just return a fixed answer

Output ONLY the Python code, no markdown fences or explanation."""

FEEDBACK_PROMPT = """Given the following hypothesis test results, update the domain knowledge.

ORIGINAL DOMAIN: {domain}

PREVIOUSLY KNOWN:
{known}

TEST RESULTS:
{test_results}

Provide:
1. NEW KNOWN: List of newly confirmed facts (prefixed with [CONFIRMED])
2. REJECTED: List of falsified hypotheses (prefixed with [REJECTED])
3. NEW UNKNOWN: List of new questions raised (prefixed with [QUESTION])

Be precise. Only include facts directly supported by test results."""


class SeedCycle:
    def __init__(self, max_cycles: int = None, tracker: CostTracker = None):
        self.max_cycles = max_cycles or SEED_CONFIG["max_cycles"]
        self.tracker = tracker or CostTracker()
        self.gen = SeedGen(self.tracker)

    def run(self, domain: str, known: list[str] = None,
            unknown: list[str] = None) -> list[CycleResult]:
        known = list(known or [])
        unknown = list(unknown or [])
        results = []
        novelty_history = []

        for cycle_num in range(1, self.max_cycles + 1):
            self.tracker.check_budget()

            # Phase 1: Generate hypotheses
            hypotheses = self.gen.generate(domain, known, unknown)
            accepted = [h for h in hypotheses if h.accept]

            if not accepted:
                print(f"[CYCLE {cycle_num}] No accepted hypotheses. Stopping.", file=sys.stderr)
                break

            # Phase 2: Test hypotheses
            test_results = self._test_hypotheses(accepted)

            # Phase 3: Feedback
            feedback = self._integrate_feedback(domain, known, test_results)
            known = feedback.get("known", known)
            unknown = feedback.get("unknown", unknown)

            # Calculate metrics
            avg_novelty = sum(h.novelty for h in accepted) / max(len(accepted), 1)
            cycle_cost = self.tracker.total_usd - (
                results[-1].cost_usd if results else 0
            )
            novelty_history.append(avg_novelty)

            # Phase 4: Convergence check
            converged = False
            if len(novelty_history) >= SEED_CONFIG["convergence_window"]:
                recent = novelty_history[-SEED_CONFIG["convergence_window"]:]
                if all(n < SEED_CONFIG["convergence_threshold"] for n in recent):
                    converged = True

            cycle_result = CycleResult(
                cycle=cycle_num,
                hypotheses=accepted,
                test_results=test_results,
                avg_novelty=round(avg_novelty, 2),
                cost_usd=round(self.tracker.total_usd, 4),
                converged=converged,
            )
            results.append(cycle_result)

            print(f"[CYCLE {cycle_num}] {len(accepted)} hypotheses, "
                  f"avg novelty={avg_novelty:.2f}, cost=${self.tracker.total_usd:.4f}")

            if converged:
                print(f"[CYCLE {cycle_num}] Converged — no novel hypotheses in "
                      f"{SEED_CONFIG['convergence_window']} consecutive cycles.")
                break

        return results

    def _test_hypotheses(self, hypotheses: list[Hypothesis]) -> list[dict]:
        """Generate and execute simple tests for hypotheses."""
        results = []
        for h in hypotheses:
            self.tracker.check_budget()
            # Generate test code
            prompt = TEST_CODE_PROMPT.format(hypothesis=h.statement)
            response = _call_api(
                [{"role": "user", "content": prompt}],
                model="ByteDance/Seed-2.0-code",
                temperature=0.3,
            )
            code = _extract_text(response)
            cost = _estimate_cost(response, "ByteDance/Seed-2.0-code")
            self.tracker.record("test-gen", "ByteDance/Seed-2.0-code",
                               response.get("usage", {}).get("total_tokens", 0), cost)

            # Try to execute
            exec_result = self._execute_test(code)
            results.append({
                "hypothesis_id": h.id,
                "hypothesis": h.statement,
                "test_code": code,
                "execution": exec_result,
            })
        return results

    def _execute_test(self, code: str) -> dict:
        """Safely execute test code in a restricted environment."""
        # Clean code
        code = re.sub(r'^```python\s*', '', code)
        code = re.sub(r'\s*```$', '', code)

        try:
            local_vars = {}
            exec(code, {"__builtins__": {
                "print": print, "range": range, "len": len,
                "int": int, "float": float, "str": str, "bool": bool,
                "list": list, "dict": dict, "set": set, "tuple": tuple,
                "True": True, "False": False, "None": None,
                "abs": abs, "min": min, "max": max, "sum": sum,
                "enumerate": enumerate, "zip": zip,
            }}, local_vars)

            # Look for a test function
            for name, obj in local_vars.items():
                if callable(obj) and "test" in name.lower():
                    result = obj()
                    if isinstance(result, dict):
                        return {"status": "success", "result": result}
                    return {"status": "success", "result": {"returned": str(result)}}

            return {"status": "no_test_function", "code": code[:500]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _integrate_feedback(self, domain: str, known: list[str],
                            test_results: list[dict]) -> dict:
        """Integrate test results into domain knowledge."""
        results_text = "\n".join(
            f"- {r['hypothesis']}: {r['execution']}"
            for r in test_results
        )
        prompt = FEEDBACK_PROMPT.format(
            domain=domain,
            known="\n".join(f"- {k}" for k in known) or "None",
            test_results=results_text,
        )

        self.tracker.check_budget()
        response = _call_api([{"role": "user", "content": prompt}])
        text = _extract_text(response)
        cost = _estimate_cost(response, SEED_CONFIG["model"])
        self.tracker.record("feedback", SEED_CONFIG["model"],
                           response.get("usage", {}).get("total_tokens", 0), cost)

        new_known = known.copy()
        new_unknown = []

        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("[CONFIRMED]"):
                new_known.append(line.replace("[CONFIRMED]", "").strip())
            elif line.startswith("[QUESTION]"):
                new_unknown.append(line.replace("[QUESTION]", "").strip())

        return {"known": new_known, "unknown": new_unknown}


# ─── SEED-ORACLE: Model Self-Analysis ────────────────────────────────────────

ORACLE_PROMPT = """You are a 3B parameter language model. You have just completed the following
tasks with these results:

TASKS AND RESULTS:
{task_results}

Analyze your own performance:

1. **Strengths:** Where did you perform well? What types of tasks suit your architecture?
2. **Weaknesses:** Where did you fail? What types of reasoning do you struggle with?
3. **Failure modes:** Are there systematic patterns in your errors?
4. **Calibration:** For tasks where you were confident but wrong, why?
5. **Recommendations:** What would help you perform better on similar tasks?

Be honest. Inflated self-assessment is less useful than accurate criticism.
Mark speculation with [SPECULATION] and evidence-based analysis with [EVIDENCE]."""


class SeedOracle:
    def __init__(self, tracker: CostTracker = None):
        self.tracker = tracker or CostTracker()

    def analyze(self, task_results: list[dict]) -> OracleAnalysis:
        results_text = json.dumps(task_results, indent=2)[:3000]
        prompt = ORACLE_PROMPT.format(task_results=results_text)

        self.tracker.check_budget()
        response = _call_api(
            [{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        text = _extract_text(response)
        cost = _estimate_cost(response, SEED_CONFIG["model"])
        self.tracker.record("seed-oracle", SEED_CONFIG["model"],
                           response.get("usage", {}).get("total_tokens", 0), cost)

        return self._parse_analysis(text, cost)

    def _parse_analysis(self, text: str, cost: float) -> OracleAnalysis:
        strengths, weaknesses, failures, recommendations = [], [], [], []
        current_section = None

        for line in text.split("\n"):
            lower = line.lower().strip()
            if "strength" in lower and (":" in lower or "**" in lower):
                current_section = "strengths"
                continue
            elif "weakness" in lower and (":" in lower or "**" in lower):
                current_section = "weaknesses"
                continue
            elif "failure" in lower and (":" in lower or "**" in lower):
                current_section = "failures"
                continue
            elif "recommend" in lower and (":" in lower or "**" in lower):
                current_section = "recommendations"
                continue

            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                item = stripped.lstrip("-* ").strip()
                if current_section == "strengths":
                    strengths.append(item)
                elif current_section == "weaknesses":
                    weaknesses.append(item)
                elif current_section == "failures":
                    failures.append(item)
                elif current_section == "recommendations":
                    recommendations.append(item)

        return OracleAnalysis(
            strengths=strengths,
            weaknesses=weaknesses,
            failure_modes=failures,
            recommendations=recommendations,
            raw_output=text,
            cost_usd=round(cost, 4),
        )


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="SEED PROTOCOL v1.0 — Small Model Discovery Engine"
    )
    parser.add_argument("--mode", required=True,
                        choices=["gen", "recon", "cycle", "oracle"],
                        help="Protocol mode to run")
    parser.add_argument("--domain", help="Domain description (gen, cycle)")
    parser.add_argument("--known", nargs="*", default=[], help="Known facts")
    parser.add_argument("--unknown", nargs="*", default=[], help="Unknown questions")
    parser.add_argument("--tile", help="Path to knowledge tile file (recon)")
    parser.add_argument("--source", help="Path to source file for recon comparison")
    parser.add_argument("--results", help="Path to task results JSON (oracle)")
    parser.add_argument("--max-cycles", type=int, default=5, help="Max cycles (cycle)")
    parser.add_argument("--n-hypotheses", type=int, default=5, help="Hypotheses to generate (gen)")
    parser.add_argument("--ensemble", type=int, default=3, help="Ensemble size (recon)")
    parser.add_argument("--no-gates", action="store_true", help="Disable quality gates")
    parser.add_argument("--json-output", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.no_gates:
        SEED_CONFIG["quality_gates"] = False

    tracker = CostTracker()
    output = None

    try:
        if args.mode == "gen":
            if not args.domain:
                parser.error("--domain required for gen mode")
            gen = SeedGen(tracker)
            hypotheses = gen.generate(
                domain=args.domain,
                known=args.known,
                unknown=args.unknown,
                n_hypotheses=args.n_hypotheses,
            )
            accepted = [h for h in hypotheses if h.accept]
            output = {
                "mode": "gen",
                "domain": args.domain,
                "total": len(hypotheses),
                "accepted": len(accepted),
                "hypotheses": [asdict(h) for h in hypotheses],
                "cost_usd": round(tracker.total_usd, 4),
            }

        elif args.mode == "recon":
            if not args.tile:
                parser.error("--tile required for recon mode")
            tile_text = Path(args.tile).read_text()
            source_text = Path(args.source).read_text() if args.source else None
            recon = SeedRecon(tracker)
            result = recon.reconstruct(tile_text, source_text, args.ensemble)
            output = {
                "mode": "recon",
                "n_reconstructions": len(result.reconstructions),
                "recovery_rate": f"{result.recovery_rate:.1%}",
                "precision": f"{result.precision:.1%}",
                "hallucination_rate": f"{result.hallucination_rate:.1%}",
                "core_facts": len(result.core_facts),
                "peripheral_facts": len(result.peripheral_facts),
                "cost_usd": result.cost_usd,
                "reconstructions": result.reconstructions,
            }

        elif args.mode == "cycle":
            if not args.domain:
                parser.error("--domain required for cycle mode")
            cycle = SeedCycle(max_cycles=args.max_cycles, tracker=tracker)
            results = cycle.run(
                domain=args.domain,
                known=args.known,
                unknown=args.unknown,
            )
            output = {
                "mode": "cycle",
                "domain": args.domain,
                "cycles_completed": len(results),
                "converged": results[-1].converged if results else False,
                "total_hypotheses": sum(len(r.hypotheses) for r in results),
                "cost_usd": round(tracker.total_usd, 4),
                "cycles": [
                    {
                        "cycle": r.cycle,
                        "n_hypotheses": len(r.hypotheses),
                        "avg_novelty": r.avg_novelty,
                        "converged": r.converged,
                        "cost_usd": r.cost_usd,
                    }
                    for r in results
                ],
            }

        elif args.mode == "oracle":
            if not args.results:
                parser.error("--results required for oracle mode")
            task_results = json.loads(Path(args.results).read_text())
            oracle = SeedOracle(tracker)
            analysis = oracle.analyze(task_results)
            output = {
                "mode": "oracle",
                "strengths": analysis.strengths,
                "weaknesses": analysis.weaknesses,
                "failure_modes": analysis.failure_modes,
                "recommendations": analysis.recommendations,
                "cost_usd": analysis.cost_usd,
                "raw_output": analysis.raw_output,
            }

    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    if output:
        if args.json_output:
            print(json.dumps(output, indent=2, default=str))
        else:
            # Pretty-print summary
            print(f"\n{'='*60}")
            print(f"  SEED PROTOCOL — {output['mode'].upper()} Results")
            print(f"{'='*60}")
            if output["mode"] == "gen":
                print(f"  Domain: {output['domain']}")
                print(f"  Generated: {output['total']} hypotheses")
                print(f"  Accepted: {output['accepted']}")
                print(f"  Cost: ${output['cost_usd']:.4f}")
                print()
                for h in output["hypotheses"]:
                    status = "✓ ACCEPT" if h["accept"] else "✗ REJECT"
                    print(f"  [{status}] {h['id']}: {h['statement'][:80]}...")
                    print(f"    Novelty={h['novelty']} Action={h['actionability']} "
                          f"Falsifiable={h['falsifiability']}")
                    print()
            elif output["mode"] == "recon":
                print(f"  Reconstructions: {output['n_reconstructions']}")
                print(f"  Recovery rate: {output['recovery_rate']}")
                print(f"  Precision: {output['precision']}")
                print(f"  Hallucination rate: {output['hallucination_rate']}")
                print(f"  Core facts: {output['core_facts']}")
                print(f"  Peripheral facts: {output['peripheral_facts']}")
                print(f"  Cost: ${output['cost_usd']:.4f}")
            elif output["mode"] == "cycle":
                print(f"  Domain: {output['domain']}")
                print(f"  Cycles: {output['cycles_completed']}")
                print(f"  Converged: {output['converged']}")
                print(f"  Total hypotheses: {output['total_hypotheses']}")
                print(f"  Cost: ${output['cost_usd']:.4f}")
                print()
                for c in output["cycles"]:
                    conv = " (CONVERGED)" if c["converged"] else ""
                    print(f"  Cycle {c['cycle']}: {c['n_hypotheses']} hypotheses, "
                          f"novelty={c['avg_novelty']}{conv}")
            elif output["mode"] == "oracle":
                print(f"  Strengths: {len(output['strengths'])}")
                for s in output["strengths"][:3]:
                    print(f"    • {s}")
                print(f"  Weaknesses: {len(output['weaknesses'])}")
                for w in output["weaknesses"][:3]:
                    print(f"    • {w}")
                print(f"  Cost: ${output['cost_usd']:.4f}")

            print(f"{'='*60}")

        # Save output
        out_path = Path(f"seed_output_{args.mode}_{int(time.time())}.json")
        out_path.write_text(json.dumps(output, indent=2, default=str))
        print(f"\n  Full output saved to: {out_path}")


if __name__ == "__main__":
    main()
