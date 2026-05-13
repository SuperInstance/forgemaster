#!/usr/bin/env python3
"""
ExpertRouter — Dynamic MoE-style routing for Lighthouse Runtime

Inspired by Seed-2.0-mini's MoE architecture (230B total / 23B active, 10:1 sparsity),
but applied to model selection rather than token routing.

The router maintains a routing table mapping task types to expert models.
It supports:
  - Static routes: explicit task_type → model mappings
  - Learned routes: embedding-based routing via task embedding → expert mapping
  - Fallback: default model when no route matches
  - Hot-reload: routes can be added/removed at runtime via config file

Config file: lighthouse-runtime/router_config.json
"""

import json
import hashlib
import os
import time
from pathlib import Path
from typing import Optional


BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "router_config.json"

# Default routing table (matches original lighthouse.py TASK_MODEL_MAP)
DEFAULT_ROUTES = {
    "synthesis": "claude",
    "critique": "claude",
    "big_idea": "claude",
    "architecture": "glm",
    "complex_code": "glm",
    "orchestration": "glm",
    "discovery": "seed",
    "exploration": "seed",
    "variation": "seed",
    "drafting": "deepseek",
    "documentation": "deepseek",
    "research": "deepseek",
    "adversarial": "hermes",
    "second_opinion": "hermes",
}

DEFAULT_FALLBACK = "seed"

# Model costs (relative, per 1K queries)
MODEL_COSTS = {
    "claude": 50.0,
    "glm": 5.0,
    "seed": 0.1,
    "deepseek": 0.2,
    "hermes": 0.15,
}


def _hash_embedding(embedding: list) -> str:
    """Stable hash of an embedding vector for learned routing lookup."""
    raw = json.dumps(embedding, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


class ExpertRouter:
    """
    Dynamic MoE router that maps tasks to expert models.
    
    Routing priority:
      1. Learned route (if embedding provided and match found)
      2. Static route (task_type → model)
      3. Fallback model
    
    Learned routing uses task embeddings to map to experts.
    When a task is routed manually and an embedding is provided,
    the mapping is recorded for future learned routing.
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = Path(config_path) if config_path else CONFIG_PATH
        self.routes: dict[str, str] = {}
        self.learned: dict[str, str] = {}  # embedding_hash → model
        self.embedding_index: dict[str, list] = {}  # embedding_hash → raw embedding
        self.fallback: str = DEFAULT_FALLBACK
        self.costs: dict[str, float] = dict(MODEL_COSTS)
        self._load_config()
    
    def _load_config(self):
        """Load routing config from JSON file, creating defaults if missing."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.routes = data.get("routes", dict(DEFAULT_ROUTES))
                self.learned = data.get("learned_routes", {})
                self.embedding_index = data.get("embedding_index", {})
                self.fallback = data.get("fallback", DEFAULT_FALLBACK)
                self.costs = data.get("costs", dict(MODEL_COSTS))
                return
            except (json.JSONDecodeError, KeyError):
                pass  # fall through to defaults
        
        # No config or broken config — use defaults
        self.routes = dict(DEFAULT_ROUTES)
        self.fallback = DEFAULT_FALLBACK
        self._save_config()
    
    def _save_config(self):
        """Persist routing config to JSON file."""
        data = {
            "routes": self.routes,
            "learned_routes": self.learned,
            "embedding_index": self.embedding_index,
            "fallback": self.fallback,
            "costs": self.costs,
            "updated_at": time.time(),
        }
        self.config_path.write_text(json.dumps(data, indent=2))
    
    def orient(self, task: str, task_type: str, embedding: Optional[list] = None) -> dict:
        """
        Route a task to the best expert model.
        
        Args:
            task: The task description
            task_type: Category of the task (e.g., "synthesis", "code")
            embedding: Optional task embedding vector for learned routing
        
        Returns:
            dict with model, routing_method, cost_estimate, task_type
        """
        method = "fallback"
        model = self.fallback
        
        # Priority 1: Learned route via embedding
        if embedding is not None:
            emb_hash = _hash_embedding(embedding)
            if emb_hash in self.learned:
                model = self.learned[emb_hash]
                method = "learned"
        
        # Priority 2: Static route by task_type
        if method == "fallback" and task_type in self.routes:
            model = self.routes[task_type]
            method = "static"
        
        # If we have an embedding but no learned route, record this mapping
        # so future tasks with similar embeddings can benefit
        if embedding is not None and method != "learned":
            emb_hash = _hash_embedding(embedding)
            self.learned[emb_hash] = model
            self.embedding_index[emb_hash] = embedding
            self._save_config()
        
        return {
            "model": model,
            "routing_method": method,
            "cost_estimate": self.costs.get(model, 0.1),
            "task_type": task_type,
            "fallback_used": method == "fallback",
        }
    
    def add_route(self, task_type: str, model: str) -> None:
        """Add or update a static route."""
        self.routes[task_type] = model
        self._save_config()
    
    def remove_route(self, task_type: str) -> bool:
        """Remove a static route. Returns True if it existed."""
        if task_type in self.routes:
            del self.routes[task_type]
            self._save_config()
            return True
        return False
    
    def list_routes(self) -> dict:
        """Return all current routes and their models."""
        return {
            "static_routes": dict(self.routes),
            "learned_count": len(self.learned),
            "fallback": self.fallback,
            "models_available": list(self.costs.keys()),
        }
    
    def set_fallback(self, model: str) -> None:
        """Set the fallback model for unknown task types."""
        self.fallback = model
        self._save_config()
    
    def clear_learned(self) -> int:
        """Clear all learned routes. Returns count cleared."""
        count = len(self.learned)
        self.learned.clear()
        self.embedding_index.clear()
        self._save_config()
        return count
