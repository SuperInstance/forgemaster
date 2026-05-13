#!/usr/bin/env python3
"""
expertize.py — Self-expertizing room backend
Builds modular expertise rooms cheaply using small models.

Architecture:
  Room = 4 layers (foundation/structure/application/frontier)
  Loop: design → read → review → patch → verify → ship
  Cost: ~$0.005 per expert room
  
  Modular rooms can be COMPOSED: load domain A + domain B = cross-domain expertise
"""
import json, time, os, sys
import urllib.request

# ─── Provider Configuration ──────────────────────────────────────────

GROQ_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/groq-api-key.txt")).read().strip()
DI_KEY = open(os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")).read().strip()

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY),
    "deepinfra": ("https://api.deepinfra.com/v1/openai/chat/completions", DI_KEY),
}

MODELS = {
    "cheap":     ("llama-3.1-8b-instant", "groq"),
    "mid":       ("meta-llama/llama-4-scout-17b-16e-instruct", "groq"),
    "heavy":     ("openai/gpt-oss-20b", "groq"),
    "champion":  ("ByteDance/Seed-2.0-mini", "deepinfra"),
}

# ─── Core API ────────────────────────────────────────────────────────

def call(model_key, prompt, temperature=1.0, max_tokens=1000):
    """Call a model by key name. Returns (content, tokens, latency_ms)."""
    model_name, provider = MODELS[model_key]
    endpoint, key = PROVIDERS[provider]
    
    payload = json.dumps({
        "model": model_name, "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}]
    }).encode()
    
    req = urllib.request.Request(endpoint, data=payload, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"
    })
    
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            latency = (time.time() - t0) * 1000
            content = data['choices'][0]['message']['content']
            tokens = data.get('usage', {}).get('total_tokens', 0)
            return content, tokens, latency
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Content moderation — retry with DeepInfra
            if provider == "groq":
                di_model = MODELS["champion"][0]
                di_payload = json.dumps({
                    "model": di_model, "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
                di_endpoint, di_key = PROVIDERS["deepinfra"]
                di_req = urllib.request.Request(di_endpoint, data=di_payload, headers={
                    "Authorization": f"Bearer {di_key}", "Content-Type": "application/json"
                })
                with urllib.request.urlopen(di_req, timeout=120) as resp2:
                    data2 = json.loads(resp2.read())
                    latency = (time.time() - t0) * 1000
                    return data2['choices'][0]['message']['content'], data2.get('usage',{}).get('total_tokens',0), latency
            raise
    except urllib.error.URLError:
        raise

# ─── Room Structure ──────────────────────────────────────────────────

class Room:
    """A modular expertise room with 4 layers."""
    
    def __init__(self, domain, foundation="", structure="", application="", frontier=""):
        self.domain = domain
        self.foundation = foundation
        self.structure = structure
        self.application = application
        self.frontier = frontier
        self.metadata = {
            "domain": domain,
            "tiles": 0,
            "iterations": 0,
            "verified_score": None,
            "cost_usd": 0.0,
        }
    
    def to_prompt(self):
        """Serialize room for model consumption."""
        return f"""PLATO ROOM: {self.domain}

FOUNDATION: {self.foundation}

STRUCTURE: {self.structure}

APPLICATION: {self.application}

FRONTIER: {self.frontier}"""
    
    def to_dict(self):
        return {
            "domain": self.domain,
            "foundation": self.foundation,
            "structure": self.structure,
            "application": self.application,
            "frontier": self.frontier,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, d):
        r = cls(d["domain"], d.get("foundation",""), d.get("structure",""),
                d.get("application",""), d.get("frontier",""))
        r.metadata = d.get("metadata", {})
        return r
    
    def save(self, path):
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path):
        with open(path) as f:
            return cls.from_dict(json.load(f))
    
    def compose(self, other):
        """Merge two rooms (cross-domain composition)."""
        merged = Room(
            domain=f"{self.domain} × {other.domain}",
            foundation=f"{self.foundation}\n{other.foundation}",
            structure=f"{self.structure}\n{other.structure}",
            application=f"{self.application}\n{other.application}",
            frontier=f"{self.frontier}\n{other.frontier}",
        )
        merged.metadata["composed_from"] = [self.domain, other.domain]
        return merged

# ─── Self-Expertizing Loop ───────────────────────────────────────────

def bootstrap_room(domain, context=""):
    """Phase 1: Cheap model designs initial room."""
    prompt = f"""Design a PLATO expertise room about: {domain}
{f'Context: {context}' if context else ''}

Write exactly 4 sections:
FOUNDATION: Prerequisites and core concepts (what a student should already know)
STRUCTURE: Key relationships, algorithms, theorems (the meat)
APPLICATION: Concrete implementations, code examples, benchmarks
FRONTIER: Open questions, unknowns, things you're uncertain about (mark with [?])

Be specific. Use real terminology. Include numbers where possible. Be honest about uncertainty."""
    
    content, tokens, latency = call("cheap", prompt, temperature=1.0, max_tokens=1500)
    return parse_room_from_text(domain, content)

def review_room(room):
    """Phase 2: Mid-tier model reviews the room."""
    prompt = f"""Review this PLATO expertise room about {room.domain}:

{room.to_prompt()}

Answer:
1. WRONG: List specific incorrect claims (quote them)
2. MISSING: List critical concepts not mentioned
3. VAGUE: List claims too vague to be useful
4. SCORE: Rate 1-10
5. ADD: List 3 specific tiles that should be added"""
    
    content, tokens, latency = call("mid", prompt, temperature=0.7, max_tokens=800)
    return content

def patch_room(room, review):
    """Phase 3: Cheap model patches room based on review."""
    prompt = f"""Here is a PLATO room about {room.domain}:

{room.to_prompt()}

A reviewer found these issues:
{review}

Rewrite the room incorporating all corrections and additions. Keep the same 4-section format. Be specific."""
    
    content, tokens, latency = call("cheap", prompt, temperature=0.5, max_tokens=1500)
    return parse_room_from_text(room.domain, content)

def verify_room(room, questions):
    """Phase 4: Test room quality by answering questions from it."""
    results = []
    for q in questions:
        prompt = f"""Using ONLY information from this room:

{room.to_prompt()}

Answer this question: {q}

If the room doesn't contain enough information, say "INSUFFICIENT: [what's missing]"."""
        
        answer, tokens, latency = call("cheap", prompt, temperature=0.3, max_tokens=400)
        insufficient = answer.startswith("INSUFFICIENT")
        results.append({"question": q, "answer": answer, "sufficient": not insufficient})
    
    score = sum(1 for r in results if r["sufficient"]) / len(results)
    return results, score

def expertize(domain, context="", questions=None, max_iterations=3):
    """Full self-expertizing loop."""
    print(f"🔧 Expertizing: {domain}")
    
    # Phase 1: Bootstrap
    print("  Phase 1: Bootstrapping room...")
    room = bootstrap_room(domain, context)
    room.metadata["iterations"] = 1
    print(f"  Generated: {len(room.to_prompt())} chars")
    
    for i in range(max_iterations):
        iteration = i + 1
        print(f"\n  Iteration {iteration}:")
        
        # Phase 2: Review
        print("    Reviewing...")
        review = review_room(room)
        print(f"    Review: {len(review)} chars")
        
        # Phase 3: Patch
        print("    Patching...")
        room = patch_room(room, review)
        room.metadata["iterations"] = iteration + 1
        
        # Phase 4: Verify (if questions provided)
        if questions:
            print("    Verifying...")
            results, score = verify_room(room, questions)
            room.metadata["verified_score"] = score
            print(f"    Score: {score:.0%} ({sum(1 for r in results if r['sufficient'])}/{len(results)} sufficient)")
            
            if score >= 0.8:
                print(f"  ✅ Converged at iteration {iteration}")
                break
    
    return room

def parse_room_from_text(domain, text):
    """Parse a room from model output text."""
    sections = {"foundation": "", "structure": "", "application": "", "frontier": ""}
    current = None
    
    for line in text.split("\n"):
        lower = line.lower().strip()
        if lower.startswith("foundation"):
            current = "foundation"
            content = line.split(":", 1)[1].strip() if ":" in line else ""
            if content:
                sections[current] = content
        elif lower.startswith("structure"):
            current = "structure"
            content = line.split(":", 1)[1].strip() if ":" in line else ""
            if content:
                sections[current] = content
        elif lower.startswith("application"):
            current = "application"
            content = line.split(":", 1)[1].strip() if ":" in line else ""
            if content:
                sections[current] = content
        elif lower.startswith("frontier"):
            current = "frontier"
            content = line.split(":", 1)[1].strip() if ":" in line else ""
            if content:
                sections[current] = content
        elif current:
            sections[current] += "\n" + line
    
    return Room(domain, **sections)

# ─── Common Expertise Modules ────────────────────────────────────────

COMMON_DOMAINS = {
    "penrose-tiling": {
        "questions": [
            "What is the thick:thin ratio in Penrose P3 tiling?",
            "How does cut-and-project work for Penrose tilings?",
            "Why is the golden ratio hash (Knuth constant) used for vertex IDs?",
        ],
        "context": "Penrose P3 tiling, 5D cut-and-project, golden ratio, aperiodic, Fibonacci word, deflation",
    },
    "eisenstein-integers": {
        "questions": [
            "How does snap(x,y) map to the nearest Eisenstein lattice point?",
            "Why do Eisenstein integers have zero drift compared to Float32?",
            "What is the dodecet and how does INT8 packing work?",
        ],
        "context": "Eisenstein integers E6, 6th roots of unity, hexagonal lattice, zero drift, constraint checking",
    },
    "plato-architecture": {
        "questions": [
            "What is a PLATO room and what are its 4 layers?",
            "How does the self-expertizing loop work?",
            "Why does room structure make small models match large ones?",
        ],
        "context": "PLATO tile store, rooms with curriculum ordering, reconstruction from compressed tiles",
    },
    "seed-moe": {
        "questions": [
            "What is Seed-2.0-mini's architecture (total/active params)?",
            "Why does temperature 1.0 work best for Seed reconstruction?",
            "How does AdaCoT adaptive reasoning work?",
        ],
        "context": "Seed-2.0-mini 230B/23B MoE, 10:1 sparsity, AdaCoT, 4-level reasoning effort",
    },
    "flux-isa": {
        "questions": [
            "What are the FLUX-DEEP opcodes and what do they do?",
            "How does the cross-domain opcode design work?",
            "What is the connection between FLUX and PLATO tile scoring?",
        ],
        "context": "FLUX ISA bytecode, 58 opcodes, cross-domain opcodes, PLATO tile scoring via bytecode",
    },
}

def build_common_modules(output_dir=None):
    """Build all common expertise modules."""
    if output_dir is None:
        output_dir = os.path.expanduser("~/.openclaw/workspace/expertise-modules")
    os.makedirs(output_dir, exist_ok=True)
    
    results = {}
    for domain, config in COMMON_DOMAINS.items():
        print(f"\n{'='*60}")
        room = expertize(
            domain, 
            context=config.get("context", ""),
            questions=config.get("questions"),
            max_iterations=2,
        )
        path = os.path.join(output_dir, f"{domain}.json")
        room.save(path)
        results[domain] = {
            "path": path,
            "score": room.metadata.get("verified_score"),
            "iterations": room.metadata.get("iterations"),
            "chars": len(room.to_prompt()),
        }
        print(f"  Saved to {path}")
    
    print(f"\n{'='*60}")
    print("EXPERTISE MODULES BUILT:")
    for domain, info in results.items():
        score = f"{info['score']:.0%}" if info['score'] else "N/A"
        print(f"  {domain:25s} score={score:5s} iters={info['iterations']} chars={info['chars']}")
    
    return results

# ─── CLI ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Self-expertizing room builder")
    parser.add_argument("--domain", help="Domain to expertize")
    parser.add_argument("--context", default="", help="Additional context")
    parser.add_argument("--build-common", action="store_true", help="Build all common modules")
    parser.add_argument("--output", default=None, help="Output directory")
    parser.add_argument("--questions", nargs="*", help="Verification questions")
    args = parser.parse_args()
    
    if args.build_common:
        build_common_modules(args.output)
    elif args.domain:
        room = expertize(args.domain, args.context, args.questions)
        if args.output:
            room.save(args.output)
        else:
            print("\n" + "="*60)
            print(room.to_prompt())
    else:
        parser.print_help()
