#!/usr/bin/env python3
"""
Fleet Router API — FastAPI on :8100 with Critical-Angle Routing
================================================================
Routes computation requests to the best fleet model using:
  - Three-tier model taxonomy (Tier 1/2/3)
  - Stage-aware translation via fleet_translator_v2
  - Hebbian conservation awareness via fleet_hebbian_service
  - Critical-angle routing: pick the model that maximizes expected accuracy
  - Auto-downgrade when primary model is unavailable

Endpoints:
  POST /route         — route a single computation
  POST /route/batch   — route multiple computations at once
  GET  /health        — router status, model registry, routing stats
  GET  /models        — list registered models with tier info

Run:
  uvicorn fleet_router_api:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

import logging
import time
import threading
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Fleet translator integration
# ---------------------------------------------------------------------------
try:
    from fleet_translator_v2 import (
        FleetRouter as TranslatorRouter,
        ModelStage,
        translate,
        translate_for_stage,
        NotationNormalizer,
        ActivationKeyEngineer,
        KNOWN_STAGES,
    )
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

# ---------------------------------------------------------------------------
# Hebbian service integration
# ---------------------------------------------------------------------------
try:
    import numpy as np  # noqa: F401 — needed by hebbian service
    from fleet_hebbian_service import FleetHebbianService
    HAS_HEBBIAN = True
except ImportError:
    HAS_HEBBIAN = False

# ---------------------------------------------------------------------------
# MythosTile integration
# ---------------------------------------------------------------------------
try:
    from mythos_tile import MythosTile, ModelTier
    HAS_MYTHOS = True
except ImportError:
    HAS_MYTHOS = False


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("fleet_router_api")
logging.basicConfig(
    level=logging.INFO,
    format="[%(name)s] %(levelname)s: %(message)s",
)


# =========================================================================
# Tier Classification
# =========================================================================

class ModelTierEnum(IntEnum):
    """Three-tier model taxonomy from Study 48."""
    TIER_1_DIRECT = 1       # Bare notation passthrough — Seed models, gemma3:1b
    TIER_2_SCAFFOLDED = 2   # Activation key injection + notation normalization
    TIER_3_INCOMPETENT = 3  # Cannot reliably compute — reject with explanation


# Default model registry — maps model_id → tier
DEFAULT_MODELS: Dict[str, ModelTierEnum] = {
    # Tier 1 — direct computation (94-100% regardless of framing)
    "ByteDance/Seed-2.0-mini":          ModelTierEnum.TIER_1_DIRECT,
    "ByteDance/Seed-2.0-code":          ModelTierEnum.TIER_1_DIRECT,
    "gemma3:1b":                         ModelTierEnum.TIER_1_DIRECT,
    # Tier 2 — needs scaffolding (activation keys + normalization)
    "Qwen/Qwen3-235B-A22B-Instruct-2507": ModelTierEnum.TIER_2_SCAFFOLDED,
    "deepseek-chat":                     ModelTierEnum.TIER_2_SCAFFOLDED,
    "NousResearch/Hermes-3-Llama-3.1-70B": ModelTierEnum.TIER_2_SCAFFOLDED,
    "phi4-mini":                         ModelTierEnum.TIER_2_SCAFFOLDED,
    "llama3.2:1b":                       ModelTierEnum.TIER_2_SCAFFOLDED,
    # Tier 3 — incompetent for math
    "Qwen/Qwen3.6-35B-A3B":             ModelTierEnum.TIER_3_INCOMPETENT,
    "qwen3:4b":                          ModelTierEnum.TIER_3_INCOMPETENT,
    "qwen3:0.6b":                        ModelTierEnum.TIER_3_INCOMPETENT,
}

# Tier → expected accuracy range
TIER_ACCURACY = {
    ModelTierEnum.TIER_1_DIRECT: (0.94, 1.00),
    ModelTierEnum.TIER_2_SCAFFOLDED: (0.60, 0.85),
    ModelTierEnum.TIER_3_INCOMPETENT: (0.0, 0.30),
}

# Tier → ModelStage mapping (for translator integration)
TIER_TO_STAGE = {
    ModelTierEnum.TIER_1_DIRECT: ModelStage.FULL if HAS_TRANSLATOR else 4,
    ModelTierEnum.TIER_2_SCAFFOLDED: ModelStage.CAPABLE if HAS_TRANSLATOR else 3,
    ModelTierEnum.TIER_3_INCOMPETENT: ModelStage.ECHO if HAS_TRANSLATOR else 1,
}

# Preferred order for auto-routing (Tier 1 first, then Tier 2)
PREFERRED_ORDER: List[str] = [
    "ByteDance/Seed-2.0-mini",
    "ByteDance/Seed-2.0-code",
    "gemma3:1b",
    "Qwen/Qwen3-235B-A22B-Instruct-2507",
    "deepseek-chat",
    "NousResearch/Hermes-3-Llama-3.1-70B",
    "phi4-mini",
    "llama3.2:1b",
]


# =========================================================================
# Routing Statistics
# =========================================================================

@dataclass
class RoutingStats:
    """Track routing decisions over time."""
    total_requests: int = 0
    tier_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    model_utilization: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    task_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    downgrade_count: int = 0
    rejection_count: int = 0
    hebbian_routed: int = 0
    start_time: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, model_id: str, tier: ModelTierEnum,
               task_type: str, downgraded: bool = False,
               rejected: bool = False, via_hebbian: bool = False):
        with self._lock:
            self.total_requests += 1
            self.tier_distribution[f"tier_{tier.value}"] += 1
            self.model_utilization[model_id] += 1
            self.task_distribution[task_type] += 1
            if downgraded:
                self.downgrade_count += 1
            if rejected:
                self.rejection_count += 1
            if via_hebbian:
                self.hebbian_routed += 1

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time
            return {
                "total_requests": self.total_requests,
                "uptime_seconds": round(uptime, 1),
                "requests_per_minute": round(self.total_requests / max(uptime / 60, 0.001), 2),
                "tier_distribution": dict(self.tier_distribution),
                "model_utilization": dict(self.model_utilization),
                "task_distribution": dict(self.task_distribution),
                "downgrade_count": self.downgrade_count,
                "rejection_count": self.rejection_count,
                "hebbian_routed": self.hebbian_routed,
            }


# =========================================================================
# Model Registry
# =========================================================================

@dataclass
class ModelEntry:
    model_id: str
    tier: ModelTierEnum
    available: bool = True
    accuracy_low: float = 0.0
    accuracy_high: float = 1.0
    last_used: float = 0.0
    total_requests: int = 0


class ModelRegistry:
    """Register and query models with tier classification."""

    def __init__(self):
        self._models: Dict[str, ModelEntry] = {}
        self._lock = threading.Lock()

    def register(self, model_id: str, tier: ModelTierEnum,
                 available: bool = True) -> ModelEntry:
        with self._lock:
            lo, hi = TIER_ACCURACY.get(tier, (0.0, 1.0))
            entry = ModelEntry(
                model_id=model_id, tier=tier, available=available,
                accuracy_low=lo, accuracy_high=hi,
            )
            self._models[model_id] = entry
            logger.info("Registered model %s → tier %d", model_id, tier.value)
            return entry

    def get(self, model_id: str) -> Optional[ModelEntry]:
        with self._lock:
            return self._models.get(model_id)

    def get_tier(self, model_id: str) -> ModelTierEnum:
        entry = self.get(model_id)
        if entry:
            return entry.tier
        return ModelTierEnum.TIER_3_INCOMPETENT  # unknown → assume worst

    def set_available(self, model_id: str, available: bool):
        with self._lock:
            if model_id in self._models:
                self._models[model_id].available = available

    def mark_used(self, model_id: str):
        with self._lock:
            if model_id in self._models:
                self._models[model_id].last_used = time.time()
                self._models[model_id].total_requests += 1

    def list_models(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "model_id": e.model_id,
                    "tier": e.tier.value,
                    "tier_name": e.tier.name,
                    "available": e.available,
                    "accuracy_range": [e.accuracy_low, e.accuracy_high],
                    "last_used": round(e.last_used, 2) if e.last_used else None,
                    "total_requests": e.total_requests,
                }
                for e in self._models.values()
            ]

    def find_best(self, preferred_tier: ModelTierEnum = ModelTierEnum.TIER_1_DIRECT,
                  exclude: Optional[set] = None) -> Optional[ModelEntry]:
        """Find the best available model, preferring given tier, auto-downgrading."""
        exclude = exclude or set()
        # Try preferred tier first
        for entry in self._models.values():
            if entry.tier == preferred_tier and entry.available and entry.model_id not in exclude:
                return entry
        # Fall back to any Tier 1
        for entry in self._models.values():
            if entry.tier == ModelTierEnum.TIER_1_DIRECT and entry.available and entry.model_id not in exclude:
                return entry
        # Fall back to Tier 2
        for entry in self._models.values():
            if entry.tier == ModelTierEnum.TIER_2_SCAFFOLDED and entry.available and entry.model_id not in exclude:
                return entry
        return None


# =========================================================================
# Critical Angle Router
# =========================================================================

class CriticalAngleRouter:
    """
    Routes computation requests to the best model using critical-angle analysis.

    "Critical angle" = the model tier threshold where routing accuracy drops
    below acceptable bounds. We route to the highest-accuracy tier that's available,
    applying the correct translation/formatting for each tier.

    Three-tier formatting (per Study 49/50):
      - Tier 1: bare notation passthrough
      - Tier 2: activation key injection + notation normalization
      - Tier 3: reject with explanation (route to Tier 1/2 instead)
    """

    def __init__(self, registry: ModelRegistry, stats: RoutingStats,
                 hebbian_url: Optional[str] = None):
        self.registry = registry
        self.stats = stats
        self.hebbian_url = hebbian_url or "http://localhost:8849"
        self._translator_router = TranslatorRouter() if HAS_TRANSLATOR else None
        # Conservation-aware routing state
        self._compliance_rate: float = 1.0
        self._alignment_score: float = 1.0
        self._cross_consult_threshold: float = 0.85

    def set_conservation_state(self, compliance_rate: float,
                                alignment_score: float = 1.0) -> None:
        """Update conservation compliance and alignment for routing decisions."""
        self._compliance_rate = max(0.0, min(1.0, compliance_rate))
        self._alignment_score = max(0.0, min(1.0, alignment_score))

    def _conservation_filter(self, entry: 'ModelEntry') -> bool:
        """If compliance < 85%, only Tier 1 models are routed."""
        if self._compliance_rate >= self._cross_consult_threshold:
            return True
        return entry.tier == ModelTierEnum.TIER_1_DIRECT

    def _should_cross_consult(self) -> bool:
        return self._alignment_score < self._cross_consult_threshold

    def _find_conservative_best(
        self,
        preferred_tier: ModelTierEnum = ModelTierEnum.TIER_1_DIRECT,
        exclude: Optional[set] = None,
    ) -> Optional[ModelEntry]:
        """Find the best model respecting conservation constraints."""
        exclude = exclude or set()
        if self._compliance_rate >= self._cross_consult_threshold:
            return self.registry.find_best(preferred_tier, exclude)

        # Low compliance: only conservation-filtered models
        candidates = [
            e for e in self.registry._models.values()
            if e.available and e.model_id not in exclude and self._conservation_filter(e)
        ]
        candidates.sort(key=lambda e: (e.tier, -e.accuracy_high))
        return candidates[0] if candidates else self.registry.find_best(preferred_tier, exclude)

    def route_request(
        self,
        task_type: str,
        params: Dict[str, Any],
        preferred_model: Optional[str] = None,
        force_tier: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Route a computation request to the best model.

        Returns dict with:
          - model_id, tier, translated_prompt, estimated_accuracy, routing_reason
          - downgrade info if auto-downgraded
        """
        # Determine target model
        target_model = preferred_model
        downgraded = False
        rejected = False
        routing_reason = ""

        if force_tier:
            tier = ModelTierEnum(force_tier)
            if tier == ModelTierEnum.TIER_3_INCOMPETENT:
                rejected = True
                routing_reason = f"Force-tier 3 rejected: Tier 3 models cannot reliably compute"
                self.stats.record(target_model or "unknown", tier, task_type, rejected=True)
                return {
                    "model_id": None,
                    "tier": tier.value,
                    "translated_prompt": None,
                    "estimated_accuracy": 0.0,
                    "routing_reason": routing_reason,
                    "downgraded": False,
                    "rejected": True,
                    "recommendation": "Use a Tier 1 or Tier 2 model instead",
                }

        if target_model:
            entry = self.registry.get(target_model)
            if entry and entry.available:
                if not self._conservation_filter(entry):
                    # Conservation filter blocks this model
                    downgraded = True
                    fallback = self._find_conservative_best(exclude={target_model})
                    if fallback:
                        target_model = fallback.model_id
                        tier = fallback.tier
                        routing_reason = f"Conservation filter: {preferred_model} skipped → {target_model}"
                    else:
                        routing_reason = "Conservation filter: no suitable model"
                        self.stats.record(target_model or "none", tier, task_type, rejected=True)
                        return {
                            "model_id": None, "tier": tier.value,
                            "translated_prompt": None, "estimated_accuracy": 0.0,
                            "routing_reason": routing_reason,
                            "downgraded": True, "rejected": True,
                            "recommendation": "Conservation compliance too low",
                            "conservation_compliance": round(self._compliance_rate, 3),
                        }
                else:
                    tier = entry.tier
                    routing_reason = f"Explicit model selection: {target_model}"
            else:
                # Model unavailable — auto-downgrade
                downgraded = True
                tier = ModelTierEnum.TIER_2_SCAFFOLDED
                fallback = self._find_conservative_best(
                    exclude={target_model} if target_model else None
                )
                if fallback:
                    target_model = fallback.model_id
                    tier = fallback.tier
                    routing_reason = f"Auto-downgrade: {preferred_model} unavailable → {target_model}"
                else:
                    routing_reason = f"No available models (requested: {preferred_model})"
                    self.stats.record(target_model or "none", tier, task_type, rejected=True)
                    return {
                        "model_id": None, "tier": tier.value,
                        "translated_prompt": None, "estimated_accuracy": 0.0,
                        "routing_reason": routing_reason,
                        "downgraded": True, "rejected": True,
                        "recommendation": "No models available",
                        "conservation_compliance": round(self._compliance_rate, 3),
                    }
        else:
            # Auto-select best model (conservation-aware)
            entry = self._find_conservative_best()
            if entry:
                target_model = entry.model_id
                tier = entry.tier
                routing_reason = f"Auto-selected: {target_model} (tier {tier.value}, compliance={self._compliance_rate:.0%})"
            else:
                routing_reason = "No models registered or all filtered"
                self.stats.record("none", ModelTierEnum.TIER_3_INCOMPETENT, task_type, rejected=True)
                return {
                    "model_id": None, "tier": 3,
                    "translated_prompt": None, "estimated_accuracy": 0.0,
                    "routing_reason": routing_reason,
                    "downgraded": False, "rejected": True,
                    "recommendation": "Register models before routing",
                    "conservation_compliance": round(self._compliance_rate, 3),
                }

        # Tier 3 rejection
        if tier == ModelTierEnum.TIER_3_INCOMPETENT and not force_tier:
            rejected = True
            fallback = self.registry.find_best(
                preferred_tier=ModelTierEnum.TIER_1_DIRECT,
                exclude={target_model},
            )
            if fallback:
                target_model = fallback.model_id
                tier = fallback.tier
                downgraded = True
                routing_reason += f" → auto-upgraded to {target_model}"
            else:
                routing_reason += " — no better model available, rejecting"
                self.stats.record(target_model, tier, task_type, rejected=True)
                return {
                    "model_id": target_model, "tier": tier.value,
                    "translated_prompt": None, "estimated_accuracy": 0.0,
                    "routing_reason": routing_reason,
                    "downgraded": downgraded, "rejected": True,
                    "recommendation": "Tier 3 models cannot reliably compute. Use Tier 1 or 2.",
                }

        # Translate the prompt based on tier
        translated_prompt = self._translate(task_type, params, tier)

        # Estimate accuracy
        entry_obj = self.registry.get(target_model)
        lo, hi = (entry_obj.accuracy_low, entry_obj.accuracy_high) if entry_obj else (0.0, 1.0)
        estimated_accuracy = round((lo + hi) / 2, 2)

        # Mark model as used
        self.registry.mark_used(target_model)

        # Record stats
        self.stats.record(target_model, tier, task_type, downgraded=downgraded)

        # Hebbian flow event (best-effort, non-blocking)
        via_hebbian = self._emit_hebbian_event(target_model, task_type, params)

        return {
            "model_id": target_model,
            "tier": tier.value,
            "tier_name": tier.name,
            "translated_prompt": translated_prompt,
            "estimated_accuracy": estimated_accuracy,
            "routing_reason": routing_reason,
            "downgraded": downgraded,
            "rejected": False,
            "via_hebbian": via_hebbian,
            "conservation_compliance": round(self._compliance_rate, 3),
            "alignment_score": round(self._alignment_score, 3),
            "cross_consultation": self._should_cross_consult(),
        }

    def _translate(self, task_type: str, params: Dict[str, Any],
                   tier: ModelTierEnum) -> str:
        """Apply three-tier formatting."""
        if tier == ModelTierEnum.TIER_1_DIRECT:
            # Tier 1: bare notation passthrough (per Study 49/50)
            return self._translate_tier1(task_type, params)
        elif tier == ModelTierEnum.TIER_2_SCAFFOLDED:
            # Tier 2: activation key injection + notation normalization
            return self._translate_tier2(task_type, params)
        else:
            # Tier 3: should not reach here (rejected above), but fallback
            return self._translate_tier2(task_type, params)

    def _translate_tier1(self, task_type: str, params: Dict[str, Any]) -> str:
        """Tier 1: bare notation passthrough."""
        if HAS_TRANSLATOR:
            return translate(task_type, params, ModelStage.FULL)
        # Fallback without translator
        return self._build_prompt(task_type, params, scaffold=False)

    def _translate_tier2(self, task_type: str, params: Dict[str, Any]) -> str:
        """Tier 2: activation key injection + notation normalization."""
        if HAS_TRANSLATOR:
            return translate(task_type, params, ModelStage.CAPABLE)
        # Fallback without translator
        return self._build_prompt(task_type, params, scaffold=True)

    def _build_prompt(self, task_type: str, params: Dict[str, Any],
                      scaffold: bool = False) -> str:
        """Build a prompt without the translator module."""
        dispatch = {
            "eisenstein_norm": lambda: (
                f"Using the Eisenstein norm: compute a^2 - a*b + b^2 where a={params['a']}, b={params['b']}"
                if scaffold else
                f"Compute the Eisenstein norm of (a={params['a']}, b={params['b']})."
            ),
            "eisenstein_snap": lambda: (
                f"Using the Eisenstein lattice snap: snap point ({params['x']}, {params['y']}) to nearest lattice point."
                if scaffold else
                f"Snap ({params['x']}, {params['y']}) to the nearest Eisenstein lattice point."
            ),
            "mobius": lambda: (
                f"Using the Möbius function: compute mu({params['n']})."
                if scaffold else
                f"Compute the Möbius function μ({params['n']})."
            ),
            "legendre": lambda: (
                f"Using the Legendre symbol: compute ({params['a']}|{params['p']})."
                if scaffold else
                f"Compute the Legendre symbol ({params['a']}|{params['p']})."
            ),
            "modular_inverse": lambda: (
                f"Using modular inverse: find the inverse of {params['a']} mod {params['m']}."
                if scaffold else
                f"Find the modular inverse of {params['a']} mod {params['m']}."
            ),
            "cyclotomic_eval": lambda: (
                f"Using the cyclotomic polynomial: evaluate Phi_{params['n']}({params['x']})."
                if scaffold else
                f"Evaluate the cyclotomic polynomial Φ_{params['n']}({params['x']})."
            ),
            "generic": lambda: params.get("expression", "Compute."),
        }
        fn = dispatch.get(task_type)
        if fn:
            return fn()
        expr = params.get("expression", "")
        if scaffold and expr:
            return f"Compute the following: {expr}"
        return expr or "Compute."

    def _emit_hebbian_event(self, model_id: str, task_type: str,
                            params: Dict[str, Any]) -> bool:
        """Best-effort Hebbian flow event emission."""
        try:
            import urllib.request
            payload = {
                "tile_type": "model",
                "source_room": "fleet-router",
                "dest_room": f"model-{model_id.replace('/', '-').replace(':', '-')}",
                "confidence": 0.9,
                "tags": [task_type, "routed"],
            }
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{self.hebbian_url}/tile",
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=2):
                return True
        except Exception:
            return False

    def route_batch(
        self,
        items: List[Dict[str, Any]],
        preferred_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Route multiple computations at once.
        Groups by optimal model to minimize API calls.
        """
        results = []
        # Group items by target model for batching
        model_groups: Dict[str, List[int]] = defaultdict(list)

        # Phase 1: determine routing for each item
        routing_plans: List[Dict[str, Any]] = []
        for i, item in enumerate(items):
            task_type = item.get("task_type", "generic")
            params = item.get("params", {})
            plan = self.route_request(task_type, params, preferred_model=preferred_model)
            routing_plans.append(plan)
            if plan.get("model_id"):
                model_groups[plan["model_id"]].append(i)

        # Phase 2: build grouped output
        groups = []
        for model_id, indices in model_groups.items():
            group_items = []
            for idx in indices:
                item = items[idx]
                plan = routing_plans[idx]
                group_items.append({
                    "index": idx,
                    "task_type": item.get("task_type", "generic"),
                    "translated_prompt": plan.get("translated_prompt"),
                    "estimated_accuracy": plan.get("estimated_accuracy"),
                })
            entry = self.registry.get(model_id)
            groups.append({
                "model_id": model_id,
                "tier": entry.tier.value if entry else 3,
                "count": len(indices),
                "items": group_items,
            })

        total = len(items)
        routed = sum(1 for p in routing_plans if not p.get("rejected"))
        rejected = total - routed

        return {
            "total": total,
            "routed": routed,
            "rejected": rejected,
            "groups": groups,
            "model_distribution": {m: len(idx_list) for m, idx_list in model_groups.items()},
        }


# =========================================================================
# Pydantic request/response models
# =========================================================================

import json  # noqa: E402 — needed earlier for hebbian, ensure available


class RouteRequest(BaseModel):
    task_type: str = Field(..., description="Task type: eisenstein_norm, mobius, legendre, etc.")
    params: Dict[str, Any] = Field(default_factory=dict, description="Task parameters")
    preferred_model: Optional[str] = Field(None, description="Preferred model ID")
    force_tier: Optional[int] = Field(None, description="Force tier (1, 2, or 3)")


class BatchRouteRequest(BaseModel):
    items: List[Dict[str, Any]] = Field(..., description="List of {task_type, params} dicts")
    preferred_model: Optional[str] = Field(None, description="Preferred model for all items")


class RegisterModelRequest(BaseModel):
    model_id: str
    tier: int = Field(..., ge=1, le=3)
    available: bool = True


class SetAvailabilityRequest(BaseModel):
    model_id: str
    available: bool


# =========================================================================
# FastAPI Application
# =========================================================================

def create_app(
    hebbian_url: Optional[str] = None,
    hebbian_service: Any = None,
) -> FastAPI:
    """Create the FastAPI app. Importable and testable without starting the server."""

    app = FastAPI(
        title="Fleet Router API",
        description="Critical-angle routing for fleet model computation",
        version="1.0.0",
    )

    # Initialize components
    registry = ModelRegistry()
    stats = RoutingStats()

    # Register default models
    for model_id, tier in DEFAULT_MODELS.items():
        registry.register(model_id, tier)

    # Create router
    hebbian = hebbian_url or "http://localhost:8849"
    router = CriticalAngleRouter(registry, stats, hebbian_url=hebbian)

    # Store hebbian_service reference if provided
    if hebbian_service:
        app.state.hebbian_service = hebbian_service

    # -------------------------------------------------------------------
    # Endpoints
    # -------------------------------------------------------------------

    @app.post("/route", response_model=None)
    async def route_computation(req: RouteRequest):
        """Route a single computation request to the best model."""
        result = router.route_request(
            task_type=req.task_type,
            params=req.params,
            preferred_model=req.preferred_model,
            force_tier=req.force_tier,
        )
        if result.get("rejected"):
            return JSONResponse(content=result, status_code=422)
        return result

    @app.post("/route/batch", response_model=None)
    async def route_batch(req: BatchRouteRequest):
        """Route multiple computations at once, grouped by optimal model."""
        return router.route_batch(req.items, preferred_model=req.preferred_model)

    @app.get("/health")
    async def health():
        """Router status, registered models, and routing stats."""
        return {
            "status": "ok",
            "service": "fleet-router-api",
            "models_registered": len(registry._models),
            "models_available": sum(
                1 for e in registry._models.values() if e.available
            ),
            "translator_available": HAS_TRANSLATOR,
            "hebbian_available": HAS_HEBBIAN,
            "mythos_available": HAS_MYTHOS,
            "routing_stats": stats.snapshot(),
            "models": registry.list_models(),
        }

    @app.get("/models")
    async def list_models():
        """List all registered models with tier info."""
        return {"models": registry.list_models()}

    @app.post("/models/register", response_model=None)
    async def register_model(req: RegisterModelRequest):
        """Register a new model or update an existing one."""
        try:
            tier = ModelTierEnum(req.tier)
        except ValueError:
            raise HTTPException(400, f"Invalid tier: {req.tier}. Must be 1, 2, or 3.")
        entry = registry.register(req.model_id, tier, req.available)
        return {
            "model_id": entry.model_id,
            "tier": entry.tier.value,
            "tier_name": entry.tier.name,
            "available": entry.available,
            "registered": True,
        }

    @app.post("/models/availability", response_model=None)
    async def set_availability(req: SetAvailabilityRequest):
        """Set model availability (mark unavailable if rate-limited)."""
        entry = registry.get(req.model_id)
        if not entry:
            raise HTTPException(404, f"Model not registered: {req.model_id}")
        registry.set_available(req.model_id, req.available)
        return {
            "model_id": req.model_id,
            "available": req.available,
            "updated": True,
        }

    @app.get("/stats")
    async def get_stats():
        """Detailed routing statistics."""
        return stats.snapshot()

    # Expose internals for testing
    app.state.registry = registry
    app.state.stats = stats
    app.state.router = router

    return app


# Create default app instance
app = create_app()


# =========================================================================
# Main
# =========================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("fleet_router_api:app", host="0.0.0.0", port=8100, reload=False)
