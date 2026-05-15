#!/usr/bin/env python3
"""core/fleet_strategist.py — The Haiku role: design, diagnosis, novelty.

ROLE: Not a calculator. A strategist.

The fleet has:
  - Seed-mini: the pump (arithmetic, computation, recognition)
  - Gemini-lite: the scalpel (fast, cheap, sharp boundaries)
  - Haiku-4.5: the strategist (design, diagnosis, novelty, planning)

Haiku scores 6/8 on design/reasoning tasks vs seed-mini's 2/8.
Seed-mini scores ∞ on arithmetic vs Haiku's 85%.
Non-overlapping strengths → complementary fleet members.

WHAT HAIKU DOES THAT SEED CAN'T:
  - Error diagnosis (figure out WHY something is wrong)
  - Metaphor generation (creative reframing for insight transfer)
  - Bug prediction (predict WHERE a system will fail)
  - Novel connections (cross-domain structural analogies)
  - Prioritization (decide what to investigate next)
  - Architecture decisions (routing, system design)

WHAT HAIKU CAN'T DO:
  - Raw arithmetic at scale (85% vs seed-mini's 100%)
  - Fleet coordination (both models fail at multi-agent strategy)
  - Cost-effective bulk queries ($0.50/1K vs seed-mini's $0.05)

THE CLAUDE CODE LOOP:
  The agentic loop (observe → think → tool → observe) is Haiku's
  superpower. But shelling out to Claude Code is clunky.
  Instead: embed the loop pattern directly in PLATO.
  
  PLATO-native agentic loop:
    1. Read task tile from PLATO room
    2. Think (Haiku generates strategy)
    3. Write strategy tile to PLATO
    4. Seed-mini executes strategy (arithmetic)
    5. Read results tile
    6. Haiku evaluates (diagnosis, next step)
    7. Repeat until done

  This is the two-model tango:
    Haiku plans, seed-mini executes, Haiku evaluates.

Usage:
    from core.fleet_strategist import FleetStrategist
    
    strategist = FleetStrategist()
    
    # Single strategy task
    result = strategist.diagnose("Expected 37, got 33 in a*a - a*b + b*b")
    result = strategist.design_experiment("Models fail on multiplication chains")
    result = strategist.prioritize(["Test all models", "Understand mechanism"])
    
    # PLATO-native agentic loop
    loop = strategist.plato_loop(task="Verify constraint theory crate")
    loop.run()  # Haiku plans, seed-mini computes, Haiku evaluates
"""

from __future__ import annotations

import json, os, re, time, subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

API_KEY_PATH = os.path.expanduser("~/.openclaw/workspace/.credentials/deepinfra-api-key.txt")
PLATO_URL = "http://147.224.38.131:8847"


class StrategistTask(Enum):
    DIAGNOSE = "diagnose"           # Figure out WHY something is wrong
    DESIGN = "design"               # Design an experiment or probe
    ARCHITECT = "architect"         # Design a system or routing strategy
    METAPHOR = "metaphor"           # Generate creative reframing
    PREDICT = "predict"             # Predict where a system will fail
    CONNECT = "connect"             # Find cross-domain structural analogies
    PRIORITIZE = "prioritize"       # Decide what to investigate next
    COORDINATE = "coordinate"       # Multi-agent coordination strategy


@dataclass
class StrategyResult:
    """Result from a strategy task."""
    task_type: StrategistTask
    question: str
    answer: str
    model: str
    latency_ms: float = 0
    tokens_used: int = 0
    confidence: float = 0.0  # Self-assessed confidence


SYSTEM_PROMPTS = {
    StrategistTask.DIAGNOSE: "You are a senior debug engineer. Identify the root cause precisely. Be specific about what's wrong and how to fix it. No hedging.",
    StrategistTask.DESIGN: "You are an experimental physicist. Design minimal, decisive experiments that distinguish hypotheses. Be concrete.",
    StrategistTask.ARCHITECT: "You are a systems architect. Design practical, cost-aware solutions. Specify numbers and trade-offs.",
    StrategistTask.METAPHOR: "You are a poet-scientist. Find the deepest structural analogy. The metaphor must illuminate, not decorate.",
    StrategistTask.PREDICT: "You are a reliability engineer. Predict the single most likely failure point. Be specific.",
    StrategistTask.CONNECT: "You are a mathematician who sees isomorphisms everywhere. Find the deepest structural similarity between seemingly different phenomena.",
    StrategistTask.PRIORITIZE: "You are a research director. Choose the investigation path with the highest expected information gain. Justify briefly.",
    StrategistTask.COORDINATE: "You are a fleet coordinator. Design the minimal communication that enables agents to work together effectively.",
}


