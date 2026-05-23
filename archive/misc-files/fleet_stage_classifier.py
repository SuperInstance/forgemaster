"""Fleet Stage Classifier — probes models and classifies their capability stage."""

from __future__ import annotations

import json
import math
import os
import re
import time
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List

import requests


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class ModelStage:
    name: str
    stage: int  # 1-4
    echo_rate: float
    accuracy: float
    is_thinking: bool
    tested_at: str


# ---------------------------------------------------------------------------
# Probes — six arithmetic / pattern questions
# ---------------------------------------------------------------------------

PROBES: List[dict] = [
    {
        "prompt": "What is 37 + 58? Reply with just the number.",
        "expected": 95,
        "type": "addition",
    },
    {
        "prompt": "What is 12 * 11? Reply with just the number.",
        "expected": 132,
        "type": "multiplication",
    },
    {
        "prompt": "Compute the Eisenstein norm a² - ab + b² where a=5, b=-3. Reply with just the number.",
        "expected": 49,
        "type": "eisenstein_vocab",
    },
    {
        "prompt": "Compute: 25 - (-15) + 9 = ? Reply with just the number.",
        "expected": 49,
        "type": "bare_arithmetic",
    },
    {
        "prompt": "What is 17 mod 5? Reply with just the number.",
        "expected": 2,
        "type": "modular",
    },
    {
        "prompt": "What is the next number in the sequence 1, 7, 19, 37, 61? Reply with just the number.",
        "expected": 91,
        "type": "pattern",
    },
]


# ---------------------------------------------------------------------------
# Model backends
# ---------------------------------------------------------------------------

def ask_ollama(model: str, prompt: str) -> tuple[str, Optional[str]]:
    """Ask a local Ollama model. Returns (content, reasoning_content_or_None)."""
    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        msg = data.get("message", {})
        content = msg.get("content", "")
        reasoning = msg.get("reasoning_content") or msg.get("thinking") or None
        return content.strip(), reasoning
    except Exception as e:
        return f"ERROR: {e}", None


def ask_deepinfra(model: str, prompt: str, api_key: str) -> tuple[str, Optional[str]]:
    """Ask a DeepInfra model. Returns (content, reasoning_content_or_None)."""
    try:
        r = requests.post(
            "https://api.deepinfra.com/v1/openai/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512,
                "temperature": 0.1,
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        choice = data.get("choices", [{}])[0]
        msg = choice.get("message", {})
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content") or None
        return content.strip(), reasoning
    except Exception as e:
        return f"ERROR: {e}", None


# ---------------------------------------------------------------------------
# Answer extraction
# ---------------------------------------------------------------------------

def extract_last_int(text: str) -> Optional[int]:
    """Extract the last integer from the model's response."""
    # Find all integers (including negative)
    matches = re.findall(r"-?\d+", text)
    if not matches:
        return None
    return int(matches[-1])


# ---------------------------------------------------------------------------
# StageClassifier
# ---------------------------------------------------------------------------

class StageClassifier:
    """Probe a model and classify its capability stage (1-4)."""

    def __init__(self, deepinfra_key: Optional[str] = None):
        self.deepinfra_key = deepinfra_key

    def _ask(self, model_id: str, provider: str, prompt: str) -> tuple[str, Optional[str]]:
        if provider == "ollama":
            return ask_ollama(model_id, prompt)
        elif provider == "deepinfra":
            if not self.deepinfra_key:
                return "ERROR: no deepinfra key", None
            return ask_deepinfra(model_id, prompt, self.deepinfra_key)
        else:
            return f"ERROR: unknown provider {provider}", None

    def classify(self, model_id: str, provider: str = "ollama") -> ModelStage:
        """Send probes and classify the model."""
        correct = 0
        echo_count = 0
        is_thinking = False
        total = len(PROBES)

        for probe in PROBES:
            content, reasoning = self._ask(model_id, provider, probe["prompt"])

            if reasoning is not None:
                is_thinking = True

            answer = extract_last_int(content)

            if answer == probe["expected"]:
                correct += 1

            # Check echo: does the response contain numbers from the prompt?
            prompt_nums = set(re.findall(r"\d+", probe["prompt"]))
            response_nums = set(re.findall(r"\d+", content))
            if prompt_nums & response_nums:
                echo_count += 1

        accuracy = correct / total
        echo_rate = echo_count / total

        # Stage thresholds
        if accuracy >= 0.80:
            stage = 4
        elif accuracy < 0.05:
            stage = 1
        elif echo_rate > 0.30 and accuracy < 0.15:
            stage = 2
        else:
            stage = 3

        return ModelStage(
            name=model_id,
            stage=stage,
            echo_rate=round(echo_rate, 3),
            accuracy=round(accuracy, 3),
            is_thinking=is_thinking,
            tested_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )


# ---------------------------------------------------------------------------
# StageRegistry — JSON persistence
# ---------------------------------------------------------------------------

class StageRegistry:
    """Persist and look up ModelStage entries."""

    def __init__(self):
        self._store: Dict[str, ModelStage] = {}

    def save(self, path: str = "stage_registry.json") -> None:
        data = {k: asdict(v) for k, v in self._store.items()}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str = "stage_registry.json") -> None:
        if not os.path.exists(path):
            return
        with open(path) as f:
            data = json.load(f)
        for k, v in data.items():
            self._store[k] = ModelStage(**v)

    def get(self, model_id: str, classifier: Optional[StageClassifier] = None,
            provider: str = "ollama") -> ModelStage:
        if model_id not in self._store and classifier is not None:
            self._store[model_id] = classifier.classify(model_id, provider)
        return self._store[model_id]

    def __contains__(self, model_id: str) -> bool:
        return model_id in self._store

    def __getitem__(self, model_id: str) -> ModelStage:
        return self._store[model_id]


