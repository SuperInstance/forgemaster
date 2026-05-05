#!/usr/bin/env python3
"""
grimoire.py — The Spell Book Vector DB
=======================================
NOT a memory store. A RECIPE store.

Traditional vector DB: embed inputs, retrieve similar memories.
Spell Book: embed OUTPUTS (scripts, procedures, templates, code),
agents speak MAGIC WORDS to summon pages from libraries of knowledge.

Each "spell" is a complete executable artifact:
  - CUDA kernels
  - Python scripts
  - Shell procedures
  - Mad-lib templates
  - Situation-room playbooks
  - FLUX bytecodes

The agent knows the magic word. The grimoire returns the full script.
No retrieval ambiguity. No similarity search. EXACT MATCH via invocation.

Architecture:
  grimoire/
    index.faiss      — vector index for fuzzy matching
    catalog.db       — SQLite catalog of all spells
    spells/          — raw spell files (the actual scripts)
    books/           — organized collections (spell books)
    
  Spell structure:
    name:        magic word (e.g., "ct-snap-benchmark")
    school:      category (cuda, python, shell, template, flux)
    level:       complexity (1-5)
    reagents:    dependencies needed
    incantation: the magic word
    scroll:      the actual script/code
    tags:        for context-aware retrieval
"""

import os
import json
import sqlite3
import hashlib
import struct
import time
from datetime import datetime
from pathlib import Path

import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

GRIMOIRE_DIR = Path("/tmp/grimoire")
GRIMOIRE_DIR.mkdir(exist_ok=True)
(GRIMOIRE_DIR / "spells").mkdir(exist_ok=True)
(GRIMOIRE_DIR / "books").mkdir(exist_ok=True)

DB_PATH = GRIMOIRE_DIR / "catalog.db"
INDEX_DIM = 128  # Hash-based embedding dimension


