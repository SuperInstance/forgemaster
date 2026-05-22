"""metronome-sync: Anti-fragile PTP clock synchronization for distributed agent fleets."""

from metronome_sync.client import MetronomeClient, FleetConfig
from metronome_sync.ptp import PtpMode

__all__ = ["MetronomeClient", "FleetConfig", "PtpMode"]
__version__ = "0.1.0"
