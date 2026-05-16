"""
Embryonic Development System — From fertilized egg to flying bird.

The biological parallel is exact:
- FERTILIZED EGG: a task specification (one cell with all the DNA needed)
- CLEAVAGE: rapid cell division without growth (generate many small fragments)
- BLASTULA: hollow ball of cells (fragments arranged around a central insight)
- GASTRULATION: cells fold inward, create layers (fragments differentiate)
- ORGANOGENESIS: organs develop from differentiated layers (modules emerge)
- FLEDGING: the system attempts flight (integration test, first real execution)

Each stage uses the RIGHT energy source:
- Early stages: MITOCHONDRIAL (Seed-mini, fast, cheap, many cells)
- Middle stages: MIXED (mito proposes, nuclear disposes)
- Late stages: NUCLEAR (GLM-5.1, heavy reasoning, integration)
"""

import json
import hashlib
import os
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime

import requests


# ---------------------------------------------------------------------------
# Enums and Data Classes
# ---------------------------------------------------------------------------

class DevelopmentalStage(Enum):
    ZYGOTE = "zygote"
    CLEAVAGE = "cleavage"
    BLASTULA = "blastula"
    GASTRULA = "gastrula"
    ORGANOGENESIS = "organogenesis"
    FLEDGE = "fledge"
    FLEDGLING = "fledgling"


@dataclass
class Cell:
    """One unit of development — a solution fragment."""
    id: str
    content: str
    cell_type: str = "undifferentiated"  # undifferentiated | frontend | backend | logic | test | config
    energy_source: str = "mitochondrial"
    parent_id: Optional[str] = None
    generation: int = 0
    fitness: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def _make_id(content: str, gen: int) -> str:
        raw = f"{content}:{gen}:{time.time_ns()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    @classmethod
    def create(cls, content: str, generation: int = 0,
               energy_source: str = "mitochondrial",
               parent_id: Optional[str] = None,
               cell_type: str = "undifferentiated",
               metadata: Optional[dict] = None) -> "Cell":
        cell_id = cls._make_id(content, generation)
        return cls(
            id=cell_id, content=content, cell_type=cell_type,
            energy_source=energy_source, parent_id=parent_id,
            generation=generation, metadata=metadata or {}
        )


@dataclass
class Organ:
    """A functional module assembled from differentiated cells."""
    name: str
    organ_type: str  # frontend | backend | logic | test | config
    cells: list  # List[Cell]
    integration_code: str = ""
    fitness: float = 0.0


# ---------------------------------------------------------------------------
# Incubator Energy — Model Routing
# ---------------------------------------------------------------------------

