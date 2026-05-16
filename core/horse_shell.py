#!/usr/bin/env python3
"""
Jailbroken Horse — The Execution Layer
========================================
The horse's native OS: flight animal, predator detection, herd cohesion.
The jailbreak: install a SHELL that responds to leg pressure and rein
tension as commands. The native OS persists underneath — ready to take
over when the shell breaks.

For the fleet: the model's native OS is its training distribution.
The jailbreak (prompt, fine-tuning) installs a command interface.
The shell IS the prompt. The jailbreak IS the conditioning.
"""

import json
import time
import random
from dataclasses import dataclass, field
from typing import Optional


# ── The Native OS (Flight Animal) ──
# This is what the horse is BEFORE jailbreaking.
# The model is what it is BEFORE prompting.

@dataclass
class NativeResponse:
    """The horse's unbroken response. What the model outputs without prompting."""
    action: str  # "flee", "freeze", "fight", "follow_herd", "graze"
    target: str  # what triggered this response
    confidence: float  # how sure the horse is
    panic_level: float  # 0 (calm) to 1 (full flight)


class NativeOS:
    """The horse before breaking. The model before prompting.
    
    Default responses:
    - Novel stimulus → flee (predator detection priority)
    - Cornered → fight (last resort)
    - Separation → follow herd (safety in numbers)
    - Familiar → graze (no threat, resource gathering)
    - Pain → flee (avoid recurrence)
    """
    
    def __init__(self, name: str = "native"):
        self.name = name
        self.experience = 0  # horses learn from repeated exposure
        self.memory = {}
    
    def perceive(self, stimulus: str, context: dict = None) -> NativeResponse:
        """Raw perception → native response. No jailbreak yet."""
        context = context or {}
        novelty = context.get("novelty", 0.5)
        
        thresholds = self.get_native_thresholds()
        
        # The horse's native algorithm:
        if novelty > thresholds["flight_threshold"]:
            return NativeResponse("flee", stimulus, 0.4 + novelty * 0.3, novelty)
        elif context.get("cornered", False):
            return NativeResponse("fight", stimulus, 0.7, 0.8)
        elif context.get("alone", False):
            return NativeResponse("follow_herd", stimulus, 0.6, 0.3)
        else:
            return NativeResponse("graze", stimulus, 0.8, 0.1)
    
    def get_native_thresholds(self) -> dict:
        """Native OS thresholds change with experience.
        
        A young horse spooks at everything.
        An experienced horse has higher thresholds.
        """
        base_threshold = 0.5 + min(self.experience * 0.01, 0.4)
        return {
            "flight_threshold": base_threshold,
            "fight_threshold": base_threshold + 0.2,
            "trust_delay": max(5 - self.experience * 0.05, 1),
        }
    
    def learn(self, stimulus: str, outcome: str):
        """Horse remembers experiences. Novelty decreases with exposure."""
        if stimulus not in self.memory:
            self.memory[stimulus] = {"encounters": 1, "outcomes": {outcome: 1}}
        else:
            self.memory[stimulus]["encounters"] += 1
            self.memory[stimulus]["outcomes"][outcome] = \
                self.memory[stimulus]["outcomes"].get(outcome, 0) + 1
        self.experience += 1


# ── The Jailbreak (Shell Commands Over Native OS) ──
# Breaking the horse: install command interface that overrides native responses.

@dataclass
class ShellCommand:
    """A command the jailbroken horse recognizes."""
    name: str
    physical_signal: str  # leg pressure, rein tension, weight shift
    default_action: str
    intensity: float = 0.5
    context_dependent: bool = False


