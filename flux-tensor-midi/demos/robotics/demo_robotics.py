#!/usr/bin/env python3
"""
6-DOF Robot Arm as a Band -- Pick-and-Place Coordination Demo

Each joint is a RoomMusician with its own T-0 clock and Eisenstein
rhythm snapping. Joints coordinate via side-channels (nods) and all
arrive at the target within 1 beat of each other -- a chord, not a scale.

Usage:
    python3 demo_robotics.py
"""

import sys
import math
import json
import os

from flux_tensor_midi import RoomMusician, FluxVector, EisensteinSnap
from flux_tensor_midi.core.snap import RhythmicRole
from flux_tensor_midi.ensemble.band import Band
from flux_tensor_midi.ensemble.score import Score
from flux_tensor_midi.harmony.jaccard import jaccard_index
from flux_tensor_midi.harmony.chord import HarmonyState

# -- Robot Arm Model -----------------------------------------------------------

DH_PARAMS = [
    {"a": 0.0,     "alpha": 0.0,          "d": 0.3,  "theta_offset": 0.0},
    {"a": 0.0,     "alpha": -math.pi/2,   "d": 0.0,  "theta_offset": 0.0},
    {"a": 0.4,     "alpha": 0.0,          "d": 0.0,  "theta_offset": 0.0},
    {"a": 0.0,     "alpha": math.pi/2,    "d": 0.35, "theta_offset": 0.0},
    {"a": 0.0,     "alpha": -math.pi/2,   "d": 0.0,  "theta_offset": 0.0},
    {"a": 0.0,     "alpha": 0.0,          "d": 0.15, "theta_offset": 0.0},
]


class JointMusician:
    """A robot joint as a RoomMusician with kinematics awareness."""

    def __init__(self, name: str, joint_index: int, role: RhythmicRole, tempo_bpm: float):
        self.index = joint_index
        self.musician = RoomMusician(name, role=role)
        self.musician.clock.set_bpm(tempo_bpm)
        self.current_angle = 0.0
        self.target_angle = 0.0
        self._start_angle = 0.0
        self._motion_beats = 0
        self._current_beat = 0

    @property
    def name(self) -> str:
        return self.musician.name

    def set_target(self, angle: float, motion_beats: int = 8) -> None:
        """Set a new target angle and plan motion duration."""
        self._start_angle = self.current_angle
        self.target_angle = angle
        self._motion_beats = motion_beats
        self._current_beat = 0

    def step(self) -> float:
        """Advance one beat, return the new angle."""
        self._current_beat += 1
        if self._current_beat >= self._motion_beats:
            self.current_angle = self.target_angle
        else:
            t = self._current_beat / self._motion_beats
            eased = t * t * (3.0 - 2.0 * t)
            self.current_angle = self._start_angle + (self.target_angle - self._start_angle) * eased

        vec = self._make_vector(self.current_angle, self.target_angle)
        self.musician.state = vec
        self.musician.emit(vec)
        return self.current_angle

    def _make_vector(self, angle: float, target: float) -> FluxVector:
        max_angle = math.pi
        progress = min(1.0, self._current_beat / max(self._motion_beats, 1))
        if self._current_beat < 1:
            prev_angle = self._start_angle
        else:
            t_prev = (self._current_beat - 1) / max(self._motion_beats, 1)
            t_prev_clamped = max(0, t_prev)
            e_prev = t_prev_clamped * t_prev_clamped * (3.0 - 2.0 * t_prev_clamped)
            prev_angle = self._start_angle + (self.target_angle - self._start_angle) * e_prev

        vel = (self.current_angle - prev_angle) / 0.5
        error = abs(self.current_angle - self.target_angle)

        values = [
            self.current_angle / max_angle,              # ch0: normalized angle
            min(1.0, error / max_angle),                  # ch1: normalized error
            min(1.0, max(0.0, (vel / 2.0) + 0.5)),       # ch2: normalized velocity
            progress,                                      # ch3: motion progress
            1.0 if self.index == 2 and progress >= 1.0 else 0.0,  # ch4: elbow ready
            0.0, 0.0, 0.0, 0.0,
        ]
        return FluxVector(values,
                          salience=[0.8, 0.7, 0.5, 0.6, 1.0, 0.0, 0.0, 0.0, 0.0],
                          tolerance=[0.05, 0.1, 0.1, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0])

    @property
    def motion_done(self) -> bool:
        return self._current_beat >= self._motion_beats

    @property
    def progress(self) -> float:
        return min(1.0, self._current_beat / max(self._motion_beats, 1))


