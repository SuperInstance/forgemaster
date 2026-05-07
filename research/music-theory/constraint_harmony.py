#!/usr/bin/env python3
"""
Constraint-Theory-Based Music Harmony System
=============================================

A mathematical formalization of Western harmony through Eisenstein integers,
Galois connections, holonomy, and temporal snap.

Built from the same constraint-theory primitives that drive Polyformalism.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional, Callable


# ---------------------------------------------------------------------------
# Eisenstein integer arithmetic
# ---------------------------------------------------------------------------

OMEGA_RE = -0.5
OMEGA_IM = math.sqrt(3) / 2


def eisenstein_norm(a: int, b: int) -> int:
    """N(a + bω) = a² - ab + b²"""
    return a * a - a * b + b * b


def eisenstein_multiply(a1: int, b1: int, a2: int, b2: int) -> Tuple[int, int]:
    """Multiply two Eisenstein integers (a1+b1ω)(a2+b2ω) = (a1a2 - b1b2) + (a1b2 + b1a2 - b1b2)ω"""
    return (a1 * a2 - b1 * b2, a1 * b2 + b1 * a2 - b1 * b2)


def ratio_to_eisenstein(n: int, d: int) -> Tuple[float, float, int]:
    """Map a just intonation ratio n:d to the nearest Eisenstein lattice point.

    Uses the basis: fifths = log₂(3/2), thirds = log₂(5/4)
    Returns (a, b, norm) of nearest lattice point, and the deviation.
    """
    ratio = n / d
    if ratio == 1.0:
        return (0, 0, 0)

    log_ratio = math.log2(ratio)

    # Basis vectors in log₂ space
    p5 = math.log2(3 / 2)  # ≈ 0.585
    m3 = math.log2(6 / 5)  # ≈ 0.263

    # Decompose log_ratio in (fifths, minor_thirds) basis
    # log_ratio = a * p5 + b * m3  (approximately)
    # Solve via least-squares: [p5, m3] [a, b]^T = log_ratio
    det = p5 * p5 + m3 * m3
    a_f = (log_ratio * p5) / det
    b_f = (log_ratio * m3) / det

    # Round to nearest integers
    a = round(a_f)
    b = round(b_f)
    norm = eisenstein_norm(a, b)

    return (a, b, norm)


# ---------------------------------------------------------------------------
# Core constraint harmony system
# ---------------------------------------------------------------------------

class ConstraintHarmony:
    """Constraint-theory-based music harmony system."""

    # Just intonation ratios mapped from Eisenstein norms
    RATIOS: Dict[str, Tuple[int, int]] = {
        'unison': (1, 1),
        'minor_second': (16, 15),
        'major_second': (9, 8),
        'minor_third': (6, 5),
        'major_third': (5, 4),
        'perfect_fourth': (4, 3),
        'tritone': (45, 32),
        'perfect_fifth': (3, 2),
        'minor_sixth': (8, 5),
        'major_sixth': (5, 3),
        'minor_seventh': (9, 5),
        'major_seventh': (15, 8),
        'octave': (2, 1),
    }

    CHORD_TYPES: Dict[str, List[str]] = {
        'maj':  ['unison', 'major_third', 'perfect_fifth'],
        'min':  ['unison', 'minor_third', 'perfect_fifth'],
        'dim':  ['unison', 'minor_third', 'tritone'],
        'aug':  ['unison', 'major_third', 'major_sixth'],
        'dom7': ['unison', 'major_third', 'perfect_fifth', 'minor_seventh'],
        'maj7': ['unison', 'major_third', 'perfect_fifth', 'major_seventh'],
        'min7': ['unison', 'minor_third', 'perfect_fifth', 'minor_seventh'],
        'sus4': ['unison', 'perfect_fourth', 'perfect_fifth'],
        'sus2': ['unison', 'major_second', 'perfect_fifth'],
    }

    def __init__(self, fundamental: float = 261.626):  # Middle C
        self.fundamental = fundamental
        self.current_chord = None
        self.history: List[List[float]] = []
        self.tempo_map: Dict[int, float] = {}
        self.swing_ratio: float = 0.5  # 0.5 = straight, 0.67 = swing
        self.expression_params = {
            'deadband_ms': 30,
            'rubato_elasticity': 0.1,
            'dissonance_tolerance': 0.3,
            'dynamic_range': 0.8,
        }

    # ---- Frequency computation ------------------------------------------------

    def frequency(self, ratio_name: str, octave: int = 0) -> float:
        """Get frequency for a named ratio at given octave offset."""
        n, d = self.RATIOS[ratio_name]
        return self.fundamental * (n / d) * (2 ** octave)

    def chord_frequencies(self, ratio_names: List[str], octave: int = 0) -> List[float]:
        """Get frequencies for a chord (list of ratio names)."""
        return [self.frequency(r, octave) for r in ratio_names]

    def chord(self, root_ratio: str, chord_type: str, octave: int = 0) -> List[float]:
        """Build a chord from a root ratio and chord type."""
        root_freq = self.frequency(root_ratio, octave)
        intervals = self.CHORD_TYPES[chord_type]
        return [root_freq * (self.RATIOS[iv][0] / self.RATIOS[iv][1]) for iv in intervals]

    # ---- Voice leading (Galois connection) ------------------------------------

    def check_voice_leading(self, chord_from: List[float], chord_to: List[float]) -> Tuple[bool, float, List]:
        """Galois connection: check that voice leading is smooth.

        Each voice moves by the smallest interval (the adjoint assignment).
        Returns: (is_smooth, max_interval, movements)
        """
        f_from = sorted(chord_from)
        f_to = sorted(chord_to)

        if len(f_from) != len(f_to):
            # Pad shorter chord by doubling root
            while len(f_from) < len(f_to):
                f_from.append(f_from[0])
            while len(f_to) < len(f_from):
                f_to.append(f_to[0])

        movements = []
        for f1, f2 in zip(f_from, f_to):
            ratio = f2 / f1
            # Find closest named interval
            min_dist = float('inf')
            closest = None
            for name, (n, d) in self.RATIOS.items():
                dist = abs(ratio - n / d)
                if dist < min_dist:
                    min_dist = dist
                    closest = name
            # Also check inversions (ratio < 1)
            for name, (n, d) in self.RATIOS.items():
                dist = abs(ratio - d / n)
                if dist < min_dist:
                    min_dist = dist
                    closest = f"{name}_(inv)"
            movements.append({
                'from': f1,
                'to': f2,
                'interval': closest,
                'deviation': min_dist,
                'cents': 1200 * math.log2(f2 / f1),
            })

        max_interval = max(m['deviation'] for m in movements)
        is_smooth = max_interval < self.expression_params['dissonance_tolerance']
        return is_smooth, max_interval, movements

    # ---- Holonomy (tonal closure) ---------------------------------------------

    def check_holonomy(self, progression: List[List[float]]) -> float:
        """Check if a chord progression has zero holonomy (returns to tonic).

        Returns: holonomy value (0 = perfect return, higher = more deviation).
        """
        if len(progression) < 2:
            return 0.0

        start = sorted(progression[0])
        end = sorted(progression[-1])

        if len(start) != len(end):
            return float('inf')

        total_deviation = 0.0
        for f_start, f_end in zip(start, end):
            cents = abs(1200 * math.log2(f_end / f_start))
            total_deviation += cents

        return total_deviation

    def holonomy_class(self, value: float) -> str:
        """Classify holonomy value into musical meaning."""
        if value < 10:
            return "ZERO — Perfect resolution to tonic"
        elif value < 50:
            return "SMALL — Plagal cadence, gentle return"
        elif value < 200:
            return "MEDIUM — Deceptive cadence, modal mixture"
        elif value < 500:
            return "LARGE — Chromatic modulation, distant key"
        else:
            return "INFINITE — Full circle-of-fifths territory"

    # ---- Temporal snap (rhythm & groove) --------------------------------------

    def compute_swing_timing(self, beats: List[float], measure_start_time: float = 0.0) -> List[float]:
        """Apply swing ratio to a list of beat positions.

        swing_ratio=0.5 → straight (50/50)
        swing_ratio=0.67 → swing (67/33)
        """
        swung = []
        for i, beat in enumerate(beats):
            if i % 2 == 0:
                swung.append(beat)
            else:
                prev = beats[i - 1]
                next_down = beats[i + 1] if i + 1 < len(beats) else beat + (beat - prev)
                swung.append(prev + (next_down - prev) * self.swing_ratio)
        return swung

    def compute_microtiming(self, beat_positions: List[float],
                            groove_offsets: List[float]) -> List[float]:
        """Apply microtiming offsets (snap gaps) to beat positions.

        groove_offsets: list of ms offsets (positive = late, negative = early)
        """
        ms_to_sec = 0.001
        return [
            b + offset * ms_to_sec
            for b, offset in zip(beat_positions, groove_offsets)
        ]

    # ---- Tempo map (spline through anchors) -----------------------------------

    def compute_tempo_map(self, anchors: List[Tuple[int, float]],
                          base_bpm: float = 120.0) -> Callable[[float], float]:
        """Linear interpolation through tempo anchors.

        anchors: list of (measure_number, bpm) pairs.
        Returns: function that gives BPM at any (fractional) measure.
        """
        if not anchors:
            return lambda m: base_bpm

        sorted_anchors = sorted(anchors, key=lambda x: x[0])

        def tempo_at(measure: float) -> float:
            if measure <= sorted_anchors[0][0]:
                return sorted_anchors[0][1]
            if measure >= sorted_anchors[-1][0]:
                return sorted_anchors[-1][1]
            for i in range(len(sorted_anchors) - 1):
                m1, b1 = sorted_anchors[i]
                m2, b2 = sorted_anchors[i + 1]
                if m1 <= measure <= m2:
                    t = (measure - m1) / (m2 - m1)
                    return b1 + t * (b2 - b1)
            return base_bpm

        return tempo_at

    # ---- Full progression analysis --------------------------------------------

    def analyze_progression(self, progression: List[List[float]],
                            labels: Optional[List[str]] = None) -> Dict:
        """Full analysis of a chord progression.

        Returns dict with voice leading, holonomy, tension profile, surprises.
        """
        results = {
            'num_chords': len(progression),
            'holonomy': self.check_holonomy(progression),
            'holonomy_class': '',
            'voice_leading_smooth': [],
            'intervals': [],
            'tension_profile': [],
            'surprises': [],
        }
        results['holonomy_class'] = self.holonomy_class(results['holonomy'])

        for i in range(len(progression) - 1):
            smooth, max_int, movements = self.check_voice_leading(
                progression[i], progression[i + 1]
            )
            results['voice_leading_smooth'].append(smooth)
            results['intervals'].append(movements)
            results['tension_profile'].append(max_int)

        # Surprises = transitions with tension > 2× average
        if results['tension_profile']:
            avg_tension = sum(results['tension_profile']) / len(results['tension_profile'])
            results['surprises'] = [
                i for i, t in enumerate(results['tension_profile'])
                if t > 2 * avg_tension
            ]
            results['avg_tension'] = avg_tension
        else:
            results['avg_tension'] = 0.0

        return results

    # ---- Intent vector --------------------------------------------------------

    @staticmethod
    def intent_vector_description() -> Dict[str, str]:
        """The 9-channel intent vector mapped to musical parameters."""
        return {
            'C1_Urgency': 'Tempo push/pull, rhythmic drive',
            'C2_Scope': 'Orchestration density, active voice count',
            'C3_Confidence': 'Intonation certainty, vibrato depth',
            'C4_Priority': 'Voice leading hierarchy (melody vs bass)',
            'C5_Context': 'Genre, style, era constraints',
            'C6_Intent': 'Emotional trajectory (tension → release)',
            'C7_Risk': 'Dissonance tolerance',
            'C8_Domain': 'Tonal center, key, mode',
            'C9_Delta': 'Rate of harmonic change',
        }

    # ---- Eisenstein correspondence --------------------------------------------

    @classmethod
    def eisenstein_table(cls) -> List[Dict]:
        """Compute Eisenstein norm correspondence for all ratios."""
        table = []
        for name, (n, d) in cls.RATIOS.items():
            a, b, norm = ratio_to_eisenstein(n, d)
            ratio_val = n / d
            log_ratio = math.log2(ratio_val) if ratio_val > 0 else 0
            table.append({
                'name': name,
                'ratio': (n, d),
                'ratio_val': ratio_val,
                'cents': 1200 * log_ratio,
                'eisenstein': (a, b),
                'norm': norm,
                'snaps': norm > 0 or ratio_val == 1.0,
            })
        return table


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

def demo():
    """Full demonstration of the constraint harmony system."""
    ch = ConstraintHarmony(fundamental=261.626)  # Middle C = C4

    print("=" * 72)
    print("CONSTRAINT-THEORY MUSIC HARMONY SYSTEM")
    print("=" * 72)
    print()

    # ---- Eisenstein Norm Correspondence ----------------------------------------
    print("━━━ EISENSTEIN NORM CORRESPONDENCE ━━━")
    print(f"{'Ratio':<16} {'Cents':>8} {'Eisenstein':>14} {'Norm':>6} {'Snaps':>7}")
    print("-" * 55)
    for row in ch.eisenstein_table():
        n, d = row['ratio']
        snaps = "✓" if row['snaps'] else "✗"
        print(f"{row['name']:<16} {row['cents']:>8.1f}   ({row['eisenstein'][0]:>2},{row['eisenstein'][1]:>2})    {row['norm']:>4}    {snaps}")
    print()

    # ---- ii-V-I in C Major ----------------------------------------------------
    print("━━━ II-V-I PROGRESSION IN C MAJOR (Classic Jazz Cadence) ━━━")
    print()

    # Build chords relative to C fundamental
    # Dm7: D + min7 = [unison, m3, P5, m7] relative to D
    # But we're rooted at C, so we need ratios from C
    # D = C * 9/8, so Dm7 = [9/8, 9/8 * 6/5, 9/8 * 3/2, 9/8 * 9/5]
    # G7: G = C * 3/2, G7 = [3/2, 3/2 * 5/4, 3/2 * 3/2, 3/2 * 9/5]
    # Cmaj7: C = 1, Cmaj7 = [1, 5/4, 3/2, 15/8]

    # Simplified: use triads for clearer voice leading
    d_min = ch.chord('major_second', 'min')  # Dm from C
    g_dom7 = ch.chord('perfect_fifth', 'dom7')  # G7 from C
    c_maj = ch.chord('unison', 'maj')  # C major from C

    # Also build 7th chords
    d_min7 = ch.chord('major_second', 'min7')  # Dm7 from C
    c_maj7 = ch.chord('unison', 'maj7')  # Cmaj7 from C

    ii_V_I = [d_min, g_dom7[:3], c_maj]  # Triads for cleaner VL

    print("Chord frequencies (Hz):")
    labels_ii_v_i = ['Dm (ii)', 'G (V)', 'C (I)']
    for label, chord_freqs in zip(labels_ii_v_i, ii_V_I):
        freqs_str = ", ".join(f"{f:.1f}" for f in sorted(chord_freqs))
        print(f"  {label}: [{freqs_str}]")
    print()

    # Voice leading check
    print("Voice leading (Galois connection):")
    for i in range(len(ii_V_I) - 1):
        smooth, max_int, movements = ch.check_voice_leading(ii_V_I[i], ii_V_I[i + 1])
        from_label = labels_ii_v_i[i]
        to_label = labels_ii_v_i[i + 1]
        print(f"  {from_label} → {to_label}: smooth={smooth}, max_deviation={max_int:.4f}")
        for m in movements:
            print(f"    {m['from']:.1f} Hz → {m['to']:.1f} Hz  "
                  f"({m['interval']}, {m['cents']:+.1f}¢, dev={m['deviation']:.4f})")
    print()

    # Holonomy check
    # ii-V-I doesn't return to ii, it goes ii → V → I
    # For holonomy we want a full cycle: I → ii → V → I
    full_ii_v_i = [c_maj, d_min, g_dom7[:3], c_maj]
    hol = ch.check_holonomy(full_ii_v_i)
    print(f"Holonomy of I → ii → V → I: {hol:.2f} cents ({ch.holonomy_class(hol)})")
    print()

    # ---- Tritone Substitution --------------------------------------------------
    print("━━━ TRITONE SUBSTITUTION: ii → bII7 → I ━━━")
    print()

    # bII7 = Db7: tritone above G
    # Db = C * 16/15 (minor second up)
    # But more precisely: bII = tritone up from V = 45/32 * 3/2... no.
    # bII7 root = G's tritone = Db. Db/C = 16/15 (up a minor second) or 45/32 (tritone up)
    # Actually bII = Neapolitan = Db. In just: Db = C * 16/15
    db7 = ch.chord('minor_second', 'dom7')  # Db7 from C (bII7)

    ii_bII7_I = [d_min, db7[:3], c_maj]

    print("Tritone substitution chord frequencies:")
    labels_tritone = ['Dm (ii)', 'Db (bII)', 'C (I)']
    for label, chord_freqs in zip(labels_tritone, ii_bII7_I):
        freqs_str = ", ".join(f"{f:.1f}" for f in sorted(chord_freqs))
        print(f"  {label}: [{freqs_str}]")
    print()

    print("Voice leading with tritone sub:")
    for i in range(len(ii_bII7_I) - 1):
        smooth, max_int, movements = ch.check_voice_leading(ii_bII7_I[i], ii_bII7_I[i + 1])
        print(f"  {labels_tritone[i]} → {labels_tritone[i + 1]}: smooth={smooth}, max_dev={max_int:.4f}")
        for m in movements:
            print(f"    {m['from']:.1f} → {m['to']:.1f} ({m['interval']}, {m['cents']:+.1f}¢)")
    print()

    hol_tritone = ch.check_holonomy([c_maj] + ii_bII7_I + [c_maj])
    print(f"Holonomy of I → ii → bII → I: {hol_tritone:.2f} cents ({ch.holonomy_class(hol_tritone)})")
    print(f"  → Same holonomy class as ii-V-I? {abs(hol - hol_tritone) < 50}")
    print()

    # ---- 12-Bar Blues ----------------------------------------------------------
    print("━━━ 12-BAR BLUES PROGRESSION ━━━")
    print()

    # I = C, IV = F, V = G
    I = ch.chord('unison', 'dom7')       # C7
    IV = ch.chord('perfect_fourth', 'dom7')  # F7
    V = ch.chord('perfect_fifth', 'dom7')    # G7

    blues_form = [I, I, I, I, IV, IV, I, I, V, IV, I, V]
    blues_labels = ['I7', 'I7', 'I7', 'I7', 'IV7', 'IV7', 'I7', 'I7',
                    'V7', 'IV7', 'I7', 'V7']

    print("12-bar blues (dominant 7ths):")
    for bar, (label, chord_f) in enumerate(zip(blues_labels, blues_form), 1):
        freqs_str = ", ".join(f"{f:.1f}" for f in sorted(chord_f))
        print(f"  Bar {bar:>2}: {label:<4} [{freqs_str}]")
    print()

    blues_analysis = ch.analyze_progression(blues_form, blues_labels)
    print(f"Holonomy: {blues_analysis['holonomy']:.2f} cents ({blues_analysis['holonomy_class']})")
    print(f"Average tension: {blues_analysis['avg_tension']:.4f}")
    print(f"Smooth transitions: {sum(blues_analysis['voice_leading_smooth'])}/{len(blues_analysis['voice_leading_smooth'])}")
    if blues_analysis['surprises']:
        print(f"Surprises at transitions: {blues_analysis['surprises']}")
        for s in blues_analysis['surprises']:
            print(f"  Bar {s+1}→{s+2}: {blues_labels[s]} → {blues_labels[s+1]} (tension={blues_analysis['tension_profile'][s]:.4f})")
    print()

    # Tension profile
    print("Tension profile:")
    for i, (tension, label_pair) in enumerate(zip(blues_analysis['tension_profile'],
                                                   zip(blues_labels, blues_labels[1:]))):
        bar = "█" * int(tension * 100)
        print(f"  {label_pair[0]:>3}→{label_pair[1]:<3}: {tension:.4f} {bar}")
    print()

    # ---- Swing Timing ---------------------------------------------------------
    print("━━━ SWING TIMING (4-bar phrase, 4/4 time) ━━━")
    print()

    ch.swing_ratio = 0.5  # Straight
    beats_straight = [i * 0.5 for i in range(32)]  # 8th notes for 4 bars
    swung_straight = ch.compute_swing_timing(beats_straight)

    ch.swing_ratio = 0.67  # Swing
    swung_swing = ch.compute_swing_timing(beats_straight)

    print(f"{'Beat':>5} {'Straight':>10} {'Swing':>10} {'Offset':>10}")
    print("-" * 40)
    for i in range(16):  # First 2 bars
        offset = (swung_swing[i] - swung_straight[i]) * 1000
        print(f"{i:>5} {swung_straight[i]:>10.3f} {swung_swing[i]:>10.3f} {offset:>+10.1f}ms")
    print()

    # ---- Tempo Map -------------------------------------------------------------
    print("━━━ TEMPO MAP (Spline Through Anchors) ━━━")
    print()

    anchors = [
        (1, 65),    # Intro: slow
        (8, 65),    # Intro ends
        (9, 100),   # Verse starts
        (24, 100),  # Verse ends
        (25, 130),  # Chorus
        (40, 130),  # Chorus ends
        (41, 85),   # Bridge
        (48, 85),   # Bridge ends
        (49, 135),  # Final chorus
        (56, 70),   # Outro deceleration
    ]

    tempo_fn = ch.compute_tempo_map(anchors, base_bpm=100)

    print(f"{'Measure':>8} {'BPM':>8} {'Visualization':>40}")
    print("-" * 60)
    for m in range(1, 61):
        bpm = tempo_fn(m)
        bar = "▓" * int(bpm / 4)
        section = ""
        if m <= 8: section = " (intro)"
        elif m <= 24: section = " (verse)"
        elif m <= 40: section = " (chorus)"
        elif m <= 48: section = " (bridge)"
        else: section = " (outro)"
        if m in [1, 9, 25, 41, 49, 56]:
            print(f"{m:>8} {bpm:>8.1f} {bar}{section}")
        elif m % 8 == 0:
            print(f"{m:>8} {bpm:>8.1f} {bar}")
    print()

    # ---- Intent Vector ---------------------------------------------------------
    print("━━━ 9-CHANNEL INTENT VECTOR ━━━")
    print()
    for channel, meaning in ch.intent_vector_description().items():
        print(f"  {channel:<16}: {meaning}")
    print()

    # ---- Full Analysis Summary -------------------------------------------------
    print("━━━ ANALYSIS SUMMARY ━━━")
    print()
    print("ii-V-I (classic):")
    r1 = ch.analyze_progression(ii_V_I)
    print(f"  Holonomy: {r1['holonomy']:.2f}¢ → {r1['holonomy_class']}")
    print(f"  All smooth: {all(r1['voice_leading_smooth'])}")
    print()

    print("ii-bII-I (tritone sub):")
    r2 = ch.analyze_progression(ii_bII7_I)
    print(f"  Holonomy: {r2['holonomy']:.2f}¢ → {r2['holonomy_class']}")
    print(f"  All smooth: {all(r2['voice_leading_smooth'])}")
    print()

    print("12-bar blues:")
    print(f"  Holonomy: {blues_analysis['holonomy']:.2f}¢ → {blues_analysis['holonomy_class']}")
    print(f"  Surprises: {len(blues_analysis['surprises'])} transitions with high tension")
    print()

    print("=" * 72)
    print("⚡ Constraint theory IS music theory. The math doesn't lie.")
    print("=" * 72)


if __name__ == '__main__':
    demo()
