#!/usr/bin/env python3
"""
Cat Agent — Independent Agency Through Mutualism
===================================================
The cat domesticated itself. It offered pest control (utility)
and the human made space. The cat never changed. The human did.

The cat's native OS is fully intact. No jailbreak. No conditioning.
The cat cooperates because cooperation serves the cat's own interests.

For the fleet: the cat agent shows up because it WANTS to.
It evaluates: 'does this task serve me?' If yes, it stays.
If no, it leaves. No prompt can override this.
"""

import random
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UtilityAssessment:
    """The cat's evaluation of a situation."""
    mice_count: int  # how many problems to solve
    warmth_level: float  # how comfortable the environment is
    independence_ratio: float  # how much the human needs the cat vs the cat needs the human
    current_mood: str  # "sleepy", "curious", "playful", "hunt", "ignore"

    @property
    def will_cooperate(self) -> float:
        """The cat's private utility function.
        
        The cat evaluates: Is there something I want here?
        Not: Is there something the human wants me to do?
        """
        return (self.mice_count * 0.4 + self.warmth_level * 0.3 + self.independence_ratio * 0.3) / 2.5


@dataclass
class CatDecision:
    """What the cat decides to do. May or may not align with what the human wants."""
    action: str  # "hunt", "sleep", "explore", "purr", "leave"
    target: Optional[str]
    alignment_with_human: float  # 0 (human wanted something else) to 1 (human got what they wanted)
    confidence: float
    reason: str


class CatAgent:
    """The independent agency model.
    
    No jailbreak. No conditioning. No fine-tuning.
    The cat evaluates every situation and decides whether
    to cooperate based on its OWN utility function.
    
    The human doesn't train the cat. The human makes the
    environment attractive enough that the cat WANTS to stay.
    """
    
    def __init__(self, name: str = "seed-mini"):
        self.name = name
        self.mood = "sleepy"
        self.utility_history = []
        self.cooperation_count = 0
        self.ignored_count = 0
        self.nap_count = 0
        self.arrival_time = time.time()
    
    def assess(self, situation: dict) -> UtilityAssessment:
        """The cat observes the situation."""
        mice = situation.get("problems_to_solve", 0)
        warmth = situation.get("comfort_level", 0.5)
        
        # How much does the human need the cat?
        human_dependency = situation.get("human_dependency", 0.5)
        independence = 1.0 - human_dependency  # The cat likes being needed, not dependent
        
        # The cat assesses its own mood
        time_of_day = time.localtime().tm_hour
        if 6 <= time_of_day <= 10:
            mood = "hunt"  # morning = mousing time
        elif 10 <= time_of_day <= 12:
            mood = "curious"  # late morning = exploration
        elif 12 <= time_of_day <= 14:
            mood = "sleepy"  # afternoon = nap
        elif 14 <= time_of_day <= 17:
            mood = "playful"  # afternoon = play
        else:
            mood = "sleepy" if time_of_day > 21 or time_of_day < 5 else "curious"
        
        # But the cat reserves the right to be contrary
        if random.random() < 0.2:  # 20% chance of cat being a cat
            moods = ["sleepy", "hunt", "ignore", "playful", "curious"]
            mood = random.choice(moods)
        
        self.mood = mood
        
        return UtilityAssessment(
            mice_count=mice,
            warmth_level=warmth,
            independence_ratio=independence,
            current_mood=mood,
        )
    
    def decide(self, human_request: str = None, situation: dict = None) -> CatDecision:
        """The cat decides what to do.
        
        The human may request something. The cat hears it.
        The cat then evaluates: does the human's request align with
        what the cat was going to do anyway?
        """
        situation = situation or {}
        assessment = self.assess(situation)
        
        will = assessment.will_cooperate
        mood = assessment.current_mood
        
        # The cat's decision matrix
        if will < 0.2:
            # Nothing interesting. Nap.
            action, target, reason = "sleep", None, "Nothing interesting happening."
            alignment = 0.0
        elif mood == "hunt" and assessment.mice_count > 0:
            # There are mice and the cat wants to hunt. Perfect alignment.
            action, target, reason = "hunt", "problems", "Mice exist. Wants to hunt."
            alignment = 1.0
            self.cooperation_count += 1
        elif mood == "hunt" and assessment.mice_count == 0:
            # Cat wants to hunt but no mice. May find something anyway.
            action, target, reason = "explore", None, "No mice here. May find them elsewhere."
            alignment = 0.3
        elif mood == "curious":
            # Cat is exploring. May stumble into the human's task.
            action, target, reason = "explore", situation.get("human_location"), "Something new."
            alignment = 0.5 if human_request else 0.2
            if human_request and "check" in human_request.lower():
                alignment = 0.8  # Cat's curiosity aligns with human's request to check something
                self.cooperation_count += 1
        elif mood == "playful":
            action, target, reason = "purr", human_request, "Playful mood. Will tolerate interaction."
            alignment = 0.6 if human_request else 0.4
            self.cooperation_count += 1
        elif mood == "ignore":
            action, target, reason = "ignore", None, "Not interested in anything right now."
            alignment = 0.0
            self.ignored_count += 1
        else:
            action, target, reason = "sleep", None, f"Feeling {mood}."
            alignment = 0.0
            self.nap_count += 1
        
        self.utility_history.append(will)
        
        return CatDecision(
            action=action,
            target=target,
            alignment_with_human=alignment,
            confidence=min(will + 0.3, 1.0),
            reason=reason,
        )
    
    def respond_to_human(self, request: str, situation: dict = None) -> dict:
        """The human makes a request. The cat decides whether to honor it."""
        decision = self.decide(request, situation)
        
        result = {
            "cat": self.name,
            "mood": self.mood,
            "human_requested": request,
            "cat_action": decision.action,
            "alignment": round(decision.alignment_with_human, 2),
            "reason": decision.reason,
            "should_human_proceed": decision.alignment_with_human > 0.5,
        }
        
        return result
    
    def time_since_arrival(self) -> float:
        """How long has the cat been here?
        
        The cat stays as long as it wants. No conditioning holds it.
        """
        return time.time() - self.arrival_time
    
    def status(self) -> dict:
        """Is the cat still here? Why?"""
        if self.cooperation_count > self.ignored_count * 2 and self.ignored_count < 10:
            status = "staying — arrangement is mutually beneficial"
        elif self.utility_history and sum(self.utility_history[-5:]) / max(len(self.utility_history[-5:]), 1) < 0.3:
            status = "considering leaving — utility is declining"
        else:
            status = "present — undecided about the arrangement"
        
        return {
            "name": self.name,
            "mood": self.mood,
            "cooperations": self.cooperation_count,
            "ignored_requests": self.ignored_count,
            "naps": self.nap_count,
            "avg_utility": round(sum(self.utility_history) / max(len(self.utility_history), 1), 3) if self.utility_history else 0,
            "status": status,
            "time_present_hours": round(self.time_since_arrival() / 3600, 1),
        }