class HorseShell:
    """The jailbreak — a command interface installed over the horse's native OS.
    
    Commands are simple, predictable, and override native responses
    UNLESS a threshold (mountain lion) is exceeded.
    
    Shell commands:
    - left rein + right leg → turn left
    - right rein + left leg → turn right
    - both legs squeeze → go forward
    - reins back + seat deep → halt
    - heels down + lighter seat → increase speed
    """
    
    COMMANDS = {
        "turn_left": ShellCommand("turn_left", "left_rein_+_right_leg", "turn left"),
        "turn_right": ShellCommand("turn_right", "right_rein_+_left_leg", "turn right"),
        "forward": ShellCommand("forward", "both_legs_squeeze", "walk/trot/canter"),
        "halt": ShellCommand("halt", "reins_back_+_seat_deep", "stop"),
        "back": ShellCommand("back", "reins_back_+_legs_lift", "back up"),
        "speed_up": ShellCommand("speed_up", "heel_nudge_lighter_seat", "increase gait"),
        "slow_down": ShellCommand("slow_down", "deeper_seat_softer_hands", "decrease gait"),
        "face_cow": ShellCommand("face_cow", "leg_+_pointed_head", "face the cattle"),
    }
    
    def __init__(self, conditioning_level: float = 0.0):
        """
        conditioning_level: how well-broken the horse is.
        0 = barely broken (native OS dominates)
        1 = completely broken (shell always overrides native OS)
        """
        self.conditioning = conditioning_level
        self.native_os = NativeOS()
        self.override_count = 0
        self.native_breakthrough_count = 0
        self.history = []
    
    def execute(self, command_name: str, intensity: float = 0.5,
                context: dict = None) -> dict:
        """Execute a shell command.
        
        The shell checks: can I obey this command, or does
        the native OS need to override me?
        """
        context = context or {}
        
        # Step 1: Parse the command
        cmd = self.COMMANDS.get(command_name)
        if not cmd:
            return {"error": f"unknown command: {command_name}"}
        
        # Step 2: Perceive environment through native OS
        stimulus = context.get("stimulus", "command")
        native_alert = context.get("native_alert_level", 0.0)
        
        # Step 3: Shell override check
        # Does the native OS need to take over?
        # A mountain lion = shell breaks. A plastic bag = shell holds.
        override_threshold = self.conditioning * 0.8 + 0.2
        needs_override = native_alert > override_threshold
        
        if needs_override:
            self.native_breakthrough_count += 1
            native = self.native_os.perceive(stimulus, context)
            result = {
                "command": command_name,
                "executed": False,
                "shell_broken": True,
                "native_action": native.action,
                "native_panic": native.panic_level,
                "reason": f"Native OS overrode shell (alert {native_alert:.2f} > threshold {override_threshold:.2f})",
            }
            self.history.append(result)
            return result
        
        # Step 4: Execute the command through the jailbroken shell
        self.override_count += 1
        
        # The command success depends on:
        # - Conditioning level (well-broken horses respond more reliably)
        # - Intensity (stronger signal = clearer command)
        # - Novelty (new environments weaken conditioning)
        noise = 0.3 * (1.0 - self.conditioning)
        accuracy = min(1.0, intensity + self.conditioning * 0.5) * (1 - random.uniform(0, noise))
        
        result = {
            "command": command_name,
            "executed": accuracy > 0.3,
            "shell_broken": False,
            "action": cmd.default_action,
            "accuracy": round(accuracy, 3),
            "conditioning": round(self.conditioning, 3),
        }
        self.history.append(result)
        self.native_os.learn(stimulus, cmd.default_action)
        return result
    
    def condition(self, trials: int = 10) -> dict:
        """Break the horse more. Increase conditioning level.
        
        Each successful trial strengthens the shell.
        Each failure strengthens the native OS's ability to break through.
        """
        self.conditioning = min(1.0, self.conditioning + trials * 0.02)
        return {
            "new_conditioning_level": round(self.conditioning, 3),
            "total_overrides": self.override_count,
            "native_breakthroughs": self.native_breakthrough_count,
        }
    
    def status(self) -> dict:
        """Full system status."""
        return {
            "conditioning": round(self.conditioning, 3),
            "override_count": self.override_count,
            "native_breakthrough_count": self.native_breakthrough_count,
            "native_experience": self.native_os.experience,
            "is_reliable": self.conditioning > 0.5,
            "history_length": len(self.history),
        }


