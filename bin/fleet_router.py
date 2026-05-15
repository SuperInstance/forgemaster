import json
import logging
import os
import sys
import datetime
import math
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional, Any, List, Tuple
from enum import Enum
from pathlib import Path


logger = logging.getLogger("fleet_router")
logger.setLevel(logging.DEBUG)


@dataclass
class ModelStage:
    name: str
    stage: int
    echo_rate: float
    accuracy: float
    is_thinking: bool
    is_free: bool
    provider: str
    model_id: str

    def __post_init__(self):
        if not 1 <= self.stage <= 4:
            raise ValueError(f"Stage must be 1-4, got {self.stage}")


FLEET_MODELS: Dict[str, ModelStage] = {
    "glm-5.1": ModelStage(
        name="glm-5.1", stage=3, echo_rate=0.12, accuracy=0.94,
        is_thinking=True, is_free=False, provider="zai", model_id="zai/glm-5.1"
    ),
    "glm-5-turbo": ModelStage(
        name="glm-5-turbo", stage=3, echo_rate=0.08, accuracy=0.91,
        is_thinking=True, is_free=False, provider="zai", model_id="zai/glm-5-turbo"
    ),
    "seed-mini": ModelStage(
        name="seed-mini", stage=4, echo_rate=0.05, accuracy=0.97,
        is_thinking=True, is_free=True, provider="deepinfra", model_id="deepinfra/seed-mini"
    ),
    "seed-code": ModelStage(
        name="seed-code", stage=4, echo_rate=0.06, accuracy=0.96,
        is_thinking=True, is_free=True, provider="deepinfra", model_id="deepinfra/seed-code"
    ),
    "hermes-70b": ModelStage(
        name="hermes-70b", stage=3, echo_rate=0.10, accuracy=0.92,
        is_thinking=False, is_free=False, provider="deepinfra", model_id="deepinfra/hermes-70b"
    ),
    "qwen3-235b": ModelStage(
        name="qwen3-235b", stage=3, echo_rate=0.07, accuracy=0.95,
        is_thinking=True, is_free=False, provider="deepinfra", model_id="deepinfra/qwen3-235b"
    ),
    "phi4-mini": ModelStage(
        name="phi4-mini", stage=3, echo_rate=0.15, accuracy=0.88,
        is_thinking=False, is_free=True, provider="ollama", model_id="ollama/phi4-mini"
    ),
    "qwen3-4b": ModelStage(
        name="qwen3-4b", stage=4, echo_rate=0.18, accuracy=0.85,
        is_thinking=False, is_free=True, provider="ollama", model_id="ollama/qwen3-4b"
    ),
    "gemma3-1b": ModelStage(
        name="gemma3-1b", stage=2, echo_rate=0.25, accuracy=0.78,
        is_thinking=False, is_free=True, provider="ollama", model_id="ollama/gemma3-1b"
    ),
}


