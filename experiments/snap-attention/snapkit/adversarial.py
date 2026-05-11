"""
adversarial.py — Adversarial Snap Calibration
===============================================

The other minds are actively generating fake deltas to jam your snap function.
This module implements the adversarial layer of delta detection:

- Real vs manufactured deltas
- Multi-level recursive deception modeling (I know you know I know...)
- Poker: real vs fake tells
- Blackjack: look recreational while counting

"The snap doesn't tell you what's true. The snap tells you what you can SAFELY
IGNORE so you can think about what matters."
— SNAPS-AS-ATTENTION.md
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable, Tuple
from enum import Enum
import hashlib
import time


class DeceptionLevel(Enum):
    """Levels of recursive deception modeling."""
    HONEST = 0          # No deception — signals are genuine
    BLUFF = 1           # "I know" — basic fake signal generation
    CALL = 2            # "I know you know" — detecting the bluff
    REBLUFF = 3         # "I know you know I know" — double bluff
    RECALL = 4          # "I know you know I know you know" — meta-call
    PROBABILISTIC = 5   # Game-theoretic optimal mixed strategy


class AdversarialStance(Enum):
    """What an adversary is trying to do to your snap function."""
    JAM = "jam"               # Flood with fake deltas to exhaust attention
    MISDIRECT = "misdirect"   # Push attention toward irrelevant signals
    CALIBRATE = "calibrate"   # Learn your tolerance to exploit it
    MASK = "mask"             # Hide real deltas behind noise
    DECOY = "decoy"           # Create plausible fake that looks real


@dataclass
class SignalProfile:
    """
    A profile of a signal source — real deltas vs manufactured.
    
    Every signal from another intelligence has a real component
    (genuine information) and a fake component (noise injected
    to jam your snap function).
    """
    source_id: str
    real_signal_rate: float        # Fraction of signal that's genuine
    fake_signal_rate: float        # Fraction that's manufactured
    deception_level: DeceptionLevel  # How sophisticated the deception is
    signal_variance: float         # Natural variance vs injection variance
    consistency_score: float       # How consistent is the fake pattern
    
    @property
    def overall_trust(self) -> float:
        """Composite trust score [0..1]."""
        base = self.real_signal_rate - self.fake_signal_rate
        level_penalty = self.deception_level.value * 0.1
        return float(np.clip(base - level_penalty, 0.0, 1.0))


@dataclass
class FakeDelta:
    """
    A manufactured delta — designed to look real but isn't.
    
    The adversary generates these to consume your attention budget.
    """
    value: float
    magnitude: float
    plausibility: float     # How likely this seems real [0..1]
    style_signature: str    # Characteristic pattern of this adversary
    generated_by: str       # Which adversary generated this
    intended_tolerance: float  # The tolerance this fake targets
    
    def __repr__(self):
        return (f"FakeΔ(val={self.value:.3f}, mag={self.magnitude:.3f}, "
                f"plausibility={self.plausibility:.2f}, "
                f"style={self.style_signature[:8]})")


class FakeDeltaGenerator:
    """
    Generates plausible but manufactured deltas.
    
    An adversary uses this to inject noise into another agent's snap
    function. The generated deltas look real enough to consume attention
    but carry no genuine information.
    
    Strategy: mimic the distribution of real deltas the target expects.
    The better the mimic, the more attention budget is wasted.
    
    Args:
        style: Human-readable identifier for this adversary's style.
        deception_level: How recursive the deception is.
        mimic_precision: How precisely to match real delta distributions.
    
    Usage:
        generator = FakeDeltaGenerator(style="loose_aggressive", 
                                       deception_level=DeceptionLevel.BLUFF)
        fake = generator.generate(target_tolerance=0.1)
    """
    
    def __init__(
        self,
        style: str = "default",
        deception_level: DeceptionLevel = DeceptionLevel.BLUFF,
        mimic_precision: float = 0.7,
    ):
        self.style = style
        self.deception_level = deception_level
        self.mimic_precision = mimic_precision
        self._real_delta_history: List[float] = []
        self._generation_count = 0
        self._style_signature = hashlib.md5(style.encode()).hexdigest()[:16]
        self._rng = np.random.default_rng(int(time.time() * 1000) % 2**32)
    
    def observe_real_delta(self, magnitude: float):
        """Observe a real delta to learn the target's expected distribution."""
        self._real_delta_history.append(magnitude)
    
    def generate(self, target_tolerance: float = 0.1) -> FakeDelta:
        """
        Generate a plausible fake delta.
        
        The fake delta is designed to:
        1. Exceed the target's tolerance (so it demands attention)
        2. Fall within the real delta distribution (so it looks genuine)
        3. Target a specific actionability/urgency profile
        """
        self._generation_count += 1
        
        # If we have observed real deltas, mimic their distribution
        if len(self._real_delta_history) >= 5:
            mean_mag = float(np.mean(self._real_delta_history))
            std_mag = float(np.std(self._real_delta_history)) or 0.1
            magnitude = float(self._rng.normal(mean_mag, std_mag * self.mimic_precision))
        else:
            # Generate just above tolerance threshold — most attention-consuming
            magnitude = target_tolerance * (1.5 + self._rng.random() * 2.0)
        
        # Base value around a plausible center
        base = float(self._rng.normal(0.0, 1.0))
        
        # Plausibility: higher for well-mimicked fakes
        plausibility = float(np.clip(
            self.mimic_precision * (0.5 + self._rng.random() * 0.5),
            0.0, 1.0
        ))
        
        # Adjust for deception level
        if self.deception_level == DeceptionLevel.REBLUFF:
            plausibility *= 1.2  # Double bluff looks MORE real
        elif self.deception_level == DeceptionLevel.CALL:
            plausibility *= 0.8  # Being called means our fakes are detected
        
        return FakeDelta(
            value=base,
            magnitude=abs(magnitude),
            plausibility=float(np.clip(plausibility, 0.0, 1.0)),
            style_signature=self._style_signature,
            generated_by=self.style,
            intended_tolerance=target_tolerance,
        )
    
    def generate_batch(self, count: int, target_tolerance: float = 0.1) -> List[FakeDelta]:
        """Generate multiple fake deltas."""
        return [self.generate(target_tolerance) for _ in range(count)]
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'style': self.style,
            'deception_level': self.deception_level.value,
            'generation_count': self._generation_count,
            'observed_real_deltas': len(self._real_delta_history),
        }
    
    def __repr__(self):
        return (f"FakeDeltaGenerator(style={self.style}, "
                f"level={self.deception_level.name}, "
                f"generated={self._generation_count})")