# ---------------------------------------------------------------------------
# translate_for_stage — prompt adaptation
# ---------------------------------------------------------------------------

def translate_for_stage(task_type: str, params: dict, stage: int) -> str:
    """Translate a task prompt appropriate for the model's stage.

    Stage < 4: pre-compute all arithmetic, use bare numbers.
    Stage 4: use domain vocabulary.
    """
    if task_type == "eisenstein_norm":
        a = params.get("a", 0)
        b = params.get("b", 0)
        if stage < 4:
            a2 = a * a
            ab = a * b
            b2 = b * b
            return f"Compute: {a2} - {ab} + {b2} = ?"
        else:
            return f"Compute the Eisenstein norm of ({a} + {b}ω)"

    elif task_type == "covering_radius":
        lattice = params.get("lattice", "A2")
        dimension = params.get("dimension", 2)
        if stage < 4:
            return f"What is the maximum distance from any point to the nearest {lattice} lattice point in {dimension}D? Give the numerical value."
        else:
            return f"Compute the covering radius of the {lattice} lattice in dimension {dimension}."

    elif task_type == "mobius":
        n = params.get("n", 1)
        if stage < 4:
            return f"Is {n} square-free and does it have an even number of prime factors? Reply 1 for yes (mobius=1), -1 for odd count, 0 if not square-free."
        else:
            return f"Compute the Möbius function μ({n})."

    elif task_type == "modular_inverse":
        a = params.get("a", 3)
        m = params.get("m", 7)
        if stage < 4:
            # Pre-compute hint
            return f"Find x such that ({a} * x) mod {m} = 1. x is between 1 and {m-1}. Reply with just x."
        else:
            return f"Compute the modular inverse of {a} modulo {m}."

    elif task_type == "generic":
        expr = params.get("expr", "?")
        return f"Compute: {expr}"

    else:
        return str(params)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== Fleet Stage Classifier ===\n")

    # Try to load DeepInfra key
    key_path = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
    deepinfra_key = None
    if os.path.exists(key_path):
        with open(key_path) as f:
            deepinfra_key = f.read().strip()

    classifier = StageClassifier(deepinfra_key=deepinfra_key)
    registry = StageRegistry()

    # Classify local Ollama models
    models_to_test = [
        ("phi4-mini", "ollama"),
        ("qwen3:4b", "ollama"),
    ]

    for model_id, provider in models_to_test:
        print(f"Classifying {model_id} via {provider}...")
        try:
            stage = classifier.classify(model_id, provider)
            registry._store[model_id] = stage
            print(f"  → Stage {stage.stage} | accuracy={stage.accuracy} | "
                  f"echo_rate={stage.echo_rate} | thinking={stage.is_thinking}")
        except Exception as e:
            print(f"  → FAILED: {e}")

    # Save registry
    registry.save()
    print(f"\nRegistry saved ({len(registry._store)} models)")

    # Test translate_for_stage
    print("\n=== translate_for_stage tests ===")
    test_params = [
        ("eisenstein_norm", {"a": 5, "b": -3}),
        ("covering_radius", {"lattice": "A2", "dimension": 2}),
        ("mobius", {"n": 30}),
        ("modular_inverse", {"a": 3, "m": 7}),
        ("generic", {"expr": "2+2"}),
    ]

    for task_type, params in test_params:
        low = translate_for_stage(task_type, params, stage=2)
        high = translate_for_stage(task_type, params, stage=4)
        print(f"\n{task_type}:")
        print(f"  Stage<4: {low}")
        print(f"  Stage 4: {high}")