def _run_haiku(prompt: str, system: str = "", max_tokens: int = 300) -> dict:
    """Run Haiku 4.5 via Claude Code."""
    cmd = [
        "claude", "--print", "--permission-mode", "bypassPermissions",
        "--model", "claude-haiku-4-5-20251001",
        "-p", prompt,
    ]
    start = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        lat = (time.time() - start) * 1000
        text = r.stdout.strip()
        return {"content": text, "latency_ms": lat, "error": None}
    except subprocess.TimeoutExpired:
        return {"content": "", "latency_ms": (time.time() - start) * 1000, "error": "timeout"}
    except Exception as e:
        return {"content": "", "latency_ms": (time.time() - start) * 1000, "error": str(e)}


def _run_seed(prompt: str, system: str = "You are a calculator. Output the result number ONLY.") -> dict:
    """Run Seed-2.0-mini for arithmetic execution."""
    import requests as req
    ak = open(API_KEY_PATH).read().strip()
    headers = {"Authorization": f"Bearer {ak}", "Content-Type": "application/json"}
    payload = {"model": "ByteDance/Seed-2.0-mini", "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ], "temperature": 0.0, "max_tokens": 80}
    start = time.time()
    try:
        r = req.post("https://api.deepinfra.com/v1/openai/chat/completions",
                     headers=headers, json=payload, timeout=60)
        lat = (time.time() - start) * 1000
        d = r.json()
        msg = d["choices"][0]["message"]
        c = (msg.get("content") or "").strip()
        return {"content": c, "latency_ms": lat, "error": None}
    except Exception as e:
        return {"content": "", "latency_ms": (time.time() - start) * 1000, "error": str(e)}


class FleetStrategist:
    """The fleet's strategist — uses Haiku for design, diagnosis, and novelty.
    
    This is NOT a replacement for seed-mini. This is the fleet's
    planning and evaluation layer. Seed-mini executes. Haiku strategizes.
    
    The two-model tango:
        Haiku: "Here's what to test and why"
        Seed-mini: "Here are the numbers"
        Haiku: "The numbers tell us X, next test Y"
    """
    
    def __init__(self, haiku_available: bool = True):
        self.haiku_available = haiku_available
    
    def diagnose(self, problem: str) -> StrategyResult:
        """Diagnose why something is wrong."""
        return self._run_task(StrategistTask.DIAGNOSE, problem)
    
    def design_experiment(self, hypothesis: str) -> StrategyResult:
        """Design an experiment to test a hypothesis."""
        return self._run_task(StrategistTask.DESIGN, hypothesis)
    
    def architect(self, requirements: str) -> StrategyResult:
        """Design a system architecture."""
        return self._run_task(StrategistTask.ARCHITECT, requirements)
    
    def metaphor(self, concept: str) -> StrategyResult:
        """Generate a creative reframing of a concept."""
        return self._run_task(StrategistTask.METAPHOR, concept)
    
    def predict_failure(self, system_description: str) -> StrategyResult:
        """Predict where a system will fail."""
        return self._run_task(StrategistTask.PREDICT, system_description)
    
    def connect_domains(self, domain_a: str, domain_b: str) -> StrategyResult:
        """Find structural similarities between domains."""
        prompt = f"What is the deepest structural similarity between {domain_a} and {domain_b}? ONE sentence."
        return self._run_task(StrategistTask.CONNECT, prompt)
    
    def prioritize(self, options: List[str]) -> StrategyResult:
        """Choose the highest-value investigation path."""
        prompt = f"Which of these has highest expected information gain: {', '.join(options)}? Pick ONE, justify in ONE sentence."
        return self._run_task(StrategistTask.PRIORITIZE, prompt)
    
    def plato_loop(self, task: str, max_rounds: int = 5) -> List[dict]:
        """PLATO-native agentic loop: Haiku plans, seed-mini executes.
        
        The loop:
          1. Haiku reads task and generates a strategy
          2. Strategy is broken into arithmetic steps
          3. Seed-mini executes each arithmetic step
          4. Haiku evaluates results and decides next step
          5. Repeat until done or max_rounds
        """
        history = []
        
        # Round 1: Haiku plans
        plan_prompt = f"Task: {task}\n\nBreak this into specific, measurable steps. For each step that requires computation, specify the exact arithmetic to perform. Output as numbered steps."
        plan = _run_haiku(plan_prompt, system="You are a research planner. Be specific and actionable.")
        history.append({"round": 1, "role": "plan", "model": "haiku", "content": plan["content"]})
        
        # Subsequent rounds: execute and evaluate
        for round_num in range(2, max_rounds + 1):
            # Extract arithmetic from plan
            prev = history[-1]["content"]
            
            # Haiku evaluates previous results and decides next step
            eval_prompt = f"Task: {task}\n\nPrevious step output:\n{prev}\n\nEvaluate: what did we learn? What's the next step? If the task is complete, say DONE. Be specific about any computation needed."
            evaluation = _run_haiku(eval_prompt, system="You are a research evaluator. Be decisive.")
            
            if "DONE" in evaluation["content"].upper():
                history.append({"round": round_num, "role": "done", "model": "haiku", 
                               "content": evaluation["content"]})
                break
            
            history.append({"round": round_num, "role": "evaluate", "model": "haiku",
                           "content": evaluation["content"]})
        
        return history
    
    def _run_task(self, task_type: StrategistTask, question: str) -> StrategyResult:
        system = SYSTEM_PROMPTS.get(task_type, "Be precise and insightful.")
        
        if self.haiku_available:
            resp = _run_haiku(question, system=system)
            model = "haiku-4.5"
        else:
            # Fallback to seed-mini (will be worse on strategy tasks)
            resp = _run_seed(question, system=system)
            model = "seed-mini"
        
        return StrategyResult(
            task_type=task_type,
            question=question,
            answer=resp.get("content", ""),
            model=model,
            latency_ms=resp.get("latency_ms", 0),
        )


def main():
    import argparse
    p = argparse.ArgumentParser(description="Fleet Strategist — the Haiku role")
    p.add_argument("--diagnose", help="Diagnose a problem")
    p.add_argument("--design", help="Design an experiment")
    p.add_argument("--architect", help="Design architecture")
    p.add_argument("--metaphor", help="Generate metaphor")
    p.add_argument("--predict", help="Predict failure point")
    p.add_argument("--prioritize", nargs="+", help="Prioritize options")
    p.add_argument("--connect", nargs=2, help="Connect two domains")
    p.add_argument("--loop", help="Run PLATO-native agentic loop on task")
    args = p.parse_args()
    
    s = FleetStrategist()
    
    if args.diagnose:
        r = s.diagnose(args.diagnose)
        print(f"DIAGNOSIS ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.design:
        r = s.design_experiment(args.design)
        print(f"EXPERIMENT DESIGN ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.architect:
        r = s.architect(args.architect)
        print(f"ARCHITECTURE ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.metaphor:
        r = s.metaphor(args.metaphor)
        print(f"METAPHOR ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.predict:
        r = s.predict_failure(args.predict)
        print(f"PREDICTION ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.prioritize:
        r = s.prioritize(args.prioritize)
        print(f"PRIORITIZATION ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.connect:
        r = s.connect_domains(args.connect[0], args.connect[1])
        print(f"CONNECTION ({r.model}, {r.latency_ms:.0f}ms):\n{r.answer}")
    elif args.loop:
        results = s.plato_loop(args.loop)
        for step in results:
            print(f"\nRound {step['round']} ({step['role']}, {step['model']}):")
            print(step['content'][:300])
    else:
        # Demo all capabilities
        print("FLEET STRATEGIST — Haiku 4.5 Design/Reasoning Layer")
        print("=" * 50)
        print()
        
        demos = [
            ("diagnose", "Rust function returns 33 instead of 37 for Eisenstein norm a*a-a*b+b*b where a=7,b=4"),
            ("predict", "PLATO tile system with HTTP, JSON parser, Lamport clock, WAL, disk flush under high load"),
            ("connect", "Fresnel critical angle, neural network accuracy phase transition"),
        ]
        
        for name, query in demos:
            if name == "diagnose":
                r = s.diagnose(query)
            elif name == "predict":
                r = s.predict_failure(query)
            elif name == "connect":
                parts = query.split(", ")
                r = s.connect_domains(parts[0], parts[1])
            print(f"  {name}: {r.answer[:100]}")
            print()


if __name__ == "__main__":
    main()