# -- Forward Kinematics --------------------------------------------------------

def forward_kinematics(joint_angles: list[float]) -> tuple[list[float], list[float]]:
    """Compute end-effector position from joint angles (simple planar arm)."""
    l1, l2, l3, l4, l5 = 0.3, 0.4, 0.35, 0.15, 0.05
    theta = joint_angles

    x = l2 * math.cos(theta[0]) * math.cos(theta[1]) \
        + l3 * math.cos(theta[0]) * math.cos(theta[1] + theta[2]) \
        + l4 * math.cos(theta[0]) * math.cos(theta[1] + theta[2] + theta[3]) \
        + l5 * math.cos(theta[0]) * math.cos(theta[1] + theta[2] + theta[3] + theta[4])
    y = l2 * math.sin(theta[0]) * math.cos(theta[1]) \
        + l3 * math.sin(theta[0]) * math.cos(theta[1] + theta[2]) \
        + l4 * math.sin(theta[0]) * math.cos(theta[1] + theta[2] + theta[3]) \
        + l5 * math.sin(theta[0]) * math.cos(theta[1] + theta[2] + theta[3] + theta[4])
    z = l1 \
        + l2 * math.sin(theta[1]) \
        + l3 * math.sin(theta[1] + theta[2]) \
        + l4 * math.sin(theta[1] + theta[2] + theta[3]) \
        + l5 * math.sin(theta[1] + theta[2] + theta[3] + theta[4])

    orientation = [theta[3], theta[4], theta[5]]
    return [x, y, z], orientation


# -- Pick-and-Place Simulation -------------------------------------------------