class FleetRouter:
    AUDIT_LOG = Path("fleet_audit.json")

    def __init__(self, models: Optional[Dict[str, ModelStage]] = None):
        self.models = models or FLEET_MODELS
        self._audit_entries: List[Dict[str, Any]] = []
        self._setup_logging()

    def _setup_logging(self):
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        )
        if not logger.handlers:
            logger.addHandler(handler)

    def _log_audit(self, entry: Dict[str, Any]) -> None:
        entry["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        self._audit_entries.append(entry)
        with open(self.AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry, indent=2) + "\n")
        logger.info(
            "Audit: task=%s model=%s provider=%s stage=%d",
            entry.get("task_type"),
            entry.get("model"),
            entry.get("provider"),
            entry.get("stage", 0),
        )

    # --- Routing ---
    def route(
        self,
        task_type: str,
        needs_domain: bool = False,
        prefer_free: bool = False,
    ) -> ModelStage:
        task_type = task_type.upper().strip()
        candidate: Optional[str] = None

        if task_type == "CODE":
            candidate = "glm-5.1"

        elif task_type == "COMPUTATION":
            if needs_domain:
                candidate = "seed-mini"
            else:
                candidate = "glm-5.1"

        elif task_type == "REASONING":
            candidate = "seed-mini"

        elif task_type == "CONTENT":
            candidate = "glm-5-turbo"

        elif task_type == "DOMAIN_MATH":
            # pick best stage-4 model by accuracy
            stage4 = [
                (m.accuracy, m.name)
                for m in self.models.values()
                if m.stage >= 4
            ]
            stage4.sort(reverse=True)
            candidate = stage4[0][1] if stage4 else "seed-mini"

        else:
            # fallback: highest accuracy stage-3+ model
            eligible = [
                (m.accuracy, m.name)
                for m in self.models.values()
                if m.stage >= 3
            ]
            eligible.sort(reverse=True)
            candidate = eligible[0][1] if eligible else "gemma3-1b"

        model = self.models[candidate]

        # prefer_free override
        if prefer_free and not model.is_free:
            free_models = [
                (m.accuracy, m.name)
                for m in self.models.values()
                if m.is_free
            ]
            if free_models:
                free_models.sort(reverse=True)
                model = self.models[free_models[0][1]]

        return model

    # --- Translation ---
    def translate(
        self,
        task_type: str,
        params: Dict[str, Any],
        model: ModelStage,
    ) -> str:
        operation = params.get("operation", "generic")
        stage = model.stage

        if stage >= 4:
            return self._translate_domain_vocabulary(operation, params)
        else:
            return self._translate_precomputed(operation, params)

    def _translate_domain_vocabulary(
        self, operation: str, params: Dict[str, Any]
    ) -> str:
        if operation == "eisenstein_norm":
            a = params.get("a", 0)
            b = params.get("b", 0)
            result = a * a - a * b + b * b
            return (
                f"Compute the Eisenstein norm N(a + bω) in the ring Z[ω] "
                f"where ω = e^(2πi/3) is a primitive cube root of unity. "
                f"For a = {a}, b = {b}, verify that N({a} + {b}ω) = a² - ab + b² = {result}. "
                f"Express your answer in terms of algebraic integer theory."
            )

        elif operation == "covering_radius":
            lattice = params.get("lattice", "hexagonal")
            dim = params.get("dimension", 2)
            return (
                f"Determine the covering radius μ(Λ) of the {lattice} lattice Λ "
                f"in dimension {dim}. Recall the covering radius is "
                f"sup_{{x ∈ R^{dim}}} inf_{{λ ∈ Λ}} ||x - λ||. "
                f"Provide the exact algebraic expression and its numerical value."
            )

        elif operation == "mobius":
            n = params.get("n", 1)
            return (
                f"Compute the Möbius function μ({n}) where μ is defined as: "
                f"μ(n) = 0 if n has a squared prime factor, "
                f"μ(n) = (-1)^k if n is the product of k distinct primes, "
                f"μ(1) = 1. Express your reasoning step by step."
            )

        elif operation == "generic":
            expression = params.get("expression", "")
            return (
                f"Evaluate the following mathematical expression using domain-specific "
                f"vocabulary from algebraic number theory and lattice geometry: "
                f"{expression}. Show all intermediate steps."
            )

        else:
            return f"Process the following parameters with full mathematical rigor: {json.dumps(params)}"

    def _translate_precomputed(
        self, operation: str, params: Dict[str, Any]
    ) -> str:
        if operation == "eisenstein_norm":
            a = params.get("a", 0)
            b = params.get("b", 0)
            result = a * a - a * b + b * b
            return (
                f"Verify the following arithmetic result: "
                f"For a = {a} and b = {b}, compute a² - a·b + b². "
                f"The pre-computed answer is {result}. "
                f"Confirm this result and show the step-by-step arithmetic."
            )

        elif operation == "covering_radius":
            lattice = params.get("lattice", "hexagonal")
            precomputed = params.get("precomputed_value", "0.5774")
            return (
                f"Verify the numerical result: The covering radius of the {lattice} lattice "
                f"is approximately {precomputed_value}. "
                f"Confirm the arithmetic: sqrt(1/3) ≈ 0.5774."
            )

        elif operation == "mobius":
            n = params.get("n", 1)
            result = self._compute_mobius(n)
            return (
                f"Verify the Möbius function computation: "
                f"μ({n}) = {result}. "
                f"Confirm this by checking the prime factorization of {n}."
            )

        elif operation == "generic":
            expression = params.get("expression", "")
            return (
                f"Compute the numerical value of: {expression}. "
                f"Show the step-by-step arithmetic."
            )

        else:
            return f"Compute the following: {json.dumps(params)}"

    @staticmethod
    def _compute_mobius(n: int) -> int:
        if n <= 0:
            return 0
        if n == 1:
            return 1
if __name__ == "__main__":
    print("=== Fleet Router Demo ===\n")
    router = FleetRouter()

    tests = [
        ("code", {"prompt": "Write eisenstein_norm function"}, False),
        ("computation", {"operation": "eisenstein_norm", "a": 7, "b": -2}, False),
        ("computation", {"operation": "eisenstein_norm", "a": 7, "b": -2}, True),
        ("domain_math", {"operation": "eisenstein_norm", "a": 3, "b": 8}, True),
        ("reasoning", {"question": "Is the Eisenstein ring a UDF?"}, False),
        ("content", {"topic": "Hexagonal lattices"}, False),
    ]

    for task_type, params, needs_domain in tests:
        model = router.route(task_type, needs_domain)
        prompt = router.translate(task_type, params, model)
        print(f'{task_type:15s} -> {model.name:15s} (Stage {model.stage})')
        print(f'  Prompt: {prompt[:80]}')
        print()

    print("=== Eisenstein Norm Routing ===")
    for a, b in [(5,-3), (7,2), (3,8), (-4,-6), (0,5)]:
        m1 = router.route("computation", needs_domain=False)
        p1 = router.translate("computation", {"operation":"eisenstein_norm","a":a,"b":b}, m1)
        m2 = router.route("domain_math", needs_domain=True)
        p2 = router.translate("domain_math", {"operation":"eisenstein_norm","a":a,"b":b}, m2)
        print(f'  ({a:+3d},{b:+3d}) compute->{m1.name:12s} domain->{m2.name:12s}')

    print(f'\nAudit log: {len(router.audit_log)} entries')
    router.save_log("/tmp/fleet_router_audit.json")
    print("Saved to /tmp/fleet_router_audit.json")
