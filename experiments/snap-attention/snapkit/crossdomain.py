"""
crossdomain.py — Cross-Domain Feel Transfer
============================================

The feel transfers across domains because it's the snap topology,
not the content. This module implements the mapping of snap topologies
between domains so that calibrated tolerances transfer directly.

"A coin flip and a true/false question feel the same. Not similar —
THE SAME FEEL."
— SNAPS-AS-ATTENTION.md, Addendum
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from snapkit.topology import SnapTopology, ADEType
from snapkit.snap import SnapFunction, SnapTopologyType


class DomainArchetype(Enum):
    """
    Archetypes of how randomness manifests in different domains.
    
    The archetype determines which snap topology best compresses
    the domain's uncertainty.
    """
    BINARY = "binary"                # Yes/no, alive/dead, pass/fail
    CATEGORICAL = "categorical"      # Multiple discrete outcomes
    UNIFORM = "uniform"              # Equal-probability outcomes
    BELL = "bell"                    # Central tendency with tails
    GRADIENT = "gradient"            # Near-continuous spectrum
    DIRECTIONAL = "directional"      # Directional outcomes (compass)
    COMBINATORIAL = "combinatorial"  # Rich combinatorial spaces
    CLUSTER = "cluster"              # Golden-ratio clustered
    META = "meta"                    # Meta: changes in randomness itself


@dataclass
class DomainProfile:
    """
    Profile of a domain's randomness flavors.
    
    Each domain has characteristic:
    - Archetype(s): what kind of randomness dominates
    - Calibration speed: how quickly snap tolerance can be tuned
    - Noise floor: baseline variance in the domain
    - Topology affinity: which snap topologies work best
    
    Usage:
        poker = DomainProfile(
            name="poker",
            archetypes=[DomainArchetype.UNIFORM, DomainArchetype.CATEGORICAL,
                       DomainArchetype.COMBINATORIAL, DomainArchetype.DIRECTIONAL],
            primary_topology=SnapTopologyType.HEXAGONAL,
            calibration_speed=0.7,
            noise_floor=0.2,
        )
    """
    name: str
    archetypes: List[DomainArchetype]
    primary_topology: SnapTopologyType
    calibration_speed: float        # How fast tolerances converge [0..1]
    noise_floor: float              # Baseline irreducible variance
    topology_affinities: Dict[SnapTopologyType, float] = field(default_factory=dict)
    description: str = ""
    
    def __post_init__(self):
        if not self.topology_affinities:
            # Default affinities based on archetypes
            for arch in self.archetypes:
                for topo, affinity in ARCHETYPE_TO_TOPOLOGY.get(arch, {}).items():
                    self.topology_affinities[topo] = max(
                        self.topology_affinities.get(topo, 0.0), affinity
                    )
    
    def best_topology(self) -> SnapTopologyType:
        """Get the topology with highest affinity for this domain."""
        if not self.topology_affinities:
            return self.primary_topology
        return max(self.topology_affinities, key=self.topology_affinities.get)
    
    def snap_affinity(self, topology: SnapTopologyType) -> float:
        """How good is a given topology for this domain? [0..1]"""
        return self.topology_affinities.get(topology, 0.0)
    
    def __repr__(self):
        arch_names = [a.value for a in self.archetypes[:3]]
        return (f"DomainProfile({self.name}, "
                f"arch={arch_names}, "
                f"topo={self.primary_topology.value}, "
                f"speed={self.calibration_speed:.2f})")


# Archetype → topology affinities
ARCHETYPE_TO_TOPOLOGY = {
    DomainArchetype.BINARY: {
        SnapTopologyType.BINARY: 1.0,
        SnapTopologyType.HEXAGONAL: 0.5,
    },
    DomainArchetype.CATEGORICAL: {
        SnapTopologyType.CATEGORICAL: 1.0,
        SnapTopologyType.OCTAHEDRAL: 0.6,
        SnapTopologyType.HEXAGONAL: 0.4,
    },
    DomainArchetype.UNIFORM: {
        SnapTopologyType.CUBIC: 1.0,
        SnapTopologyType.HEXAGONAL: 0.7,
        SnapTopologyType.UNIFORM: 1.0,
    },
    DomainArchetype.BELL: {
        SnapTopologyType.BELL: 1.0,
        SnapTopologyType.HEXAGONAL: 0.6,
        SnapTopologyType.GRADIENT: 0.5,
    },
    DomainArchetype.GRADIENT: {
        SnapTopologyType.GRADIENT: 1.0,
        SnapTopologyType.UNIFORM: 0.7,
        SnapTopologyType.BELL: 0.4,
    },
    DomainArchetype.DIRECTIONAL: {
        SnapTopologyType.OCTAHEDRAL: 1.0,
        SnapTopologyType.HEXAGONAL: 0.8,
        SnapTopologyType.CUBIC: 0.5,
    },
    DomainArchetype.COMBINATORIAL: {
        SnapTopologyType.HEXAGONAL: 0.8,
        SnapTopologyType.OCTAHEDRAL: 0.6,
        SnapTopologyType.CUBIC: 0.5,
    },
    DomainArchetype.CLUSTER: {
        SnapTopologyType.HEXAGONAL: 0.9,
        SnapTopologyType.OCTAHEDRAL: 0.5,
    },
    DomainArchetype.META: {
        SnapTopologyType.HEXAGONAL: 0.7,
        SnapTopologyType.BINARY: 0.5,
    },
}


# Pre-built domain profiles
BUILTIN_DOMAIN_PROFILES = {
    'poker': DomainProfile(
        name='poker',
        archetypes=[DomainArchetype.UNIFORM, DomainArchetype.CATEGORICAL,
                   DomainArchetype.COMBINATORIAL, DomainArchetype.DIRECTIONAL],
        primary_topology=SnapTopologyType.HEXAGONAL,
        calibration_speed=0.7,
        noise_floor=0.2,
        description='Poker: card probabilities, player behavior, betting patterns, emotional tells',
    ),
    'medical': DomainProfile(
        name='medical',
        archetypes=[DomainArchetype.BINARY, DomainArchetype.GRADIENT,
                   DomainArchetype.DIRECTIONAL],
        primary_topology=SnapTopologyType.BELL,
        calibration_speed=0.3,
        noise_floor=0.3,
        description='Medical: diagnosis (binary), vitals (gradient), trends (directional)',
    ),
    'finance': DomainProfile(
        name='finance',
        archetypes=[DomainArchetype.GRADIENT, DomainArchetype.COMBINATORIAL,
                   DomainArchetype.DIRECTIONAL],
        primary_topology=SnapTopologyType.GRADIENT,
        calibration_speed=0.5,
        noise_floor=0.4,
        description='Finance: market movements, risk assessment, portfolio allocation',
    ),
    'driving': DomainProfile(
        name='driving',
        archetypes=[DomainArchetype.DIRECTIONAL, DomainArchetype.BELL,
                   DomainArchetype.BINARY],
        primary_topology=SnapTopologyType.OCTAHEDRAL,
        calibration_speed=0.8,
        noise_floor=0.1,
        description='Driving: steering (directional), speed (bell), hazards (binary)',
    ),
    'education': DomainProfile(
        name='education',
        archetypes=[DomainArchetype.CATEGORICAL, DomainArchetype.GRADIENT,
                   DomainArchetype.BELL],
        primary_topology=SnapTopologyType.BELL,
        calibration_speed=0.6,
        noise_floor=0.2,
        description='Education: grading (gradient), understanding (bell), topics (categorical)',
    ),
    'coding': DomainProfile(
        name='coding',
        archetypes=[DomainArchetype.BINARY, DomainArchetype.CATEGORICAL,
                   DomainArchetype.COMBINATORIAL],
        primary_topology=SnapTopologyType.HEXAGONAL,
        calibration_speed=0.7,
        noise_floor=0.15,
        description='Coding: bug/no-bug (binary), approach (categorical), architecture (combinatorial)',
    ),
    'military': DomainProfile(
        name='military',
        archetypes=[DomainArchetype.DIRECTIONAL, DomainArchetype.BINARY,
                   DomainArchetype.UNIFORM],
        primary_topology=SnapTopologyType.OCTAHEDRAL,
        calibration_speed=0.4,
        noise_floor=0.5,
        description='Military: threats (directional), survivability (binary), resources (uniform)',
    ),
    'scientific': DomainProfile(
        name='scientific',
        archetypes=[DomainArchetype.GRADIENT, DomainArchetype.COMBINATORIAL,
                   DomainArchetype.BELL],
        primary_topology=SnapTopologyType.GRADIENT,
        calibration_speed=0.2,
        noise_floor=0.1,
        description='Scientific: measurements (gradient), hypotheses (bell), experiments (combinatorial)',
    ),
    'blackjack': DomainProfile(
        name='blackjack',
        archetypes=[DomainArchetype.UNIFORM, DomainArchetype.DIRECTIONAL,
                   DomainArchetype.CATEGORICAL],
        primary_topology=SnapTopologyType.UNIFORM,
        calibration_speed=0.8,
        noise_floor=0.1,
        description='Blackjack: card distribution (uniform), count (directional), strategy (categorical)',
    ),
}


@dataclass
class TransferMap:
    """
    Which snap topologies transfer between which domains.
    
    The transfer map encodes the cross-domain feel equivalence:
    two domains share a topology → calibration transfers.
    """
    source_domain: str
    target_domain: str
    transfer_quality: float          # 0..1: how well calibration transfers
    shared_topologies: List[SnapTopologyType]
    calibration_scale_factor: float  # Scale factor for tolerance adjustment
    
    def __repr__(self):
        topo_names = [t.value for t in self.shared_topologies]
        return (f"TransferMap({self.source_domain} → {self.target_domain}, "
                f"qual={self.transfer_quality:.2f}, "
                f"topo={topo_names})")


@dataclass
class CalibrationSpeed:
    """How quickly a snap calibrates to a new domain."""
    domain: str
    time_to_converge: int           # Expected observations to calibrate
    learning_rate: float            # Adaptation rate for this domain
    required_examples: int          # Minimum examples for meaningful calibration
    transfer_benefit: float         # How much cross-domain transfer helps [0..1]
    
    def __repr__(self):
        return (f"CalibrationSpeed({self.domain}, "
                f"converge_in={self.time_to_converge}, "
                f"lr={self.learning_rate:.4f})")


class FeelTransfer:
    """
    Maps snap topology from one domain to another.
    
    When two domains share a snap topology, the calibrated tolerance
    from domain A transfers directly to domain B. The 'feel' is the
    same because the shape of the possibility space is isomorphic.
    
    "The mind doesn't track domain content. It tracks snap topology.
    When the topology matches, the feel matches, regardless of what
    the tokens actually represent."
    — SNAPS-AS-ATTENTION.md
    
    Args:
        source_domain: Domain with calibrated tolerances.
        source_snap: SnapFunction calibrated in source_domain.
    
    Usage:
        transfer = FeelTransfer(source_domain="poker",
                                source_snap=SnapFunction(tolerance=0.15))
        
        # Transfer to medical domain
        medical_snap = transfer.transfer("medical")
        print(f"Tolerance in medical: {medical_snap.tolerance:.3f}")
        
        # Get all compatible domains
        compatible = transfer.compatible_domains()
        for domain, quality in compatible:
            print(f"  {domain}: {quality:.2f}")
    """
    
    def __init__(
        self,
        source_domain: str = "poker",
        source_snap: Optional[SnapFunction] = None,
    ):
        self.source_domain = source_domain
        self.source_snap = source_snap or SnapFunction(tolerance=0.1)
        
        # Domain profiles
        self._profiles = dict(BUILTIN_DOMAIN_PROFILES)
        
        # Tracked transfer maps
        self._transfer_maps: Dict[str, TransferMap] = {}
        
        # Calibration speed cache
        self._calibration_speeds: Dict[str, CalibrationSpeed] = {}
    
    def add_domain_profile(self, profile: DomainProfile):
        """Register a custom domain profile."""
        self._profiles[profile.name] = profile
    
    def transfer(
        self,
        target_domain: str,
        target_tolerance_override: Optional[float] = None,
    ) -> SnapFunction:
        """
        Transfer calibrated snap from source to target domain.
        
        The transfer preserves the snap topology and adjusts
        tolerance based on the target domain's noise floor and
        calibration speed.
        
        Args:
            target_domain: Domain to transfer to.
            target_tolerance_override: Explicit tolerance override.
        
        Returns:
            SnapFunction calibrated for the target domain.
        """
        source_profile = self._profiles.get(self.source_domain)
        target_profile = self._profiles.get(target_domain)
        
        if source_profile is None or target_profile is None:
            # Fallback: return a copy with same settings
            return SnapFunction(
                tolerance=self.source_snap.tolerance,
                topology=self.source_snap.topology,
            )
        
        # Determine shared topology affinity
        shared = self._find_shared_topologies(source_profile, target_profile)
        
        if not shared:
            # No shared topology — use target's primary topology with default tolerance
            target_topology = target_profile.primary_topology
            transfer_quality = 0.0
            tolerance = self.source_snap.tolerance
        else:
            target_topology = shared[0]
            transfer_quality = self._compute_transfer_quality(source_profile, target_profile)
            
            # Scale tolerance based on:
            # 1. Source tolerance
            # 2. Ratio of noise floors
            # 3. Calibration speed ratio
            noise_ratio = target_profile.noise_floor / max(source_profile.noise_floor, 0.01)
            speed_ratio = target_profile.calibration_speed / max(source_profile.calibration_speed, 0.01)
            
            tolerance = self.source_snap.tolerance * noise_ratio * transfer_quality
            
            # If target has override, use it
            if target_tolerance_override is not None:
                tolerance = target_tolerance_override
        
        # Create calibrated snap for target
        target_snap = SnapFunction(
            tolerance=max(tolerance, 0.01),
            topology=target_topology,
            adaptation_rate=target_profile.calibration_speed * 0.1,
        )
        
        # Record transfer map
        self._transfer_maps[target_domain] = TransferMap(
            source_domain=self.source_domain,
            target_domain=target_domain,
            transfer_quality=transfer_quality if shared else 0.0,
            shared_topologies=shared or [],
            calibration_scale_factor=transfer_quality if shared else 1.0,
        )
        
        return target_snap
    
    def _find_shared_topologies(
        self, source: DomainProfile, target: DomainProfile
    ) -> List[SnapTopologyType]:
        """Find topologies shared between two domains."""
        shared = []
        for topo, src_aff in source.topology_affinities.items():
            tgt_aff = target.topology_affinities.get(topo, 0.0)
            if src_aff > 0.3 and tgt_aff > 0.3:
                shared.append(topo)
        return sorted(shared, key=lambda t: (
            source.topology_affinities.get(t, 0.0) *
            target.topology_affinities.get(t, 0.0)
        ), reverse=True)
    
    def _compute_transfer_quality(
        self, source: DomainProfile, target: DomainProfile
    ) -> float:
        """Compute how well calibration transfers between domains."""
        if not source.topology_affinities or not target.topology_affinities:
            return 0.0
        
        # Weighted overlap of topology affinities
        total_overlap = 0.0
        total_weight = 0.0
        
        all_topos = set(source.topology_affinities) | set(target.topology_affinities)
        for topo in all_topos:
            src_aff = source.topology_affinities.get(topo, 0.0)
            tgt_aff = target.topology_affinities.get(topo, 0.0)
            overlap = min(src_aff, tgt_aff)
            weight = max(src_aff, tgt_aff)
            total_overlap += overlap * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        base_quality = total_overlap / total_weight
        
        # Adjust for noise floor compatibility
        noise_compatibility = 1.0 - abs(source.noise_floor - target.noise_floor)
        
        return float(np.clip(base_quality * noise_compatibility, 0.0, 1.0))
    
    def compatible_domains(self, min_quality: float = 0.3) -> List[Tuple[str, float]]:
        """Find domains compatible with source domain."""
        source_profile = self._profiles.get(self.source_domain)
        if source_profile is None:
            return []
        
        compatible = []
        for name, profile in self._profiles.items():
            if name == self.source_domain:
                continue
            quality = self._compute_transfer_quality(source_profile, profile)
            if quality >= min_quality:
                compatible.append((name, quality))
        
        return sorted(compatible, key=lambda x: x[1], reverse=True)
    
    def get_calibration_speed(self, domain: str) -> CalibrationSpeed:
        """
        Get calibration speed profile for a domain.
        
        Estimates how many observations needed to calibrate snap tolerance.
        """
        profile = self._profiles.get(domain)
        if profile is None:
            return CalibrationSpeed(
                domain=domain, time_to_converge=100,
                learning_rate=0.01, required_examples=10,
                transfer_benefit=0.0,
            )
        
        # Base: domains with simple archetypes calibrate faster
        archetype_complexity = {
            DomainArchetype.BINARY: 1,
            DomainArchetype.CATEGORICAL: 2,
            DomainArchetype.UNIFORM: 2,
            DomainArchetype.BELL: 3,
            DomainArchetype.GRADIENT: 4,
            DomainArchetype.DIRECTIONAL: 2,
            DomainArchetype.COMBINATORIAL: 5,
            DomainArchetype.CLUSTER: 3,
            DomainArchetype.META: 5,
        }
        complexity = max(
            archetype_complexity.get(a, 3) for a in profile.archetypes
        )
        
        base_observations = complexity * 10
        speed_factor = profile.calibration_speed
        time_to_converge = max(5, int(base_observations * (2 - speed_factor)))
        
        # Transfer benefit: how much cross-domain knowledge helps
        transfer_benefit = 0.0
        if self.source_domain != domain:
            _, quality = max(self.compatible_domains(min_quality=0.0), 
                           key=lambda x: x[1], default=(None, 0.0))
            transfer_benefit = quality if quality else 0.0
        
        return CalibrationSpeed(
            domain=domain,
            time_to_converge=time_to_converge,
            learning_rate=profile.calibration_speed * 0.02,
            required_examples=complexity,
            transfer_benefit=transfer_benefit,
        )
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'source_domain': self.source_domain,
            'domains_registered': list(self._profiles.keys()),
            'transfers_applied': list(self._transfer_maps.keys()),
            'profiles': [
                {
                    'name': p.name,
                    'archetypes': [a.value for a in p.archetypes],
                    'primary_topology': p.primary_topology.value,
                }
                for p in self._profiles.values()
            ],
        }
    
    def __repr__(self):
        return (f"FeelTransfer(source={self.source_domain}, "
                f"profiles={len(self._profiles)}, "
                f"transfers={len(self._transfer_maps)})")


def calibrate_for_domain(
    domain: str,
    sample_values: List[float],
    target_snap_rate: float = 0.9,
    topology: Optional[SnapTopologyType] = None,
) -> SnapFunction:
    """
    Helper: create a calibrated SnapFunction for a given domain.
    
    Uses the domain profile to pick the right topology and auto-calibrates
    tolerance from sample values.
    
    Args:
        domain: Domain name (must be in BUILTIN_DOMAIN_PROFILES or registered).
        sample_values: Sample observations from this domain.
        target_snap_rate: Desired snap rate (0.9 = 90% within tolerance).
        topology: Override topology (if None, uses domain's primary).
    
    Returns:
        Calibrated SnapFunction ready for this domain.
    
    Examples:
        >>> poker_snap = calibrate_for_domain("poker", [0.1, 0.2, 0.05, 0.3])
        >>> print(f"Tolerance: {poker_snap.tolerance:.3f}")
    """
    profile = BUILTIN_DOMAIN_PROFILES.get(domain)
    topo = topology or (profile.primary_topology if profile else SnapTopologyType.HEXAGONAL)
    
    snap = SnapFunction(tolerance=0.1, topology=topo)
    snap.calibrate(sample_values, target_snap_rate=target_snap_rate)
    
    # Additional domain-specific tuning
    if profile:
        snap.adaptation_rate = profile.calibration_speed * 0.1
    
    return snap