class AdversarialDetector:
    """
    Distinguishes real deltas from manufactured ones.
    
    The adversarial detector learns the characteristic patterns of
    each adversary's fake deltas (style signatures) and uses Bayesian
    inference to classify incoming signals as real vs manufactured.
    
    This is the poker pro's ability to distinguish:
    - A genuine pause (actually thinking about a tough decision)
    - A manufactured pause (pretending to think about a trivial decision)
    
    Args:
        detection_threshold: Minimum confidence to classify as fake.
        memory_size: How many observations to keep per source.
    
    Usage:
        detector = AdversarialDetector()
        detector.learn_source_style("loose_aggressive", 
                                     style_signature="abc123...")
        
        is_fake = detector.classify(fake_candidate)
        confidence = detector.confidence
            
        # For each signal:
        result = detector.detect(signal_value, delta_magnitude)
    """
    
    def __init__(
        self,
        detection_threshold: float = 0.75,
        memory_size: int = 500,
    ):
        self.detection_threshold = detection_threshold
        self.memory_size = memory_size
        
        # Per-source tracking
        self._source_profiles: Dict[str, SignalProfile] = {}
        self._source_real_history: Dict[str, List[float]] = {}
        self._source_fake_history: Dict[str, List[float]] = {}
        self._observations: List[Dict[str, Any]] = []
        
        # Feature extractors
        self._style_signatures: Dict[str, List[float]] = {}  # source → feature vector
        
        self._true_positives = 0
        self._false_positives = 0
        self._true_negatives = 0
        self._false_negatives = 0
    
    def learn_source_profile(
        self,
        source_id: str,
        real_signal_rate: float = 0.5,
        fake_signal_rate: float = 0.3,
        deception_level: DeceptionLevel = DeceptionLevel.HONEST,
        signal_variance: float = 0.1,
    ) -> SignalProfile:
        """Register a profile for a known signal source."""
        profile = SignalProfile(
            source_id=source_id,
            real_signal_rate=real_signal_rate,
            fake_signal_rate=fake_signal_rate,
            deception_level=deception_level,
            signal_variance=signal_variance,
            consistency_score=1.0 - fake_signal_rate,
        )
        self._source_profiles[source_id] = profile
        self._source_real_history[source_id] = []
        self._source_fake_history[source_id] = []
        return profile
    
    def observe_signal(
        self,
        source_id: str,
        value: float,
        magnitude: float,
        known_classification: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Observe a signal and optionally know if it was real or fake.
        
        Args:
            source_id: Who sent the signal.
            value: The signal value.
            magnitude: Delta magnitude.
            known_classification: If known, True = real, False = fake.
        
        Returns:
            Classification result.
        """
        result = {
            'source': source_id,
            'value': value,
            'magnitude': magnitude,
            'classified_as_fake': False,
            'confidence': 0.0,
            'features': {},
        }
        
        # Extract features
        features = self._extract_features(source_id, magnitude)
        result['features'] = features
        
        # Classification
        is_fake_prob = self._compute_fake_probability(source_id, features)
        result['classified_as_fake'] = is_fake_prob >= self.detection_threshold
        result['confidence'] = is_fake_prob
        
        # Update tracking if ground truth is known
        if known_classification is not None:
            if known_classification:
                # Real signal
                self._source_real_history[source_id].append(magnitude)
                if result['classified_as_fake']:
                    self._false_positives += 1
                else:
                    self._true_negatives += 1
            else:
                # Fake signal
                self._source_fake_history[source_id].append(magnitude)
                if result['classified_as_fake']:
                    self._true_positives += 1
                else:
                    self._false_negatives += 1
        
        self._observations.append(result)
        if len(self._observations) > self.memory_size:
            self._observations = self._observations[-self.memory_size:]
        
        return result
    
    def _extract_features(self, source_id: str, magnitude: float) -> Dict[str, float]:
        """Extract features that distinguish real from fake deltas."""
        features = {}
        
        # Feature 1: Magnitude consistency with history
        real_hist = self._source_real_history.get(source_id, [])
        fake_hist = self._source_fake_history.get(source_id, [])
        
        if real_hist:
            real_mean = float(np.mean(real_hist))
            real_std = float(np.std(real_hist)) or 0.01
            z_real = abs(magnitude - real_mean) / real_std
            features['z_vs_real'] = float(np.clip(z_real, 0.0, 5.0))
        else:
            features['z_vs_real'] = 0.0
        
        if fake_hist:
            fake_mean = float(np.mean(fake_hist))
            fake_std = float(np.std(fake_hist)) or 0.01
            z_fake = abs(magnitude - fake_mean) / fake_std
            features['z_vs_fake'] = float(np.clip(z_fake, 0.0, 5.0))
        else:
            features['z_vs_fake'] = 5.0  # Unknown, so default to likely fake
        
        # Feature 2: Is the magnitude "too perfect" for the tolerance?
        # Real deltas aren't always just barely above tolerance
        features['suspicious_timing'] = 0.0
        
        # Feature 3: Source consistency
        profile = self._source_profiles.get(source_id)
        if profile:
            features['source_trust'] = profile.overall_trust
        else:
            features['source_trust'] = 0.5
        
        return features
    
    def _compute_fake_probability(
        self, source_id: str, features: Dict[str, float]
    ) -> float:
        """
        Compute probability that a signal is fake.
        
        Uses a naive Bayesian approach over extracted features.
        """
        prob = 0.0
        n_features = 0
        
        # If no history, assume 50/50
        source_has_history = (
            source_id in self._source_real_history and
            source_id in self._source_fake_history
        )
        if not source_has_history:
            return 0.5
        
        # High z_vs_real deviation → more likely fake
        if features.get('z_vs_real', 0) > 2.0:
            prob += 0.3
        
        # Low z_vs_fake deviation → more likely fake (similar to known fakes)
        if features.get('z_vs_fake', 5.0) < 1.0:
            prob += 0.4
        
        # Low source trust → more likely fake
        trust = features.get('source_trust', 0.5)
        prob += (1.0 - trust) * 0.3
        
        # Source profile prior
        profile = self._source_profiles.get(source_id)
        if profile:
            prob += profile.fake_signal_rate * 0.3
            prob -= profile.real_signal_rate * 0.2
        
        return float(np.clip(prob, 0.0, 1.0))
    
    def classify(self, delta_candidate: 'FakeDelta') -> bool:
        """
        Classify a single candidate as real or fake.
        
        Returns True if classified as fake.
        """
        result = self.observe_signal(
            source_id=delta_candidate.generated_by,
            value=delta_candidate.value,
            magnitude=delta_candidate.magnitude,
        )
        return result['classified_as_fake']
    
    # Performance metrics
    
    @property
    def precision(self) -> float:
        """Precision: true positives / (true positives + false positives)."""
        denom = self._true_positives + self._false_positives
        return self._true_positives / denom if denom > 0 else 0.0
    
    @property
    def recall(self) -> float:
        """Recall: true positives / (true positives + false negatives)."""
        denom = self._true_positives + self._false_negatives
        return self._true_positives / denom if denom > 0 else 0.0
    
    @property
    def f1_score(self) -> float:
        """F1 score for fake detection."""
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r > 0 else 0.0
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'sources_tracked': len(self._source_profiles),
            'total_observations': len(self._observations),
            'precision': self.precision,
            'recall': self.recall,
            'f1_score': self.f1_score,
            'true_positives': self._true_positives,
            'false_positives': self._false_positives,
            'true_negatives': self._true_negatives,
            'false_negatives': self._false_negatives,
        }
    
    def __repr__(self):
        return (f"AdversarialDetector(sources={len(self._source_profiles)}, "
                f"prec={self.precision:.2f}, rec={self.recall:.2f})")


class CamouflageEngine:
    """
    Masks your own delta detection from adversaries.
    
    When your snap function detects a real delta, the CamouflageEngine
    ensures that your reaction doesn't leak that information to
    adversarial observers. It generates false behavioral signals that
    look recreational/natural while you perform the actual cognitive work.
    
    This is the blackjack counter's PERFORMANCE OF NORMALCY:
    - Keep betting patterns that look recreational
    - Maintain consistent body language
    - Generate casual conversation at the right moments
    
    Args:
        camouflage_level: How aggressive the camouflage is [0..1].
            0 = no camouflage (honest signals)
            1 = full camouflage (perfect acting)
        natural_noise: Amount of natural variance to inject.
    
    Usage:
        engine = CamouflageEngine(camouflage_level=0.8)
        
        # Before acting on a delta:
        mask = engine.prepare_cover(real_action="increase_bet")
        
        # Execute cover actions while processing
        engine.apply_cover(mask)
        
        # After processing, check if camouflage held
        stats = engine.camouflage_statistics()
    """
    
    def __init__(
        self,
        camouflage_level: float = 0.6,
        natural_noise: float = 0.15,
    ):
        self.camouflage_level = camouflage_level
        self.natural_noise = natural_noise
        self._cover_actions: List[Dict[str, Any]] = []
        self._detection_events: List[Dict[str, Any]] = []
        self._rng = np.random.default_rng()
    
    def prepare_cover(
        self,
        real_action: str,
        real_action_magnitude: float = 1.0,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Prepare a camouflage cover for a real action.
        
        Returns a cover plan that masks the real action's cognitive
        signature with plausible alternatives.
        """
        context = context or {}
        
        # Generate distracting signals
        distraction_count = int(self.camouflage_level * 3) + 1
        
        cover = {
            'real_action': real_action,
            'distractions': [],
            'timing_delays': [],
            'noise_injection': 0.0,
        }
        
        for _ in range(distraction_count):
            # Create plausible alternatives
            distraction = self._generate_distraction(real_action)
            cover['distractions'].append(distraction)
        
        # Timing obfuscation: delay real action randomization
        base_delay = self.camouflage_level * 0.5  # Up to 0.5s delay
        jitter = float(self._rng.exponential(self.natural_noise))
        cover['timing_delays'] = {
            'pre_action': base_delay + jitter,
            'post_action': float(self._rng.exponential(self.natural_noise)),
        }
        
        # Noise injection: add random variance to observable signals
        cover['noise_injection'] = self.natural_noise * self.camouflage_level
        
        return cover
    
    def _generate_distraction(self, action: str) -> Dict[str, Any]:
        """Generate a plausible distracting action."""
        distractors = {
            'increase_bet': [
                {'type': 'adjust_seat', 'description': 'Adjust seating position'},
                {'type': 'check_chips', 'description': 'Count chips casually'},
                {'type': 'conversation', 'description': 'Mention unrelated topic'},
                {'type': 'stretch', 'description': 'Stretch arms/neck'},
            ],
            'fold': [
                {'type': 'look_away', 'description': 'Look at something off-table'},
                {'type': 'sigh', 'description': 'Audible sigh of disappointment'},
                {'type': 'conversation', 'description': 'Ask about next hand'},
            ],
            'call': [
                {'type': 'check_watch', 'description': 'Casually check time'},
                {'type': 'drink', 'description': 'Take a sip of drink'},
                {'type': 'conversation', 'description': 'Comment on the hand'},
            ],
            'raise': [
                {'type': 'count_chips', 'description': 'Stack chips deliberately'},
                {'type': 'conversation', 'description': 'Narrate the raise'},
                {'type': 'lean_forward', 'description': 'Lean into the table'},
            ],
        }
        
        category = distractors.get(action, distractors['call'])
        return self._rng.choice(category).copy()
    
    def apply_cover(self, cover: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the cover actions (record what was done)."""
        self._cover_actions.append(cover)
        return cover.get('distractions', [])
    
    def record_detection_event(
        self, 
        delta_magnitude: float,
        was_detected_by_adversary: bool,
    ):
        """Record whether a camouflage event was successful."""
        self._detection_events.append({
            'delta_magnitude': delta_magnitude,
            'was_detected': was_detected_by_adversary,
            'camouflage_level': self.camouflage_level,
        })
        # Adjust camouflage level based on outcome
        if len(self._detection_events) >= 10:
            recent = self._detection_events[-10:]
            detection_rate = sum(1 for e in recent if e['was_detected']) / len(recent)
            if detection_rate > 0.3:
                # Being detected too often — increase camouflage
                self.camouflage_level = min(1.0, self.camouflage_level + 0.05)
            elif detection_rate < 0.05:
                # Too much camouflage, wasting cognition
                self.camouflage_level = max(0.0, self.camouflage_level - 0.05)
    
    @property
    def camouflage_statistics(self) -> Dict[str, Any]:
        if not self._detection_events:
            return {'detection_rate': 0.0, 'cover_actions': 0}
        
        detection_rate = sum(1 for e in self._detection_events if e['was_detected'])
        return {
            'detection_rate': detection_rate / len(self._detection_events),
            'cover_actions': len(self._cover_actions),
            'camouflage_level': self.camouflage_level,
            'total_detection_events': len(self._detection_events),
        }
    
    def __repr__(self):
        stat = self.camouflage_statistics
        return (f"CamouflageEngine(level={self.camouflage_level:.2f}, "
                f"detection_rate={stat['detection_rate']:.2f})")


class BluffCalibration:
    """
    Multi-level recursive deception modeling.
    
    Implements the "I know you know I know you know..." recursion:
    - Level 0: Honest signals (no deception)
    - Level 1: Basic bluff (I generate fake deltas)
    - Level 2: Call (I detect your bluff)
    - Level 3: Re-bluff (I know you'll call, so I double-bluff)
    - Level N: Nth-order theory of mind
    
    "The game is in the space between minds — where each intelligence
    tries to out-fake the other's delta detection."
    — SNAPS-AS-ATTENTION.md
    
    Args:
        max_depth: Maximum level of recursive modeling.
        base_strategy: Initial stance for each level.
    
    Usage:
        calibrator = BluffCalibration(max_depth=5)
        
        # Model the adversary
        calibrator.model_adversary("loose_aggressive", 
                                    estimated_level=1)
        
        # What's the optimal response?
        response = calibrator.optimize_response(
            my_level=2, adversary="loose_aggressive"
        )
    """
    
    def __init__(
        self,
        max_depth: int = 5,
        base_strategy: str = "mixed",
    ):
        self.max_depth = max_depth
        self.base_strategy = base_strategy
        
        # Level-specific models
        self._level_strategies: Dict[int, Dict[str, Any]] = {}
        self._adversary_models: Dict[str, Dict[int, float]] = {}
        self._game_history: List[Dict[str, Any]] = []
        
        # Initialize level models
        for level in range(max_depth + 1):
            self._init_level(level)
    
    def _init_level(self, level: int):
        """Initialize strategy for a given recursion level."""
        if level == 0:
            self._level_strategies[level] = {
                'name': 'HONEST',
                'bluff_probability': 0.0,
                'call_probability': 0.0,
                'description': 'All signals are genuine',
                'optimal_against': 'Any (no gain from deception)',
            }
        elif level == 1:
            self._level_strategies[level] = {
                'name': 'BLUFF',
                'bluff_probability': 0.3,
                'call_probability': 0.0,
                'description': 'I send fake deltas, assume you are honest',
                'optimal_against': 'Honest agents',
            }
        elif level == 2:
            self._level_strategies[level] = {
                'name': 'CALL',
                'bluff_probability': 0.1,
                'call_probability': 0.7,
                'description': 'I detect your bluffs, I signal honestly',
                'optimal_against': 'Basic bluffers',
            }
        elif level == 3:
            self._level_strategies[level] = {
                'name': 'REBLUFF',
                'bluff_probability': 0.5,
                'call_probability': 0.3,
                'description': 'I know you detect bluffs, so I double-bluff',
                'optimal_against': 'CALL-level agents',
            }
        elif level == 4:
            self._level_strategies[level] = {
                'name': 'RECALL',
                'bluff_probability': 0.2,
                'call_probability': 0.8,
                'description': 'I know you double-bluff, I detect it',
                'optimal_against': 'REBLUFF-level agents',
            }
        else:
            self._level_strategies[level] = {
                'name': f'LEVEL_{level}',
                'bluff_probability': 0.3,
                'call_probability': 0.5,
                'description': f'Level {level} recursive modeling',
                'optimal_against': f'Level {level - 1} agents',
            }
    
    def model_adversary(
        self,
        adversary_id: str,
        estimated_level: int = 1,
        confidence: float = 0.5,
    ):
        """
        Model an adversary's deception level.
        
        Args:
            adversary_id: Unique identifier for the adversary.
            estimated_level: Estimated deception level of the adversary.
            confidence: How confident we are in the estimate.
        """
        self._adversary_models[adversary_id] = {
            'estimated_level': estimated_level,
            'confidence': confidence,
            'last_updated': len(self._game_history),
        }
    
    def update_adversary_model(
        self,
        adversary_id: str,
        observed_bluff_rate: float,
        observed_call_rate: float,
    ) -> int:
        """
        Update adversary model based on observed behavior.
        
        Uses observed bluff and call rates to infer the adversary's
        deception level.
        
        Returns the newly estimated level.
        """
        # Compare observation to level models
        best_level = 1
        best_distance = float('inf')
        
        for level, strategy in self._level_strategies.items():
            if level > self.max_depth:
                break
            b_dist = abs(strategy['bluff_probability'] - observed_bluff_rate)
            c_dist = abs(strategy['call_probability'] - observed_call_rate)
            distance = b_dist + c_dist
            
            if distance < best_distance:
                best_distance = distance
                best_level = level
        
        # Update with decaying confidence
        old = self._adversary_models.get(adversary_id, {})
        old_confidence = old.get('confidence', 0.0)
        
        new_level = best_level
        new_confidence = min(1.0, old_confidence + 0.1)
        
        self._adversary_models[adversary_id] = {
            'estimated_level': new_level,
            'confidence': new_confidence,
            'last_updated': len(self._game_history),
        }
        
        return new_level
    
    def optimize_response(
        self,
        my_level: int = 2,
        adversary_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Determine optimal response level given adversary model.
        
        Returns:
            Dict with recommended level, bluff_prob, call_prob, and reasoning.
        """
        adv_model = self._adversary_models.get(adversary_id) if adversary_id else None
        
        if adv_model is None:
            # No adversary model — play safe with mixed strategy
            return {
                'recommended_level': 1,
                'bluff_probability': 0.15,
                'call_probability': 0.15,
                'reasoning': 'No adversary model — low-risk baseline',
                'strategy_name': 'DEFENSIVE',
            }
        
        adv_level = adv_model['estimated_level']
        adv_conf = adv_model['confidence']
        
        # Optimal response: adversary level + 1 (stay one step ahead)
        # But account for confidence — less confident = closer to defensive
        confidence_weight = adv_conf
        
        if adv_level >= self.max_depth:
            # Adversary may be at our max — use probabilistic mixed strategy
            recommended = adv_level
        else:
            recommended = adv_level + 1
        
        # Apply confidence weighting
        effective_level = int(round(adv_level + confidence_weight))
        effective_level = min(effective_level, self.max_depth)
        
        strategy = self._level_strategies[effective_level]
        
        return {
            'recommended_level': effective_level,
            'adversary_estimated_level': adv_level,
            'confidence': adv_conf,
            'bluff_probability': strategy['bluff_probability'],
            'call_probability': strategy['call_probability'],
            'reasoning': f'Adv at level {adv_level} (conf={adv_conf:.1f}) → respond at level {effective_level}',
            'strategy_name': strategy['name'],
            'strategy_description': strategy['description'],
        }
    
    def record_round(
        self,
        my_bluffed: bool,
        adversary_called: bool,
        adversary_id: Optional[str] = None,
    ):
        """
        Record the outcome of a round for model refinement.
        
        Args:
            my_bluffed: Did we generate a fake delta?
            adversary_called: Did the adversary detect our bluff?
            adversary_id: Which adversary (if tracking).
        """
        self._game_history.append({
            'round': len(self._game_history),
            'my_bluffed': my_bluffed,
            'adversary_called': adversary_called,
        })
        
        if adversary_id:
            # Update adversary model based on outcome
            recent = self._game_history[-20:]
            if recent:
                observed_bluff = sum(1 for r in recent if r['adversary_called']) / len(recent)
                observed_call = sum(1 for r in recent if r['my_bluffed']) / len(recent)
                self.update_adversary_model(adversary_id, observed_bluff, observed_call)
    
    @property
    def statistics(self) -> Dict[str, Any]:
        return {
            'max_depth': self.max_depth,
            'adversaries_tracked': len(self._adversary_models),
            'rounds_played': len(self._game_history),
            'level_strategies': {
                level: info['name']
                for level, info in self._level_strategies.items()
                if level <= self.max_depth
            },
        }
    
    def __repr__(self):
        return (f"BluffCalibration(depth={self.max_depth}, "
                f"adversaries={len(self._adversary_models)}, "
                f"rounds={len(self._game_history)})")