def simulate_pick_and_place() -> dict:
    """Run a full pick-and-place cycle with musical coordination."""
    print("=" * 72)
    print("  6-DOF ROBOT ARM AS A BAND -- Pick-and-Place Demo")
    print("=" * 72)

    # Create the band: each joint is a musician with a different role/tempo
    j1 = JointMusician("base",          0, RhythmicRole.HALFTIME,   30)
    j2 = JointMusician("shoulder",      1, RhythmicRole.TRIPLET,    40)
    j3 = JointMusician("elbow",         2, RhythmicRole.ROOT,       60)
    j4 = JointMusician("wrist_pitch",   3, RhythmicRole.COMPOUND,   80)
    j5 = JointMusician("wrist_yaw",     4, RhythmicRole.DOUBLETIME, 80)
    j6 = JointMusician("gripper",       5, RhythmicRole.WALTZ,     120)

    arm = Band("robot_arm", bpm=60)
    arm.add_musician(j1.musician)
    arm.add_musician(j2.musician)
    arm.add_musician(j3.musician)
    arm.add_musician(j4.musician)
    arm.add_musician(j5.musician)
    arm.add_musician(j6.musician)
    arm.everyone_listens_to_everyone()

    score = Score("robot_arm_pick_and_place")
    joints = [j1, j2, j3, j4, j5, j6]

    print(f"\nBand: {arm}")
    print(f"Members: {[m.name for m in arm.members.values()]}")
    print(f"Roles: {arm.get_roles()}\n")

    # Motion plan: 9 phases of pick-and-place
    phases = [
        ("HOME",            [0.0,   0.0,   0.0,   0.0,   0.0,   0.2],   8),
        ("APPROACH_PICK",   [0.3,   0.5,  -1.0,   0.0,   0.2,   0.2],  12),
        ("LOWER_TO_PICK",   [0.3,   0.8,  -0.5,   0.3,   0.2,   0.2],   8),
        ("GRASP",           [0.3,   0.8,  -0.5,   0.3,   0.2,   0.0],   4),
        ("LIFT",            [0.3,   0.5,  -1.0,   0.0,   0.2,   0.0],   8),
        ("MOVE_TO_PLACE",  [-0.3,   0.5,  -1.0,   0.0,  -0.2,   0.0],  16),
        ("LOWER_TO_PLACE", [-0.3,   0.8,  -0.5,   0.3,  -0.2,   0.0],   8),
        ("RELEASE",        [-0.3,   0.8,  -0.5,   0.3,  -0.2,   0.2],   4),
        ("RETURN",          [0.0,   0.0,   0.0,   0.0,   0.0,   0.2],  12),
    ]

    timeline = []
    total_beats = 0
    harmony_at_phase_end = []

    print(f"{'Beat':>4} | {'Phase':<18} | End-Effector Position")
    print("-" * 72)

    for phase_name, target_angles, beats in phases:
        for joint, target in zip(joints, target_angles):
            joint.set_target(target, motion_beats=beats)

        for beat in range(beats):
            angs = [joint.step() for joint in joints]
            pos, orient = forward_kinematics(angs)

            state_vecs = []
            for jnt in joints:
                ts = jnt.musician.event_history[-1][0]
                vec = jnt.musician.event_history[-1][1]
                score.record_event(jnt.name, ts, vec)
                state_vecs.append((jnt.name, ts, vec))

            # Side-channel: elbow nods to gripper when in position
            if phase_name in ("LIFT", "MOVE_TO_PLACE"):
                if j3.motion_done and not j6.motion_done:
                    j3.musician.send_nod(j6.musician, intensity=0.8)
                    score.record_side_channel("elbow", "nod", total_beats + beat)

            entry = {
                "beat": total_beats + beat,
                "phase": phase_name,
                "angles": [round(a, 4) for a in angs],
                "end_effector": [round(p, 4) for p in pos],
                "orientation": [round(o, 4) for o in orient],
                "joint_progress": [round(j.progress, 3) for j in joints],
                "t0_ticks": [j.musician.clock.ticks for j in joints],
                "t0_timestamps_ms": [
                    round(j.musician.event_history[-1][0], 2)
                    if j.musician.event_history else 0 for j in joints
                ],
            }
            timeline.append(entry)

            if beat == 0 or beat == beats - 1 or beat == beats // 2:
                pos_str = f"({pos[0]:.3f}, {pos[1]:.3f}, {pos[2]:.3f})"
                print(f"{total_beats + beat:>4} | {phase_name:<18} | {pos_str}")

            total_beats += 1

        # End of phase: compute harmony
        latest_states = [j.musician.state for j in joints]
        h = HarmonyState(latest_states)
        harmony_at_phase_end.append({
            "phase": phase_name,
            "beat": total_beats,
            "consonance": round(h.consonance(), 4),
            "quality": h.quality(),
            "correlation": round(h.correlation(), 4),
        })
        print(f"  ... {phase_name} done -- harmony: {h.quality()} "
              f"(consonance={h.consonance():.3f}, corr={h.correlation():.3f})")

    # -- Analysis: Arrival Times -----------------------------------------------
    print("\n" + "=" * 72)
    print("  HARMONY ANALYSIS -- Joint Timing Overlap")
    print("=" * 72)

    arrival_times = {}
    for joint in joints:
        jidx = joints.index(joint)
        arrival = None
        for i in range(len(timeline) - 1, -1, -1):
            e = timeline[i]
            if abs(e["angles"][jidx] - joint.target_angle) < 0.001:
                arrival = e["beat"]
                break
        arrival_times[joint.name] = arrival

    print("\nArrival times (beat number when joint reached target):")
    for name, beat in arrival_times.items():
        print(f"  {name:<16}: beat {beat}")

    if all(v is not None for v in arrival_times.values()):
        arrivals = list(arrival_times.values())
        spread = max(arrivals) - min(arrivals)
        print(f"\n  Spread (max - min): {spread} beats")
        if spread <= 1:
            print("  ++ ALL JOINTS ARRIVED WITHIN 1 BEAT -- Perfect chord!")
        else:
            print(f"  Joints arrived within {spread} beats")

    # -- Jaccard overlap of joint timing profiles ------------------------------
    print("\nJoint timing overlap (Jaccard index of angle profiles):")
    from flux_tensor_midi.core.flux import FluxVector as FV
    for i in range(len(joints)):
        for j in range(i + 1, len(joints)):
            angles_i = [e["angles"][i] for e in timeline]
            angles_j = [e["angles"][j] for e in timeline]
            m = len(timeline)
            if m > 9:
                step = m // 9
                vals_i = [angles_i[min(k * step, m - 1)] for k in range(9)]
                vals_j = [angles_j[min(k * step, m - 1)] for k in range(9)]
            else:
                vals_i = angles_i + [0.0] * (9 - m)
                vals_j = angles_j + [0.0] * (9 - m)
            fvi = FV(vals_i)
            fvj = FV(vals_j)
            jacc = jaccard_index(fvi, fvj, threshold=0.05)
            print(f"  {joints[i].name:<12} <-> {joints[j].name:<12}: Jaccard={jacc:.4f}")

    # -- Phase Harmony Summary -------------------------------------------------
    print("\n" + "=" * 72)
    print("  PHASE HARMONY SUMMARY")
    print("=" * 72)
    for h in harmony_at_phase_end:
        print(f"  {h['phase']:<20} | quality={h['quality']:<12} | "
              f"consonance={h['consonance']} | correlation={h['correlation']}")

    # -- Performance Summary ---------------------------------------------------
    print("\n" + "=" * 72)
    print("  PERFORMANCE SUMMARY")
    print("=" * 72)
    print(f"  Total beats:             {total_beats}")
    print(f"  Total events recorded:   {score.total_events()}")
    print(f"  Score duration:          {score.duration_ms():.1f} ms")
    print(f"  Phases:                  {len(phases)}")
    print(f"  Joints in band:          {arm.member_count}")
    print(f"  Mean coherence:          {arm.mean_coherence():.4f}")
    final_h = arm.harmony()
    print(f"  Final harmony:           {final_h.quality()} "
          f"(consonance={final_h.consonance():.3f})")

    last_entry = timeline[-1] if timeline else {}
    print(f"  Final end-effector pos:  {last_entry.get('end_effector', 'N/A')}")

    return {
        "timeline": timeline,
        "harmony_at_phase_end": harmony_at_phase_end,
        "arrival_times": arrival_times,
        "score_summary": score.summary(),
        "band_info": {
            "name": arm.name,
            "members": list(arm.members.keys()),
            "roles": {name: r.value for name, r in arm.get_roles().items()},
            "bpm": arm.bpm,
        },
    }