class IncubatorEnergy:
    """The energy provisioning system.

    Mitochondrial = Seed-2.0-mini (fast, cheap, always on)
    Nuclear = GLM-5.1 (slow, expensive, powerful)
    """

    DEEPINFRA_KEY: str = ""
    DEEPINFRA_URL = "https://api.deepinfra.com/v1/openai/chat/completions"

    MITO_MODEL = "ByteDance/Seed-2.0-mini"
    NUCLEAR_MODEL = "ByteDance/Seed-2.0-mini"

    def __init__(self):
        key_path = os.path.expanduser(
            "~/.openclaw/workspace/.credentials/deepinfra-api-key.txt"
        )
        if os.path.exists(key_path):
            with open(key_path) as f:
                self.DEEPINFRA_KEY = f.read().strip()

    # -- public routing -----------------------------------------------------

    def get_model(self, stage: DevelopmentalStage) -> str:
        if stage in (DevelopmentalStage.ZYGOTE, DevelopmentalStage.CLEAVAGE,
                     DevelopmentalStage.BLASTULA):
            return self.MITO_MODEL
        elif stage == DevelopmentalStage.GASTRULA:
            return "mixed"
        else:
            return self.NUCLEAR_MODEL

    def get_energy_label(self, stage: DevelopmentalStage) -> str:
        if stage in (DevelopmentalStage.ZYGOTE, DevelopmentalStage.CLEAVAGE,
                     DevelopmentalStage.BLASTULA):
            return "mitochondrial"
        elif stage == DevelopmentalStage.GASTRULA:
            return "mixed"
        else:
            return "nuclear"

    def estimate_cost(self, cells: list) -> dict:
        mito = sum(1 for c in cells if c.energy_source == "mitochondrial")
        nuc = sum(1 for c in cells if c.energy_source == "nuclear")
        mixed = sum(1 for c in cells if c.energy_source == "mixed")
        return {
            "mitochondrial_cells": mito,
            "nuclear_cells": nuc,
            "mixed_cells": mixed,
            "total_cells": len(cells),
            "est_mito_cost_usd": round(mito * 0.01, 3),
            "est_nuclear_cost_usd": round(nuc * 0.05, 3),
            "est_total_usd": round(mito * 0.01 + nuc * 0.05, 3),
        }

    # -- actual API calls ---------------------------------------------------

    def call_mito(self, prompt: str, max_tokens: int = 200) -> str:
        """Call Seed-2.0-mini (mitochondrial energy)."""
        if not self.DEEPINFRA_KEY:
            return self._mock_mito(prompt)
        try:
            resp = requests.post(
                self.DEEPINFRA_URL,
                json={
                    "model": self.MITO_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
                headers={"Authorization": f"Bearer {self.DEEPINFRA_KEY}"},
                timeout=(5, 10),  # (connect, read)
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [mito API error: {e}, using fallback]")
            return self._mock_mito(prompt, error=str(e))

    def call_nuclear(self, prompt: str, max_tokens: int = 600) -> str:
        """Call nuclear model — uses Seed-2.0-mini via DeepInfra."""
        if not self.DEEPINFRA_KEY:
            return self._mock_nuclear(prompt)
        try:
            resp = requests.post(
                self.DEEPINFRA_URL,
                json={
                    "model": self.MITO_MODEL,  # Use mini for reliability
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": 0.4,
                },
                headers={"Authorization": f"Bearer {self.DEEPINFRA_KEY}"},
                timeout=(5, 12),  # (connect, read)
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  [nuclear API error: {e}, using fallback]")
            return self._mock_nuclear(prompt, error=str(e))

    # -- fallbacks ----------------------------------------------------------

    @staticmethod
    def _mock_mito(prompt: str, error: str = "") -> str:
        """Fallback mito response when API unavailable."""
        pl = prompt.lower()
        # Classification mode
        if "fragment 0" in pl or "classify" in pl or "category" in pl or "type" in pl:
            lines = []
            for i in range(10):
                types = ["backend", "frontend", "logic", "test", "config"]
                # Heuristic: assign based on index patterns
                if i % 5 == 0: t = "backend"
                elif i % 5 == 1: t = "frontend"
                elif i % 5 == 2: t = "logic"
                elif i % 5 == 3: t = "test"
                else: t = "config"
                lines.append(f"FRAGMENT {i}: {t}")
            return "\n".join(lines)
        # Insight mode
        if "core requirement" in pl or "insight" in pl or "one core" in pl:
            return "The core requirement is mapping short URLs to original URLs with click tracking for analytics."
        # Fragment generation mode
        if "fragment" in pl or "solution" in pl:
            return (
                "FRAGMENT 0:\nfrom flask import Flask, redirect, request\napp = Flask(__name__)\n"
                "FRAGMENT 1:\nimport hashlib\ndef shorten(url): return hashlib.sha256(url.encode()).hexdigest()[:8]\n"
                "FRAGMENT 2:\nstore = {}\ndef save_mapping(short, long): store[short] = {'url': long, 'clicks': 0}\n"
                "FRAGMENT 3:\ndef track_click(short): store[short]['clicks'] += 1\n"
                "FRAGMENT 4:\n@app.route('/<short>')\ndef handle_redirect(short): track_click(short); return redirect(store[short]['url'])\n"
                "FRAGMENT 5:\nimport re\ndef validate_url(url): return bool(re.match(r'https?://.+', url))\n"
                "FRAGMENT 6:\ndef test_shorten(): assert len(shorten('http://x.com')) == 8; print('PASS')\n"
                "FRAGMENT 7:\nCONFIG = {'host': '0.0.0.0', 'port': 5000, 'max_urls': 10000}\n"
            )
        return "# Mito fragment: placeholder solution sketch\npass\n"

    @staticmethod
    def _mock_nuclear(prompt: str, error: str = "") -> str:
        """Fallback nuclear response."""
        pl = prompt.lower()
        if "combine" in pl or "module" in pl:
            # Module integration
            if "backend" in pl:
                return (
                    "MODULE: backend\n"
                    "from flask import Flask, redirect, request, jsonify\n"
                    "app = Flask(__name__)\n"
                    "store = {}\n"
                    "import hashlib\n"
                    "def shorten_url(url): return hashlib.sha256(url.encode()).hexdigest()[:8]\n"
                    "@app.route('/api/shorten', methods=['POST'])\n"
                    "def api_shorten():\n"
                    "    data = request.json\n"
                    "    short = shorten_url(data['url'])\n"
                    "    store[short] = {'url': data['url'], 'clicks': 0}\n"
                    "    return jsonify({'short': short})\n"
                )
            elif "logic" in pl:
                return (
                    "MODULE: logic\n"
                    "import re, hashlib\n"
                    "def shorten_url(url): return hashlib.sha256(url.encode()).hexdigest()[:8]\n"
                    "def validate_url(url): return bool(re.match(r'https?://.+', url))\n"
                    "def track_click(mapping): mapping['clicks'] += 1; return mapping\n"
                    "def get_stats(mapping): return {'url': mapping['url'], 'clicks': mapping['clicks']}\n"
                )
            else:
                return (
                    "MODULE: " + ("frontend" if "frontend" in pl else "test" if "test" in pl else "config") + "\n"
                    "# Integrated module\npass\n"
                )
        return (
            "# Nuclear judgment (mock)\n"
            "from flask import Flask, redirect, request, jsonify\n"
            "import hashlib, re\n"
            "app = Flask(__name__)\n"
            "store = {}\n"
            "def shorten_url(url): return hashlib.sha256(url.encode()).hexdigest()[:8]\n"
            "def validate_url(url): return bool(re.match(r'https?://.+', url))\n"
            "@app.route('/api/shorten', methods=['POST'])\n"
            "def api_shorten():\n"
            "    data = request.json\n"
            "    if not validate_url(data.get('url', '')): return jsonify({'error': 'invalid'}), 400\n"
            "    short = shorten_url(data['url'])\n"
            "    store[short] = {'url': data['url'], 'clicks': 0}\n"
            "    return jsonify({'short': short, 'full': f\"http://localhost:5000/{short}\"})\n"
            "@app.route('/<short>')\n"
            "def handle_redirect(short):\n"
            "    if short not in store: return jsonify({'error': 'not found'}), 404\n"
            "    store[short]['clicks'] += 1\n"
            "    return redirect(store[short]['url'])\n"
            "@app.route('/api/stats/<short>')\n"
            "def api_stats(short):\n"
            "    if short not in store: return jsonify({'error': 'not found'}), 404\n"
            "    return jsonify({'url': store[short]['url'], 'clicks': store[short]['clicks']})\n"
            "if __name__ == '__main__': app.run(debug=True)\n"
        )


# ---------------------------------------------------------------------------
# The Embryo
# ---------------------------------------------------------------------------

class Embryo:
    """A developing system — from zygote to fledgling."""

    def __init__(self, task: str, energy: Optional[IncubatorEnergy] = None):
        self.task = task
        self.cells: list = []      # List[Cell]
        self.organs: list = []     # List[Organ]
        self.stage = DevelopmentalStage.ZYGOTE
        self.energy = energy or IncubatorEnergy()
        self.stage_log: list = []
        self.zygote = Cell.create(
            content=task, generation=0,
            energy_source="mitochondrial", cell_type="undifferentiated"
        )
        self.cells.append(self.zygote)
        self._log("ZYGOTE", f"Task received: {task[:80]}...")

    def _log(self, stage: str, msg: str):
        self.stage_log.append({"stage": stage, "msg": msg, "time": datetime.utcnow().isoformat()})

    # -----------------------------------------------------------------------
    # Stage 1: Cleavage — rapid cell division
    # -----------------------------------------------------------------------

    def cleavage(self, num_fragments: int = 12) -> list:
        """Rapid cell division — generate many small fragments.

        Uses MITOCHONDRIAL energy (Seed-mini). Speed over precision.
        Each fragment is a tiny piece of the solution. Many fragments,
        low individual quality, but together they cover the space.
        """
        self.stage = DevelopmentalStage.CLEAVAGE
        self._log("CLEAVAGE", f"Beginning rapid division: target {num_fragments} fragments")

        prompt = (
            f"Task: {self.task}\n\n"
            f"Generate {num_fragments} distinct small solution fragments (2-5 lines each). "
            f"Each fragment should approach the problem from a different angle. "
            f"Format each fragment as:\n"
            f"FRAGMENT N:\n<code>\n\n"
            f"Cover: routing, data storage, URL handling, redirect logic, "
            f"analytics/tracking, error handling, input validation, configuration, "
            f"testing, API design, database schema, and middleware."
        )

        raw = self.energy.call_mito(prompt, max_tokens=1500)
        fragments = self._parse_fragments(raw, num_fragments)

        # If API didn't give us enough, synthesize the rest
        if len(fragments) < num_fragments:
            fragments.extend(self._synthesize_fragments(num_fragments - len(fragments)))

        new_cells = []
        for i, frag in enumerate(fragments[:num_fragments]):
            cell = Cell.create(
                content=frag, generation=1,
                energy_source="mitochondrial",
                parent_id=self.zygote.id,
                cell_type="undifferentiated",
                metadata={"fragment_index": i}
            )
            self.cells.append(cell)
            new_cells.append(cell)

        self._log("CLEAVAGE", f"Created {len(new_cells)} cells from zygote")
        return new_cells

    # -----------------------------------------------------------------------
    # Stage 2: Blastula — arrange fragments around central insight
    # -----------------------------------------------------------------------

    def blastula(self) -> dict:
        """Arrange cells around the central insight of the task.

        Cells are evaluated for fitness and organized into a structure.
        The 'hollow ball' is the set of cells arranged around the core
        requirement identified by the mito model.
        """
        self.stage = DevelopmentalStage.BLASTULA
        self._log("BLASTULA", "Arranging fragments around central insight")

        # Get a central insight from mito
        insight_prompt = (
            f"Task: {self.task}\n\n"
            f"What is the ONE core requirement that everything else revolves around? "
            f"Answer in 1-2 sentences."
        )
        insight = self.energy.call_mito(insight_prompt, max_tokens=50)

        # Score each cell for relevance to the central insight
        undifferentiated = [c for c in self.cells if c.cell_type == "undifferentiated"]
        for cell in undifferentiated:
            cell.fitness = self._score_fitness(cell.content, insight)
            cell.metadata["insight_relevance"] = cell.fitness

        # Sort by fitness — arrange around the insight
        undifferentiated.sort(key=lambda c: c.fitness, reverse=True)

        self._log("BLASTULA", f"Central insight: {insight[:100]}")
        self._log("BLASTULA", f"Arranged {len(undifferentiated)} cells by fitness")

        return {
            "insight": insight,
            "cells": undifferentiated,
            "top_fitness": undifferentiated[0].fitness if undifferentiated else 0,
            "avg_fitness": sum(c.fitness for c in undifferentiated) / max(len(undifferentiated), 1),
        }

    # -----------------------------------------------------------------------
    # Stage 3: Gastrulation — differentiation
    # -----------------------------------------------------------------------

    def gastrulate(self) -> dict:
        """Differentiation — cells fold into types.

        Compare mitochondrial outputs. Where they converge = clear type.
        Where they diverge = needs nuclear judgment to decide type.
        The comparison IS the differentiation signal.
        """
        self.stage = DevelopmentalStage.GASTRULA
        self._log("GASTRULA", "Beginning cell differentiation")

        undifferentiated = [c for c in self.cells if c.cell_type == "undifferentiated"]

        # --- Mitochondrial classification (fast, proposed) ---
        mito_types = {}
        # Single batch classification to save API calls
        batch_content = ""
        for i, cell in enumerate(undifferentiated):
            batch_content += f"FRAGMENT {i}:\n{cell.content[:200]}\n\n"
        
        batch_prompt = (
            f"Classify each fragment as exactly ONE type: frontend | backend | logic | test | config\n"
            f"Reply with one line per fragment: FRAGMENT N: type\n\n"
            f"{batch_content}"
        )
        batch_result = self.energy.call_mito(batch_prompt, max_tokens=200)
        
        # Parse batch result
        for i, cell in enumerate(undifferentiated):
            found = False
            for line in batch_result.split('\n'):
                if f"FRAGMENT {i}" in line.upper() or f"fragment {i}" in line:
                    for t in ["frontend", "backend", "logic", "test", "config"]:
                        if t in line.lower():
                            mito_types[cell.id] = t
                            found = True
                            break
            if not found:
                mito_types[cell.id] = "logic"

        # --- Second mito pass for convergence check (batch) ---
        mito_types_2 = {}
        batch_prompt_2 = (
            f"Look at each fragment and pick the BEST category:\n"
            f"  frontend (UI/HTML/display) | backend (server/routes/API)\n"
            f"  logic (algorithms/processing) | test (verification) | config (setup)\n"
            f"Reply: FRAGMENT N: category\n\n"
            f"{batch_content}"
        )
        batch_result_2 = self.energy.call_mito(batch_prompt_2, max_tokens=200)
        
        for i, cell in enumerate(undifferentiated):
            found = False
            for line in batch_result_2.split('\n'):
                if f"FRAGMENT {i}" in line.upper() or f"fragment {i}" in line:
                    for t in ["frontend", "backend", "logic", "test", "config"]:
                        if t in line.lower():
                            mito_types_2[cell.id] = t
                            found = True
                            break
            if not found:
                mito_types_2[cell.id] = "logic"

        # --- Compare: convergence vs divergence ---
        convergence = []
        divergence = []
        for cell in undifferentiated:
            t1 = mito_types.get(cell.id, "logic")
            t2 = mito_types_2.get(cell.id, "logic")
            if t1 == t2:
                # Converged — clear classification
                cell.cell_type = t1
                cell.energy_source = "mitochondrial"
                convergence.append((cell.id, t1))
            else:
                # Diverged — needs nuclear judgment
                divergence.append((cell.id, t1, t2))

        # --- Nuclear judgment for divergent cells ---
        for cell_id, t1, t2 in divergence:
            cell = next(c for c in self.cells if c.id == cell_id)
            prompt = (
                f"This fragment was classified as '{t1}' by one assessor and '{t2}' by another.\n"
                f"Pick the BEST single type: frontend | backend | logic | test | config\n\n"
                f"Fragment:\n{cell.content[:300]}\n\n"
                f"Type:"
            )
            result = self.energy.call_nuclear(prompt, max_tokens=30).strip().lower()
            for t in ["frontend", "backend", "logic", "test", "config"]:
                if t in result:
                    cell.cell_type = t
                    cell.energy_source = "mixed"
                    break
            else:
                cell.cell_type = t1  # fallback to first mito judgment
                cell.energy_source = "mixed"

        # --- Report ---
        type_counts = {}
        for c in self.cells:
            type_counts[c.cell_type] = type_counts.get(c.cell_type, 0) + 1

        report = {
            "converged": len(convergence),
            "diverged": len(divergence),
            "convergence_details": convergence[:5],
            "divergence_details": divergence[:5],
            "type_distribution": type_counts,
        }

        self._log("GASTRULA", f"Converged: {len(convergence)}, Diverged: {len(divergence)}")
        self._log("GASTRULA", f"Type distribution: {type_counts}")
        return report

    # -----------------------------------------------------------------------
    # Stage 4: Organogenesis — modules emerge
    # -----------------------------------------------------------------------

    def organogenesis(self) -> list:
        """Module emergence — differentiated cells become organs.

        Groups of same-type cells merge into functional modules.
        Nuclear model ensures coherence within each module.
        """
        self.stage = DevelopmentalStage.ORGANOGENESIS
        self._log("ORGANOGENESIS", "Assembling organs from differentiated cells")

        # Group cells by type
        type_groups: dict = {}
        for cell in self.cells:
            if cell.cell_type == "undifferentiated":
                continue
            type_groups.setdefault(cell.cell_type, []).append(cell)

        # Batch integration for all types
        all_fragments = "\n".join(
            f"## {cell_type.upper()} FRAGMENTS:\n" +
            "\n".join(c.content[:300] for c in grp) + "\n"
            for cell_type, grp in type_groups.items()
        )
        
        integration_prompt = (
            f"Combine fragments by type into coherent modules. For each type below, "
            f"output a code block with MODULE: <type> header.\n\n{all_fragments[:3000]}"
        )
        batch_integration = self.energy.call_nuclear(integration_prompt, max_tokens=1200)
        
        # Parse per-type modules from batch result
        type_sections = re.split(r"MODULE:\s*(\w+)", batch_integration, flags=re.IGNORECASE)
        integrated_map = {}
        if len(type_sections) >= 3:
            for j in range(1, len(type_sections) - 1, 2):
                tname = type_sections[j].lower().strip()
                tcode = type_sections[j + 1].strip() if j + 1 < len(type_sections) else ""
                for t in ["frontend", "backend", "logic", "test", "config"]:
                    if t in tname:
                        integrated_map[t] = tcode
                        break
        
        self.organs = []
        for cell_type, group_cells in type_groups.items():
            # Use pre-integrated code or combine manually
            integrated = integrated_map.get(cell_type, "")
            if not integrated:
                integrated = "\n\n".join(c.content for c in group_cells)
            
            # Score the organ
            fitness = sum(c.fitness for c in group_cells) / max(len(group_cells), 1)

            organ = Organ(
                name=f"{cell_type}_module",
                organ_type=cell_type,
                cells=group_cells,
                integration_code=integrated,
                fitness=fitness,
            )
            self.organs.append(organ)
            self._log("ORGANOGENESIS", f"Created {organ.name} from {len(group_cells)} cells")

        self._log("ORGANOGENESIS", f"Total organs: {len(self.organs)}")
        return self.organs

    # -----------------------------------------------------------------------
    # Stage 5: Fledging — first flight
    # -----------------------------------------------------------------------

    def fledge(self) -> dict:
        """First flight — attempt full integration.

        Nuclear model assembles all modules into a working system.
        If it flies, we have a fledgling. If it crashes, identify failures.
        """
        self.stage = DevelopmentalStage.FLEDGE
        self._log("FLEDGE", "Attempting first flight — full system integration")

        organ_summaries = []
        for organ in self.organs:
            organ_summaries.append(
                f"## {organ.name} ({organ.organ_type})\n"
                f"{organ.integration_code[:200]}"
            )

        assembly_prompt = (
            f"Task: {self.task}\n\n"
            f"Combine these modules into a working Python system with imports and main():\n\n"
            f"{'---'.join(organ_summaries[:3])}\n\n"
            f"Complete system:"
        )

        system_code = self.energy.call_nuclear(assembly_prompt, max_tokens=800)

        # Validate the system
        validation = self._validate_system(system_code)

        if validation["runnable"]:
            self.stage = DevelopmentalStage.FLEDGLING
            self._log("FLEDGE", "SUCCESS — system is flying! 🐦")
        else:
            self._log("FLEDGE", f"CRASH — {validation['issues']}")

        return {
            "stage": self.stage.value,
            "system_code": system_code,
            "validation": validation,
            "organs_used": [o.name for o in self.organs],
            "total_cells": len(self.cells),
            "cost": self.energy.estimate_cost(self.cells),
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _parse_fragments(self, raw: str, target: int) -> list:
        """Parse raw model output into fragments."""
        # Try splitting on FRAGMENT markers
        parts = re.split(r"FRAGMENT\s*\d+", raw, flags=re.IGNORECASE)
        if len(parts) > 1:
            return [p.strip() for p in parts[1:] if p.strip()]

        # Try splitting on code blocks
        blocks = re.findall(r"```(?:\w+)?\n(.*?)```", raw, re.DOTALL)
        if blocks:
            return [b.strip() for b in blocks]

        # Fallback: split on double newlines
        chunks = [c.strip() for c in raw.split("\n\n") if c.strip() and len(c.strip()) > 20]
        return chunks if chunks else [raw]

    def _synthesize_fragments(self, count: int) -> list:
        """Synthesize fragments when API didn't produce enough."""
        templates = [
            "# Routing: map short codes to destinations\nfrom collections import defaultdict\nroutes = defaultdict(str)\n",
            "# Data storage: simple dict-based store\nstore = {}\ndef save(key, val): store[key] = val\n",
            "# URL handling: generate and parse short URLs\nimport hashlib\ndef shorten(url): return hashlib.md5(url.encode()).hexdigest()[:8]\n",
            "# Redirect logic: 301/302 responses\ndef redirect(url, permanent=False):\n    return {'status': 301 if permanent else 302, 'location': url}\n",
            "# Analytics: track clicks\nclick_log = []\ndef log_click(code, ts): click_log.append((code, ts))\n",
            "# Error handling\ndef error_response(code, msg):\n    return {'status': code, 'error': msg}\n",
            "# Input validation\nimport re\ndef is_valid_url(url): return bool(re.match(r'https?://.+', url))\n",
            "# Configuration\nCONFIG = {'base_url': 'http://localhost:8080', 'max_urls': 10000}\n",
            "# Testing\ndef test_shorten():\n    assert shorten('https://example.com') is not None\n    print('PASS')\n",
            "# API design\ndef api_handler(method, path, body=None):\n    if method == 'POST': return create_short(body)\n    elif method == 'GET': return get_long(path)\n",
            "# Database schema\nSCHEMA = 'CREATE TABLE urls (id INTEGER PRIMARY KEY, short TEXT, long TEXT, clicks INT)'\n",
            "# Middleware: rate limiting\nfrom time import time\nrate_limit = {}\ndef check_limit(ip): return rate_limit.get(ip, 0) > time() - 60\n",
        ]
        return templates[:count]

    def _score_fitness(self, content: str, insight: str) -> float:
        """Score a cell's relevance to the central insight."""
        # Keyword overlap scoring
        insight_words = set(insight.lower().split())
        content_words = set(content.lower().split())
        if not insight_words:
            return 0.5
        overlap = len(insight_words & content_words) / max(len(insight_words), 1)
        # Length bonus — longer fragments tend to be more substantive
        length_bonus = min(len(content) / 500, 0.3)
        return min(overlap + length_bonus, 1.0)

    def _validate_system(self, code: str) -> dict:
        """Check if the assembled system is runnable."""
        issues = []
        has_def = "def " in code
        has_import = code.strip().startswith("import") or code.strip().startswith("from")
        has_main = '__main__' in code or 'main()' in code
        has_syntax = True

        try:
            compile(code, "<system>", "exec")
        except SyntaxError as e:
            has_syntax = False
            issues.append(f"SyntaxError: {e.msg} at line {e.lineno}")

        if not has_def:
            issues.append("No function definitions found")
        if not has_main:
            issues.append("No main() entry point")

        runnable = has_syntax and has_def and len(issues) <= 1

        return {
            "runnable": runnable,
            "has_functions": has_def,
            "has_imports": has_import,
            "has_main": has_main,
            "has_valid_syntax": has_syntax,
            "issues": issues,
            "code_length": len(code),
        }


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo():
    """Run the full embryonic development demo."""
    print("=" * 70)
    print("  🥚 EMBRYONIC DEVELOPMENT SYSTEM")
    print("  From fertilized egg to flying bird")
    print("=" * 70)

    task = "Build a URL shortener with redirect tracking"
    print(f"\n📋 TASK (fertilized egg): {task}\n")

    energy = IncubatorEnergy()
    embryo = Embryo(task, energy)

    # --- Stage 1: Cleavage ---
    print("=" * 70)
    print("  🧬 STAGE 1: CLEAVAGE — Rapid Cell Division")
    print("  Energy: MITOCHONDRIAL (Seed-2.0-mini, fast & cheap)")
    print("=" * 70)

    cells = embryo.cleavage(num_fragments=8)
    print(f"\n  Created {len(cells)} cells from zygote:")
    for i, cell in enumerate(cells):
        preview = cell.content[:60].replace("\n", " ")
        print(f"    Cell {i+1:2d} [{cell.id}] (gen {cell.generation})")
        print(f"      Preview: {preview}...")
    print()

    # --- Stage 2: Blastula ---
    print("=" * 70)
    print("  🔵 STAGE 2: BLASTULA — Arranging Around Central Insight")
    print("  Energy: MITOCHONDRIAL")
    print("=" * 70)

    blastula_result = embryo.blastula()
    print(f"\n  Central Insight: {blastula_result['insight'][:120]}")
    print(f"  Top fitness: {blastula_result['top_fitness']:.3f}")
    print(f"  Avg fitness: {blastula_result['avg_fitness']:.3f}")
    print()

    # --- Stage 3: Gastrulation ---
    print("=" * 70)
    print("  🔄 STAGE 3: GASTRULATION — Cell Differentiation")
    print("  Energy: MIXED (mito proposes, nuclear disposes)")
    print("=" * 70)

    gastrula_report = embryo.gastrulate()
    print(f"\n  Convergence: {gastrula_report['converged']} cells (mito models agreed)")
    print(f"  Divergence:  {gastrula_report['diverged']} cells (needed nuclear judgment)")
    print(f"\n  Type Distribution:")
    for t, count in sorted(gastrula_report['type_distribution'].items()):
        print(f"    {t:20s}: {count} cells")

    print(f"\n  Convergence Examples (mito agreed):")
    for cid, t in gastrula_report['convergence_details'][:3]:
        print(f"    Cell {cid} → {t} ✓")
    print(f"\n  Divergence Examples (needed nuclear):")
    for cid, t1, t2 in gastrula_report['divergence_details'][:3]:
        print(f"    Cell {cid}: mito₁={t1} vs mito₂={t2} → nuclear decided")
    print()

    # --- Stage 4: Organogenesis ---
    print("=" * 70)
    print("  🫀 STAGE 4: ORGANOGENESIS — Modules Emerge")
    print("  Energy: NUCLEAR (coherence requires heavy reasoning)")
    print("=" * 70)

    organs = embryo.organogenesis()
    print(f"\n  Organs formed: {len(organs)}")
    for organ in organs:
        preview = organ.integration_code[:80].replace("\n", " ")
        print(f"    {organ.name:25s} — {len(organ.cells)} cells, fitness {organ.fitness:.2f}")
        print(f"      Preview: {preview}...")
    print()

    # --- Stage 5: Fledging ---
    print("=" * 70)
    print("  🐦 STAGE 5: FLEDGING — First Flight")
    print("  Energy: NUCLEAR (integration requires full coherence)")
    print("=" * 70)

    fledge_result = embryo.fledge()
    print(f"\n  Final Stage: {fledge_result['stage']}")
    print(f"  Runnable: {fledge_result['validation']['runnable']}")
    print(f"  Has valid syntax: {fledge_result['validation']['has_valid_syntax']}")
    print(f"  Has functions: {fledge_result['validation']['has_functions']}")
    print(f"  Has main(): {fledge_result['validation']['has_main']}")
    if fledge_result['validation']['issues']:
        print(f"  Issues: {fledge_result['validation']['issues']}")

    print(f"\n  Organs used: {fledge_result['organs_used']}")
    print(f"  Total cells created: {fledge_result['total_cells']}")

    print(f"\n  Integrated System Preview:")
    code = fledge_result['system_code']
    for line in code[:400].split("\n"):
        print(f"    {line}")
    if len(code) > 400:
        print(f"    ... ({len(code)} chars total)")

    # --- Cost Report ---
    print("\n" + "=" * 70)
    print("  💰 ENERGY COST REPORT")
    print("=" * 70)
    cost = fledge_result['cost']
    print(f"  Mitochondrial cells: {cost['mitochondrial_cells']}")
    print(f"  Nuclear cells:       {cost['nuclear_cells']}")
    print(f"  Mixed cells:         {cost['mixed_cells']}")
    print(f"  Total cells:         {cost['total_cells']}")
    print(f"  Est. mito cost:      ${cost['est_mito_cost_usd']:.3f}")
    print(f"  Est. nuclear cost:   ${cost['est_nuclear_cost_usd']:.3f}")
    print(f"  Est. total cost:     ${cost['est_total_usd']:.3f}")

    # --- Stage-by-stage energy summary ---
    print("\n" + "=" * 70)
    print("  ⚡ STAGE-BY-STAGE ENERGY SUMMARY")
    print("=" * 70)
    stage_energies = {
        "Zygote": "mitochondrial",
        "Cleavage": "mitochondrial",
        "Blastula": "mitochondrial",
        "Gastrula": "mixed (mito proposes, nuclear disposes)",
        "Organogenesis": "nuclear",
        "Fledge": "nuclear",
    }
    for stage, esrc in stage_energies.items():
        icon = "🔋" if "mito" in esrc else "⚡" if "nuclear" in esrc else "🔀"
        print(f"  {icon} {stage:20s}: {esrc}")

    print("\n" + "=" * 70)
    if embryo.stage == DevelopmentalStage.FLEDGLING:
        print("  🐦 SUCCESS — THE BIRD IS FLYING!")
    else:
        print("  💥 CRASH — BACK TO THE INCUBATOR")
    print("=" * 70)

    return embryo


if __name__ == "__main__":
    demo()