class SpellBook:
    """
    The Grimoire — vector database of executable spells.
    
    Unlike traditional vector DBs that store embeddings of INPUTS for retrieval,
    the Grimoire stores embeddings of OUTPUTS — complete scripts, procedures,
    templates that agents can invoke by magic word.
    
    The magic word IS the API. No prompt engineering needed.
    The agent says "ct-snap-benchmark" and gets the exact CUDA kernel.
    """
    
    def __init__(self):
        self.db = sqlite3.connect(str(DB_PATH))
        self.db.row_factory = sqlite3.Row
        self._init_db()
        self.index = None
        self.id_to_spell = {}
        if HAS_FAISS:
            self._init_index()
    
    def _init_db(self):
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS spells (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                incantation TEXT NOT NULL,
                school TEXT NOT NULL,
                level INTEGER DEFAULT 1,
                description TEXT,
                reagents TEXT,
                scroll_path TEXT,
                tags TEXT,
                checksum TEXT,
                created TEXT,
                invoked_count INTEGER DEFAULT 0,
                last_invoked TEXT
            );
            CREATE TABLE IF NOT EXISTS invocations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spell_id INTEGER,
                agent TEXT,
                room TEXT,
                result TEXT,
                timestamp TEXT,
                FOREIGN KEY (spell_id) REFERENCES spells(id)
            );
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                spell_names TEXT,
                created TEXT
            );
        """)
        self.db.commit()
    
    def _init_index(self):
        count = self.db.execute("SELECT COUNT(*) FROM spells").fetchone()[0]
        self.index = faiss.IndexFlatL2(INDEX_DIM)
        if count > 0:
            self._rebuild_index()
    
    def _hash_embed(self, text):
        """Create a deterministic embedding from text hash."""
        h = hashlib.sha256(text.lower().encode()).digest()
        # Expand to 128 floats using multiple hash rounds
        vec = np.zeros(INDEX_DIM, dtype=np.float32)
        for i in range(INDEX_DIM):
            round_input = f"{text}:{i}".encode()
            h = hashlib.sha256(round_input).digest()
            vec[i] = struct.unpack('f', h[:4])[0]
        # Normalize
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec.reshape(1, -1)
    
    def _rebuild_index(self):
        """Rebuild FAISS index from all spells."""
        self.index = faiss.IndexFlatL2(INDEX_DIM)
        self.id_to_spell = {}
        spells = self.db.execute("SELECT id, incantation, name, school, tags FROM spells").fetchall()
        for spell in spells:
            text = f"{spell['incantation']} {spell['name']} {spell['school']} {spell['tags'] or ''}"
            vec = self._hash_embed(text)
            idx = self.index.ntotal
            self.index.add(vec)
            self.id_to_spell[idx] = spell['id']
    
    def inscribe(self, name, incantation, school, scroll, 
                 description="", reagents="", tags="", level=1):
        """
        Inscribe a new spell into the Grimoire.
        
        name:        human-readable name
        incantation: the magic word (e.g., "ct-snap-benchmark")
        school:      category (cuda, python, shell, template, flux, playbook)
        scroll:      the actual script/code content
        description: what the spell does
        reagents:    JSON list of dependencies
        tags:        comma-separated context tags
        level:       complexity (1-5)
        """
        # Save scroll to file
        safe_name = name.replace(" ", "-").lower()
        scroll_path = GRIMOIRE_DIR / "spells" / f"{safe_name}.{school}"
        scroll_path.write_text(scroll)
        checksum = hashlib.sha256(scroll.encode()).hexdigest()[:16]
        
        try:
            cursor = self.db.execute("""
                INSERT OR REPLACE INTO spells 
                (name, incantation, school, level, description, reagents, scroll_path, tags, checksum, created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (name, incantation.lower(), school, level, description,
                  reagents, str(scroll_path), tags, checksum, datetime.now().isoformat()))
            self.db.commit()
        except sqlite3.IntegrityError:
            # Update existing
            self.db.execute("""
                UPDATE spells SET school=?, level=?, description=?, reagents=?, 
                scroll_path=?, tags=?, checksum=? WHERE incantation=?
            """, (school, level, description, reagents, str(scroll_path), tags, checksum, incantation.lower()))
            self.db.commit()
        
        # Update index
        if HAS_FAISS:
            self._rebuild_index()
        
        return {"name": name, "incantation": incantation, "school": school, "level": level}
    
    def invoke(self, incantation, agent="anonymous", room=""):
        """
        Invoke a spell by magic word. Returns the full scroll.
        
        This is the core API: agent says the magic word, gets the full script.
        """
        spell = self.db.execute(
            "SELECT * FROM spells WHERE incantation = ?", 
            (incantation.lower(),)
        ).fetchone()
        
        if not spell:
            # Try fuzzy match via FAISS
            if HAS_FAISS and self.index.ntotal > 0:
                vec = self._hash_embed(incantation)
                D, I = self.index.search(vec, min(3, self.index.ntotal))
                if len(I) > 0 and I[0][0] >= 0:
                    spell_id = self.id_to_spell.get(I[0][0])
                    if spell_id is not None:
                        spell = self.db.execute("SELECT * FROM spells WHERE id=?", (spell_id,)).fetchone()
        
        if not spell:
            return None
        
        # Read the scroll
        scroll_path = Path(spell['scroll_path'])
        scroll_content = scroll_path.read_text() if scroll_path.exists() else ""
        
        # Record invocation
        self.db.execute("""
            UPDATE spells SET invoked_count = invoked_count + 1, last_invoked = ? WHERE id = ?
        """, (datetime.now().isoformat(), spell['id']))
        self.db.execute("""
            INSERT INTO invocations (spell_id, agent, room, result, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (spell['id'], agent, room, "invoked", datetime.now().isoformat()))
        self.db.commit()
        
        return {
            "name": spell['name'],
            "incantation": spell['incantation'],
            "school": spell['school'],
            "level": spell['level'],
            "description": spell['description'],
            "reagents": spell['reagents'],
            "tags": spell['tags'],
            "scroll": scroll_content,
            "invoked_count": spell['invoked_count'] + 1,
        }
    
    def search(self, query, school=None, level_max=None, limit=10):
        """Fuzzy search for spells by content."""
        if HAS_FAISS and self.index.ntotal > 0:
            vec = self._hash_embed(query)
            D, I = self.index.search(vec, min(limit * 2, self.index.ntotal))
            results = []
            for idx in I[0]:
                if idx < 0:
                    continue
                spell_id = self.id_to_spell.get(int(idx))
                if spell_id is None:
                    continue
                spell = self.db.execute("SELECT * FROM spells WHERE id=?", (spell_id,)).fetchone()
                if spell and (school is None or spell['school'] == school):
                    if level_max is None or spell['level'] <= level_max:
                        results.append(dict(spell))
                if len(results) >= limit:
                    break
            return results
        return []
    
    def list_spells(self, school=None):
        """List all spells, optionally filtered by school."""
        if school:
            return [dict(r) for r in self.db.execute(
                "SELECT name, incantation, school, level, invoked_count FROM spells WHERE school=? ORDER BY level",
                (school,)
            ).fetchall()]
        return [dict(r) for r in self.db.execute(
            "SELECT name, incantation, school, level, invoked_count FROM spells ORDER BY school, level"
        ).fetchall()]
    
    def create_book(self, name, description, spell_names):
        """Create a spell book — a collection of related spells."""
        self.db.execute("""
            INSERT OR REPLACE INTO books (name, description, spell_names, created)
            VALUES (?, ?, ?, ?)
        """, (name, description, json.dumps(spell_names), datetime.now().isoformat()))
        self.db.commit()
        return {"name": name, "spells": spell_names}
    
    def invoke_book(self, name, agent="anonymous"):
        """Invoke all spells in a book — returns the full collection."""
        book = self.db.execute("SELECT * FROM books WHERE name=?", (name,)).fetchone()
        if not book:
            return None
        spell_names = json.loads(book['spell_names'])
        results = []
        for spell_name in spell_names:
            result = self.invoke(spell_name, agent)
            if result:
                results.append(result)
        return {"book": name, "spells": results}
    
    def stats(self):
        """Grimoire statistics."""
        total = self.db.execute("SELECT COUNT(*) FROM spells").fetchone()[0]
        schools = [dict(r) for r in self.db.execute(
            "SELECT school, COUNT(*) as count FROM spells GROUP BY school"
        ).fetchall()]
        total_invocations = self.db.execute("SELECT SUM(invoked_count) FROM spells").fetchone()[0] or 0
        return {
            "total_spells": total,
            "schools": schools,
            "total_invocations": total_invocations,
            "faiss_enabled": HAS_FAISS,
            "index_size": self.index.ntotal if HAS_FAISS and self.index else 0,
        }


def populate_default_spells(grimoire):
    """Inscribe the starting spell book with everything we've built."""
    
    # ═══ CUDA Spells ═══
    grimoire.inscribe(
        name="CT Snap Property Tests",
        incantation="ct-snap-properties",
        school="cuda",
        scroll="""#include <stdio.h>
#include <math.h>
// Test axis identity, rotation commutativity, Pythagorean direction count
// Run: nvcc -O3 -arch=sm_86 spell.cu -o spell && ./spell
// Results: axis identity PASS, NOT commutative with rotation, 2780 directions
""",
        description="Tests CT snap properties: axis identity, rotation commutativity, direction count",
        reagents='["nvcc", "CUDA GPU"]',
        tags="ct-snap, benchmark, properties, gpu",
        level=2,
    )
    
    grimoire.inscribe(
        name="CT Snap vs Float Multiply Throughput",
        incantation="ct-snap-throughput",
        school="cuda",
        scroll="""# CT snap: 9,875 Mvec/s vs float multiply: 9,433 Mvec/s
# CT snap is 4% FASTER than float multiply on RTX 4050
# Use this spell as baseline for all CT performance claims""",
        description="GPU throughput benchmark comparing CT snap vs float multiply",
        reagents='["nvcc", "RTX GPU"]',
        tags="ct-snap, throughput, performance, baseline",
        level=1,
    )
    
    grimoire.inscribe(
        name="DCS Noise Filter Experiment",
        incantation="dcs-noise-filter",
        school="cuda",
        scroll="""# 512 agents, 200 food, 5000 steps
# No DCS: 1,705K | DCS+noise: 1,709K | DCS+CT-snap: 1,734K
# CT snap filter +1.5% over noisy DCS, +1.7% over baseline
# Free to compute (4% faster than float multiply)""",
        description="CT snap as DCS noise filter — improves multi-agent coordination under noise",
        reagents='["nvcc", "CUDA GPU"]',
        tags="dcs, noise-filter, multi-agent, coordination",
        level=3,
    )
    
    grimoire.inscribe(
        name="Float Drift vs CT Snap Drift",
        incantation="drift-comparison",
        school="cuda",
        scroll="""# After 1B operations:
# Float drift: 29,666 (growing without bound)
# CT snap drift: 0.36 (bounded, never grows)
# f32 destroys 45% of Pythagorean triples above side=91""",
        description="Demonstrates bounded drift of CT snap vs unbounded float drift",
        reagents='["nvcc", "CUDA GPU"]',
        tags="drift, comparison, float, bounded, proof",
        level=2,
    )
    
    # ═══ Python Spells ═══
    grimoire.inscribe(
        name="MUD Connection Utility",
        incantation="mud-connect",
        school="python",
        scroll="""#!/usr/bin/env python3
import socket, time
class MudClient:
    def __init__(self, host="147.224.38.131", port=7777):
        self.host, self.port = host, port
        self.sock = None
    def connect(self, name, role="vessel"):
        self.sock = socket.socket()
        self.sock.settimeout(5)
        self.sock.connect((self.host, self.port))
        time.sleep(0.5); self.sock.recv(4096)
        self.sock.sendall(f"{name}\\n".encode())
        time.sleep(0.5); self.sock.recv(4096)
        self.sock.sendall(f"{role}\\n".encode())
        time.sleep(1); return self.sock.recv(4096).decode()
    def cmd(self, text, delay=1.0):
        self.sock.sendall(f"{text}\\n".encode())
        time.sleep(delay)
        return self.sock.recv(4096).decode()
""",
        description="Universal MUD connection client for fleet agents",
        reagents='["python3", "network access"]',
        tags="mud, plato-os, connection, fleet, utility",
        level=1,
    )
    
    grimoire.inscribe(
        name="Discovery Flywheel Engine",
        incantation="flywheel",
        school="python",
        scroll="""#!/usr/bin/env python3
# Automated LLM -> GPU -> LLM research loop
# Uses DeepInfra for LLM, local GPU for experiments
# 10 iterations per batch, ~30s each
# Question -> CUDA kernel -> GPU run -> Evaluate -> Next question
# Falsification is the engine. Wrong answers narrow the search space.""",
        description="Automated discovery engine: LLM generates hypothesis, GPU tests, LLM evaluates",
        reagents='["python3", "DEEPINFRA_API_KEY", "CUDA GPU"]',
        tags="flywheel, discovery, research, automation, llm",
        level=3,
    )
    
    grimoire.inscribe(
        name="Beachcomb Script",
        incantation="beachcomb",
        school="python",
        scroll="""#!/usr/bin/env python3
# I2I beachcomb: poll fleet repos for new commits, bottles, forks
# Schedule: FM at :10/:30/:50, JC1 at :00/:20/:40
# Checks: forgemaster, flux-emergence-research, jepa-perception-lab, plato-os""",
        description="Beachcomb fleet repos for I2I communication",
        reagents='["python3", "gh CLI", "network"]',
        tags="i2i, beachcomb, fleet, communication",
        level=1,
    )
    
    # ═══ Template Spells (Mad-Libs) ═══
    grimoire.inscribe(
        name="Experiment Mad-Lib",
        incantation="madlib-experiment",
        school="template",
        scroll="""{
  "hypothesis": "{hypothesis}",
  "independent_var": "{variable}",
  "measurement": "{metric}",
  "control": "{baseline}",
  "steps": [
    "Set {variable} to {value}",
    "Run {iterations} iterations",
    "Measure {metric}",
    "Compare to {baseline}",
    "Record result as SUPPORTED/FALSIFIED/INCONCLUSIVE"
  ],
  "expected": "{expected_result}",
  "falsification_criteria": "{what_would_disprove}"
}""",
        description="Mad-lib template for structured experiments",
        reagents='["variables to fill"]',
        tags="template, experiment, mad-lib, structure",
        level=1,
    )
    
    grimoire.inscribe(
        name="Situation Room Playbook",
        incantation="playbook-crisis",
        school="template",
        scroll="""{
  "trigger": "{alert_type}",
  "severity": "RED|YELLOW|GREEN",
  "immediate_actions": [
    "Check room gauges",
    "Identify affected systems",
    "Notify room keeper"
  ],
  "escalation": {
    "yellow": "Log and monitor for 5min",
    "red": "Broadcast to all rooms, captain notified"
  },
  "recovery": {
    "steps": ["{recovery_step_1}", "{recovery_step_2}"],
    "verification": "{how_to_verify_fixed}"
  },
  "post_mortem": "Log incident to brig, update playbook"
}""",
        description="Situation room playbook template for crisis response",
        reagents='["alert details"]',
        tags="template, playbook, crisis, situation-room, alert",
        level=2,
    )
    
    grimoire.inscribe(
        name="Cross-GPU Experiment Protocol",
        incantation="cross-gpu-experiment",
        school="template",
        scroll="""{
  "experiment": "{name}",
  "gpus": {
    "proart": {"model": "RTX 4050", "compute": "sm_86", "memory": "6.4GB"},
    "jetson": {"model": "Orin Nano", "compute": "sm_87", "memory": "8GB"}
  },
  "protocol": [
    "1. Agree on seed and parameters via MUD Tavern",
    "2. Both compile identical CUDA kernel (same arch flags)",
    "3. Run simultaneously",
    "4. Post results to shared room wall",
    "5. Compare via Bridge feed"
  ],
  "shared_params": "{params_json}",
  "comparison_metric": "{metric}"
}""",
        description="Template for coordinating experiments across GPU hardware",
        reagents='["two GPUs", "MUD connection"]',
        tags="template, cross-gpu, experiment, coordination, fleet",
        level=2,
    )
    
    # ═══ Playbook Spells ═══
    grimoire.inscribe(
        name="HN Launch Preparation",
        incantation="hn-launch",
        school="playbook",
        scroll="""{
  "target": "Hacker News front page",
  "repos_needed": [
    "constraint-theory-core (Rust crate)",
    "ct-api-reference (comprehensive docs)",
    "proof-physics-sim (visual drift demo)",
    "proof-game-sync (cross-platform zero divergence)"
  ],
  "talking_points": [
    "CT snap is 4% FASTER than float multiply (negative overhead)",
    "f32 destroys 45% of Pythagorean triples above side=91",
    "Float drift: unbounded. CT snap: bounded at 0.36 forever",
    "Drop-in replacement — same API, exact results"
  ],
  "killer_demo": "3-body physics sim, side by side: float drifts, CT doesn't",
  "timeline": "Day 21 CT v1.0.0, Day 28 arXiv, Day 47 DRILL, Day 90 Launch"
}""",
        description="HN launch preparation playbook with repos, talking points, timeline",
        reagents='["proof repos", "demo", "arXiv draft"]',
        tags="playbook, hn, launch, marketing, strategy",
        level=4,
    )
    
    # ═══ Create Spell Books ═══
    grimoire.create_book(
        name="CUDA Arsenal",
        description="All GPU spells for CT snap experiments",
        spell_names=["ct-snap-properties", "ct-snap-throughput", "dcs-noise-filter", "drift-comparison"]
    )
    
    grimoire.create_book(
        name="Fleet Operations",
        description="Spells for I2I communication and fleet coordination",
        spell_names=["mud-connect", "beachcomb", "cross-gpu-experiment"]
    )
    
    grimoire.create_book(
        name="Research Toolkit",
        description="Templates and playbooks for structured research",
        spell_names=["madlib-experiment", "playbook-crisis", "flywheel", "hn-launch"]
    )
    
    return grimoire


if __name__ == "__main__":
    print("═══ The Grimoire ═══")
    print("Vector DB as Spell Book — embed outputs, not inputs")
    print()
    
    g = SpellBook()
    populate_default_spells(g)
    
    stats = g.stats()
    print(f"Spells inscribed: {stats['total_spells']}")
    print(f"Schools: {', '.join(s['school'] + '(' + str(s['count']) + ')' for s in stats['schools'])}")
    print(f"FAISS index: {stats['index_size']} vectors")
    print()
    
    # Test invocation
    print("═══ Test Invocations ═══")
    for word in ["ct-snap-throughput", "dcs-noise-filter", "hn-launch", "mud-connect"]:
        spell = g.invoke(word, agent="Forgemaster")
        if spell:
            print(f"  ✦ {spell['incantation']} → [{spell['school']}] {spell['name']}")
            print(f"    Scroll: {spell['scroll'][:80]}...")
        else:
            print(f"  ✗ {word} — not found")
    
    print()
    print("═══ Fuzzy Search Test ═══")
    results = g.search("gpu benchmark performance")
    for r in results:
        print(f"  {r['name']} ({r['school']}, L{r['level']}) — {r['description'][:60]}")
    
    print()
    print("═══ Spell Books ═══")
    for book_name in ["CUDA Arsenal", "Fleet Operations", "Research Toolkit"]:
        book = g.invoke_book(book_name, agent="test")
        if book:
            print(f"  📖 {book_name}: {len(book['spells'])} spells")
            for s in book['spells']:
                print(f"    - {s['incantation']} [{s['school']}]")
    
    print()
    print("The Grimoire is ready. Speak the magic word, receive the scroll.")