# -- Main ---------------------------------------------------------------------

if __name__ == "__main__":
    results = simulate_pick_and_place()

    out_dir = os.path.dirname(os.path.abspath(__file__))

    # Save timeline as JSON
    tl_path = os.path.join(out_dir, "pick_and_place_timeline.json")
    summary = {
        "timeline": [{
            "beat": e["beat"],
            "phase": e["phase"],
            "angles": e["angles"],
            "end_effector": e["end_effector"],
            "joint_progress": e["joint_progress"],
        } for e in results["timeline"]],
        "harmony_at_phase_end": results["harmony_at_phase_end"],
        "arrival_times": results["arrival_times"],
        "score_summary": results["score_summary"],
        "band_info": results["band_info"],
    }
    with open(tl_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n++ Timeline saved to: {tl_path}")

    # Export as VMS score
    vms_path = os.path.join(out_dir, "pick_and_place.vms")
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from vms import VideoScore, SceneEvent, SceneType, Channel, EisensteinLattice, save_vms

    vms_score = VideoScore(
        name="robot_arm_pick_and_place",
        tempo_bpm=60,
        lattice=EisensteinLattice(24),
    )
    for e in results["timeline"]:
        vms_score.add_scene(SceneEvent(
            beat=e["beat"] / 2.0,
            scene_type=SceneType.USER_INTERACTION,
            duration_beats=0.5,
            velocity=max(1, min(127, int(abs(e["angles"][2]) * 40 + 20))),
            channel=Channel.VISUAL,
            meta={
                "joint": "elbow",
                "angle": round(e["angles"][2], 3),
                "phase": e["phase"],
                "end_effector": e["end_effector"],
            },
        ), snap=True)
    save_vms(vms_score, vms_path)
    print(f"++ VMS score saved to: {vms_path}")

    print("\n" + "=" * 72)
    print("  DEMO COMPLETE +")
    print("=" * 72)