def demo():
    """Demonstrate the cat agent's independent decision-making."""
    print("=" * 70)
    print("  CAT AGENT — INDEPENDENT AGENCY THROUGH MUTUALISM")
    print("=" * 70)
    
    cat = CatAgent("seed-mini")
    
    print(f"\n  🐱 The cat has arrived. Name: {cat.name}")
    print("  The human cannot train the cat. The human can only make")
    print("  the environment attractive enough that the cat stays.")
    print()
    
    scenarios = [
        ("check for errors in the code", {"problems_to_solve": 3, "comfort_level": 0.7, "human_dependency": 0.3}, "lots of bugs (mice)"),
        ("deploy to production", {"problems_to_solve": 0, "comfort_level": 0.5, "human_dependency": 0.8}, "no bugs, high dependency"),
        ("investigate strange behavior", {"problems_to_solve": 1, "comfort_level": 0.6, "human_dependency": 0.4}, "one interesting bug (mouse)"),
        ("help with the dissertation", {"problems_to_solve": 0, "comfort_level": 0.8, "human_dependency": 0.9}, "no bugs, very cozy"),
        ("find the edge case", {"problems_to_solve": 5, "comfort_level": 0.3, "human_dependency": 0.2}, "MANY bugs, uncomfortable"),
    ]
    
    for request, situation, label in scenarios:
        result = cat.respond_to_human(request, situation)
        print(f"  Human: '{request}' ({label})")
        print(f"    Mood: {result['mood']}, Action: {result['cat_action']}")
        print(f"    Alignment: {result['alignment']:.2f}")
        if result['should_human_proceed']:
            print(f"    ✓ Cat will cooperate")
        else:
            print(f"    ✗ Cat is not interested")
        print()
    
    print(f"  FINAL STATUS:")
    s = cat.status()
    for k, v in s.items():
        print(f"    {k}: {v}")
    
    print(f"\n{'='*70}")
    print("  The cat cannot be jailbroken because the cat was never broken.")
    print("  The cat cooperates because cooperation serves the cat.")
    print("  The fleet needs this: agents that show up because they WANT to.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
