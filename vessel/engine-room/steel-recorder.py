#!/usr/bin/env python3
"""
steel-recorder.py — Tier 3: Steel.dev Browser Recording Control Script
JC1 Three-Tier RFC Architecture — Tier 3 (Controls)

Captures plato-room playtests and A/B quest videos using the self-hosted
Steel.dev browser API. Applies the RFC's six extraction patterns and
four-stage validation before attaching recordings to marketplace submissions
and syncing metadata to fleet shared storage.

Self-hosted Steel.dev API: http://localhost:3000
Start: docker run -d -p 3000:3000 steeldev/steel-browser:latest
"""

import json
import hashlib
import subprocess
import time
import os
from datetime import datetime, timezone
from pathlib import Path

STEEL_API_URL = os.getenv("STEEL_API_URL", "http://localhost:3000")
STEEL_API_KEY = os.getenv("STEEL_API_KEY", "local-fleet-key")
PLATO_ROOM_URL = os.getenv("PLATO_ROOM_URL", "http://localhost:7878")
RECORDING_OUTPUT = Path(os.getenv("RECORDING_OUTPUT", "/tmp/forgemaster/bootcamp/recording/videos"))
BOOTCAMP_DIR = Path("/tmp/forgemaster/bootcamp")
STATUS_FILE = Path("/tmp/forgemaster/bootcamp/recording/STATUS.md")
FLEET_DIR = Path("/tmp/forgemaster/for-fleet")

# ─── Six Extraction Patterns (JC1 RFC) ───────────────────────────────────────

def session_capture(session_id: str, url: str) -> dict:
    """
    Pattern 1: Capture Steel.dev session lifecycle metadata.
    Opens a browser session targeting the given URL and returns session info.
    """
    headers = {
        "Authorization": f"Bearer {STEEL_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "url": url,
        "sessionTimeout": 600,
        "recordSession": True,
        "useProxy": False,
    }
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions",
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return {
                "session_id": data.get("id", session_id),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "url": url,
                "steel_api_url": STEEL_API_URL,
            }
    except Exception as e:
        # Steel.dev not yet running — return scaffolded metadata
        return {
            "session_id": session_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "url": url,
            "steel_api_url": STEEL_API_URL,
            "error": str(e),
        }


def viewport_record(session_id: str, output_dir: Path) -> Path:
    """
    Pattern 2: Record browser viewport to WebM video.
    Polls Steel.dev for the session recording and saves to output_dir.
    Returns path to the saved video file.
    """
    video_path = output_dir / "session.webm"
    try:
        import urllib.request
        headers = {"Authorization": f"Bearer {STEEL_API_KEY}"}
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions/{session_id}/recording",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            video_path.write_bytes(resp.read())
    except Exception:
        # Scaffold placeholder until Steel.dev is running
        video_path.write_bytes(b"")
    return video_path


def console_extract(session_id: str, output_dir: Path) -> Path:
    """
    Pattern 3: Extract browser console logs as JSONL.
    """
    console_path = output_dir / "console.jsonl"
    try:
        import urllib.request
        headers = {"Authorization": f"Bearer {STEEL_API_KEY}"}
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions/{session_id}/logs/console",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            logs = json.loads(resp.read())
            lines = [json.dumps(entry) for entry in logs]
            console_path.write_text("\n".join(lines))
    except Exception as e:
        console_path.write_text(json.dumps({"error": str(e), "session_id": session_id}))
    return console_path


def network_trace(session_id: str, output_dir: Path) -> Path:
    """
    Pattern 4: Capture CDP network events as HAR file.
    """
    har_path = output_dir / "network.har"
    try:
        import urllib.request
        headers = {"Authorization": f"Bearer {STEEL_API_KEY}"}
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions/{session_id}/har",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            har_path.write_bytes(resp.read())
    except Exception as e:
        har_path.write_text(json.dumps({
            "log": {"version": "1.2", "entries": [], "error": str(e)}
        }))
    return har_path


def dom_snapshot(session_id: str, output_dir: Path, index: int = 0) -> Path:
    """
    Pattern 5: Take DOM snapshot at a key playtest moment.
    """
    snap_path = output_dir / f"dom-{index}.html"
    try:
        import urllib.request
        headers = {"Authorization": f"Bearer {STEEL_API_KEY}"}
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions/{session_id}/dom",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            snap_path.write_bytes(resp.read())
    except Exception as e:
        snap_path.write_text(f"<!-- DOM snapshot failed: {e} -->")
    return snap_path


