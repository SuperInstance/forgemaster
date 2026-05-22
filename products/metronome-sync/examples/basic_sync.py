"""Quick-start: sync two virtual clocks with PTP offsets."""

from fractions import Fraction
from metronome_sync import MetronomeClient, FleetConfig, PtpMode

# Set up two agents in a minimal fleet
alice = MetronomeClient(FleetConfig(name="alice", node_id=0, drift_rate=0.001))
bob = MetronomeClient(FleetConfig(name="bob", node_id=1, drift_rate=-0.002, mode=PtpMode.PTP))

# Simulate 100 ticks
for _ in range(100):
    alice._clock.tick()
    bob._clock.tick()

# Alice measures Bob's clock (simulated PTP exchange)
alice.apply_ptp_offset(
    local_time=alice.now(),
    remote_time=bob.now(),
    rtt=Fraction(2),  # 2 tick RTT
)

print(f"Alice: {alice.now()}  Bob: {bob.now()}")
print(f"Alice drift: {alice.drift()}  EMA: {alice._estimator.value}")
