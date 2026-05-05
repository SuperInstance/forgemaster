from dataclasses import dataclass
from typing import List

@dataclass
class ChipScore:
    name: str
    raw_tops_w: float
    safety_factor: float  # 0 if uncertified
    pass_rate: float
    power_overhead: float  # multiplier

    @property
    def safe_tops_w(self) -> float:
        return (self.raw_tops_w * self.pass_rate * self.safety_factor) / self.power_overhead

chips = [
    ChipScore("FLUX-LUCID", 24.0, 1.0, 0.9999999, 1.19),
    ChipScore("Jetson Orin AGX", 5.7, 0.0, 0.0, 1.0),
    ChipScore("Hailo-8 Safety", 9.7, 0.72, 0.99981, 1.32),
    ChipScore("Groq LPU", 21.4, 0.0, 0.0, 1.0),
    ChipScore("Google TPU v5e", 28.8, 0.0, 0.0, 1.0),
    ChipScore("Mobileye EyeQ6H", 7.2, 0.88, 0.99997, 1.27),
]

def print_comparison():
    print("| Chip | Raw TOPS/W | S Factor | Pass Rate | Power OH | Safe-TOPS/W |")
    print("|---|---|---|---|---|---|")
    for c in chips:
        print(f"| {c.name} | {c.raw_tops_w} | {c.safety_factor} | {c.pass_rate} | {c.power_overhead}x | **{c.safe_tops_w:.2f}** |")

print_comparison()