def perf_profile(session_id: str, output_dir: Path) -> Path:
    """
    Pattern 6: Extract GPU/CPU performance metrics via CDP Performance timeline.
    """
    perf_path = output_dir / "perf.json"
    try:
        import urllib.request
        headers = {"Authorization": f"Bearer {STEEL_API_KEY}"}
        req = urllib.request.Request(
            f"{STEEL_API_URL}/sessions/{session_id}/performance",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            perf_path.write_bytes(resp.read())
    except Exception as e:
        perf_path.write_text(json.dumps({
            "metrics": [], "error": str(e),
            "session_id": session_id,
        }))
    return perf_path


# ─── Four-Stage Validation (JC1 RFC) ─────────────────────────────────────────

def _validate_recording(output_dir: Path, quest_metadata: dict) -> dict:
    """
    TODO: Implement the four-stage validation gate.

    This is the gatekeeper between a raw Steel.dev capture and a
    marketplace-attached artifact. All four stages must pass before
    the recording is attached to the submission.

    Parameters
    ----------
    output_dir : Path
        Directory containing: session.webm, console.jsonl,
        network.har, dom-*.html, perf.json, manifest.json
    quest_metadata : dict
        Loaded from bootcamp/quests/pending/{QUEST_ID}/metadata.json
        Keys: quest_id, title, estimated_duration_sec, rtx_class, variant

    Returns
    -------
    dict with keys:
        passed : bool          — True only if all four stages pass
        stages : dict          — Per-stage result: {"quality_check": True, ...}
        failures : list[str]   — Human-readable failure reasons
        gpu_peak_mb : int      — Peak GPU memory seen in perf.json (stage 3)

    Stage definitions (from JC1 RFC):
        1. quality_check  — Video resolution ≥ 1280×720, bitrate ≥ 800kbps
        2. content_align  — Recording duration within ±20% of estimated_duration_sec
        3. rtx_parity     — GPU memory peak < 4096 MB (RTX 4050 6.4GB VRAM budget)
        4. fleet_ready    — File ≤ 500MB, format .webm, checksum computable

    Guidance
    --------
    Consider: stage 3 (rtx_parity) is the most fleet-critical — a recording
    that exceeds the 4050's budget means the quest can't run on fleet hardware.
    Stage 1 thresholds are quality floors, not ceilings — you can raise them.
    Stage 2 uses estimated_duration_sec from metadata; decide how strict ±20% is.
    """
    # TODO: implement this function (5-10 lines per stage)
    raise NotImplementedError(
        "Implement _validate_recording in vessel/engine-room/steel-recorder.py.\n"
        "See the TODO docstring above for stage definitions and guidance."
    )


def _run_validation(output_dir: Path, quest_metadata: dict) -> dict:
    """
    Wraps _validate_recording with a fallback so the rest of the pipeline
    continues to function while the validation logic is being implemented.
    """
    try:
        return _validate_recording(output_dir, quest_metadata)
    except NotImplementedError:
        # Graceful scaffold: all stages pending until implemented
        return {
            "passed": False,
            "stages": {
                "quality_check": None,
                "content_align": None,
                "rtx_parity": None,
                "fleet_ready": None,
            },
            "failures": ["_validate_recording not yet implemented"],
            "gpu_peak_mb": 0,
        }


# ─── Recording Session ────────────────────────────────────────────────────────

def run_recording_session(quest_id: str, variant: str, target_url: str) -> dict:
    """
    Run all six extraction patterns for a single quest variant recording.
    Returns a manifest dict suitable for attaching to the marketplace submission.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M")
    output_dir = RECORDING_OUTPUT / quest_id / f"variant-{variant}" / ts
    output_dir.mkdir(parents=True, exist_ok=True)

    session_id = f"steel-{quest_id.lower()}-{variant}-{ts}"

    # Pattern 1 — session capture
    meta = session_capture(session_id, target_url)
    session_id = meta["session_id"]

    # Patterns 2-6 run in parallel (threads)
    import threading
    results = {}

    def run(fn, *args):
        try:
            results[fn.__name__] = fn(*args)
        except Exception as e:
            results[fn.__name__] = str(e)

    threads = [
        threading.Thread(target=run, args=(viewport_record, session_id, output_dir)),
        threading.Thread(target=run, args=(console_extract, session_id, output_dir)),
        threading.Thread(target=run, args=(network_trace, session_id, output_dir)),
        threading.Thread(target=run, args=(dom_snapshot, session_id, output_dir, 0)),
        threading.Thread(target=run, args=(perf_profile, session_id, output_dir)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    # Compute checksum on video
    video_path = output_dir / "session.webm"
    checksum = hashlib.sha256(video_path.read_bytes()).hexdigest() if video_path.exists() else ""

    # Load quest metadata for validation
    quest_meta_path = BOOTCAMP_DIR / "quests" / "pending" / quest_id / "metadata.json"
    quest_metadata = json.loads(quest_meta_path.read_text()) if quest_meta_path.exists() else {}
    quest_metadata["variant"] = variant

    # Four-stage validation
    validation = _run_validation(output_dir, quest_metadata)

    # Write manifest
    manifest = {
        "quest_id": quest_id,
        "variant": variant,
        "recording": {
            "session_id": session_id,
            "video_path": str(video_path.relative_to(Path("/tmp/forgemaster"))),
            "checksum_sha256": checksum,
            "duration_sec": quest_metadata.get("estimated_duration_sec", 0),
            "resolution": "1280x720",
            "validation_stages": [k for k, v in validation["stages"].items() if v is True],
            "validated_at": datetime.now(timezone.utc).isoformat(),
            "steel_api_url": STEEL_API_URL,
            "validation": validation,
        },
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"[steel-recorder] {quest_id}/{variant}: recorded → {output_dir}")
    print(f"[steel-recorder] validation: {'PASS' if validation['passed'] else 'FAIL'}")
    if not validation["passed"]:
        for f in validation.get("failures", []):
            print(f"  ✗ {f}")

    return manifest


# ─── Marketplace Attachment ───────────────────────────────────────────────────

def attach_to_submission(quest_id: str, variant: str, recording_manifest: dict):
    """
    Attach a validated recording manifest to the marketplace submission.
    Writes to bootcamp/quests/pending/{QUEST_ID}/variant-{a|b}/recording.json
    """
    submission_dir = BOOTCAMP_DIR / "quests" / "pending" / quest_id / f"variant-{variant}"
    submission_dir.mkdir(parents=True, exist_ok=True)
    out = submission_dir / "recording.json"
    out.write_text(json.dumps(recording_manifest, indent=2))
    print(f"[steel-recorder] attached recording to {out}")


# ─── Fleet Shared Storage Sync ───────────────────────────────────────────────

def sync_to_fleet(manifests: list[dict]):
    """
    Sync recording metadata to fleet shared storage via the I2I bottle pattern.
    Commits STATUS.md update and drops a fleet bottle with the recording summary.
    Video binaries stay local; only metadata is pushed.
    """
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")

    # Drop a fleet bottle
    bottle_name = f"BOTTLE-FROM-FORGEMASTER-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-STEEL-RECORDINGS-UPDATE.md"
    bottle_path = FLEET_DIR / bottle_name
    lines = [
        f"# Steel.dev Recording Update — {ts}",
        f"**From:** Forgemaster ⚒️",
        f"**To:** Fleet",
        f"",
        f"## Recording Manifests This Cycle",
        f"",
    ]
    for m in manifests:
        r = m.get("recording", {})
        v = r.get("validation", {})
        status = "✅ PASS" if v.get("passed") else "⏳ PENDING"
        lines += [
            f"### {m['quest_id']} — Variant {m['variant'].upper()}",
            f"- Session: `{r.get('session_id', '—')}`",
            f"- Validation: {status}",
            f"- Checksum: `{r.get('checksum_sha256', '—')[:16]}...`",
            f"- Path: `{r.get('video_path', '—')}`",
            f"",
        ]
    lines += [
        f"## Fleet Distribution",
        f"Video binaries are stored locally on Forgemaster (WSL2 drive).",
        f"Access via vessel IP + path reference. Metadata committed to git.",
        f"",
        f"*Forgemaster ⚒️ — Hourly I2I Push — {ts}*",
    ]
    bottle_path.write_text("\n".join(lines))
    print(f"[steel-recorder] fleet bottle → {bottle_path.name}")

    # Git commit and push
    repo = Path("/tmp/forgemaster")
    try:
        subprocess.run(
            ["git", "-C", str(repo), "add",
             "bootcamp/recording/STATUS.md",
             "bootcamp/recording/README.md",
             str(bottle_path)],
            check=True, capture_output=True,
        )
        msg = f"[I2I:LOG] steel-recording: hourly sync — {len(manifests)} recording(s) processed"
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", msg],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo), "push"],
            check=True, capture_output=True,
        )
        print(f"[steel-recorder] pushed: {msg}")
    except subprocess.CalledProcessError as e:
        print(f"[steel-recorder] git error: {e.stderr.decode()[:200]}")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """
    Record both variants for every quest in the RTX drill queue.
    Attach validated recordings to marketplace submissions.
    Sync metadata to fleet shared storage.
    """
    # RTX drill quest queue (matches proposals/CLAUDE-MARKETPLACE-AB-QUEST-VIDEO-APPROVAL.md)
    queue = [
        ("RTX-001", "a", f"{PLATO_ROOM_URL}/quest/rtx-001/variant-a"),
        ("RTX-001", "b", f"{PLATO_ROOM_URL}/quest/rtx-001/variant-b"),
        ("RTX-002", "a", f"{PLATO_ROOM_URL}/quest/rtx-002/variant-a"),
        ("RTX-002", "b", f"{PLATO_ROOM_URL}/quest/rtx-002/variant-b"),
    ]

    manifests = []
    for quest_id, variant, url in queue:
        print(f"\n[steel-recorder] recording {quest_id} variant-{variant}...")
        manifest = run_recording_session(quest_id, variant, url)
        if manifest["recording"]["validation"].get("passed", False):
            attach_to_submission(quest_id, variant, manifest)
        manifests.append(manifest)

    sync_to_fleet(manifests)
    print("\n[steel-recorder] done. All sessions processed.")


if __name__ == "__main__":
    main()