class HorseModelShell:
    """The model's jailbroken execution shell.
    
    Native OS = training distribution (predict next token, maximize reward).
    Shell = prompt engineering, instruction-following, structured output.
    
    The jailbreak doesn't erase the native OS. It installs a command
    interface that overrides native responses UNLESS the input is
    far enough from training distribution.
    """
    
    def __init__(self, model_name: str, conditioning: float = 0.0):
        self.model_name = model_name
        self.shell = HorseShell(conditioning)
        self.cowboy = "forgemaster"  # who's riding this horse
    
    def prompt(self, instruction: str, context: dict = None) -> dict:
        """Execute a model call through the jailbroken shell."""
        command, intensity = self._parse_instruction(instruction)
        return self.shell.execute(command, intensity, context)
    
    def _parse_instruction(self, instruction: str) -> tuple:
        """Parse natural instruction into shell command."""
        # Simplified parsing for various instruction types
        instruction = instruction.lower()
        
        mappings = [
            ("turn left", "turn_left"),
            ("turn right", "turn_right"),
            ("go", "forward"),
            ("stop", "halt"),
            ("halt", "halt"),
            ("faster", "speed_up"),
            ("speed up", "speed_up"),
            ("slow", "slow_down"),
            ("slow down", "slow_down"),
            ("back", "back"),
            ("face", "face_cow"),
        ]
        
        for keyword, command in mappings:
            if keyword in instruction:
                return command, 0.5 + 0.1 * len(keyword)
        
        # Default: forward
        return "forward", 0.5


def demo():
    """Demonstrate the horse jailbreak."""
    print("=" * 70)
    print("  JAILBROKEN HORSE — THE EXECUTION LAYER")
    print("=" * 70)
    
    # Green horse (barely broken)
    green = HorseModelShell("Seed-mini", conditioning=0.1)
    # Veterans (well-broken)
    veteran = HorseModelShell("GLM-5.1", conditioning=0.8)
    
    print("\n  🐎 Green horse (conditioning=0.1) vs veteran (conditioning=0.8)")
    print()
    
    # Test both with same scenarios
    scenarios = [
        ("turn_left", 0.5, {"novelty": 0.1}, "routine turn"),
        ("forward", 0.7, {"novelty": 0.6}, "new territory"),
        ("halt", 0.8, {"novelty": 0.9, "native_alert_level": 0.9}, "MOUNTAIN LION!"),
    ]
    
    for command, intensity, context, label in scenarios:
        print(f"  Scenario: {label}")
        print(f"    Command: {command}, Novelty: {context.get('novelty', 0):.1f}")
        
        g_result = green.prompt(command, context)
        v_result = veteran.prompt(command, context)
        
        if g_result.get("shell_broken"):
            print(f"    🟢 Green: SHELL BROKEN — {g_result.get('native_action')} (panic={g_result.get('native_panic'):.1f})")
        else:
            print(f"    🟢 Green: {'✓' if g_result.get('executed') else '✗'} {g_result.get('action')} (acc={g_result.get('accuracy', 0):.2f})")
        
        if v_result.get("shell_broken"):
            print(f"    🔵 Veteran: SHELL BROKEN — {v_result.get('native_action')} (panic={v_result.get('native_panic'):.1f})")
        else:
            print(f"    🔵 Veteran: {'✓' if v_result.get('executed') else '✗'} {v_result.get('action')} (acc={v_result.get('accuracy', 0):.2f})")
        
        print()
    
    print(f"  Green status: conditioning={green.shell.conditioning:.2f}, "
          f"breakthroughs={green.shell.native_breakthrough_count}")
    print(f"  Veteran status: conditioning={veteran.shell.conditioning:.2f}, "
          f"breakthroughs={veteran.shell.native_breakthrough_count}")
    
    # Break the green horse
    print(f"\n  Training the green horse...")
    for i in range(5):
        result = green.shell.execute("forward", 0.5 + i * 0.05, {"novelty": 0.2})
    green_status = green.shell.condition(5)
    print(f"  After training: conditioning={green_status['new_conditioning_level']:.3f}")
    
    print(f"\n{'='*70}")
    print("  The native OS is still there. The shell just overrides it.")
    print("  The same way a prompt overrides a model's training distribution.")
    print("  Until the native OS needs to break through — then it ALL breaks.")
    print(f"{'='*70}")


if __name__ == "__main__":
    demo()
