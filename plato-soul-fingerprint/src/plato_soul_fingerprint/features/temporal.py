"""Temporal features from git log."""

import subprocess
import os
import re
from datetime import datetime
from collections import defaultdict
import math


def _git_log_porcelain(repo_path: str):
    """Yield (timestamp, added, deleted) for each commit."""
    env = os.environ.copy()
    env["GIT_DIR"] = os.path.join(repo_path, ".git")
    env["GIT_WORK_TREE"] = repo_path

    result = subprocess.run(
        ["git", "log", "--format=%H %at"],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_path,
    )
    if result.returncode != 0:
        return

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
            commits.append((parts[0], int(parts[1])))

    for commit_hash, ts in commits:
        stat_res = subprocess.run(
            ["git", "show", "--format=", "--stat", commit_hash],
            capture_output=True,
            text=True,
            env=env,
            cwd=repo_path,
        )
        added, deleted = 0, 0
        if stat_res.returncode == 0:
            for line in stat_res.stdout.splitlines():
                m = re.search(r"(\d+) insertion", line)
                if m:
                    added = int(m.group(1))
                m = re.search(r"(\d+) deletion", line)
                if m:
                    deleted = int(m.group(1))
        yield ts, added, deleted


def extract_temporal_features(repo_path: str) -> dict:
    features = {}
    timestamps = []
    adds = []
    dels = []

    for ts, a, d in _git_log_porcelain(repo_path):
        timestamps.append(ts)
        adds.append(a)
        dels.append(d)

    if not timestamps:
        features["commit_frequency"] = 0.0
        features["commit_burstiness"] = 0.0
        for h in range(24):
            features[f"commit_hour_{h:02d}"] = 0.0
        features["commit_size_mean"] = 0.0
        features["commit_size_std"] = 0.0
        features["commit_size_max"] = 0.0
        features["batch_vs_incremental"] = 0.0
        return features

    timestamps.sort()
    total_commits = len(timestamps)
    span_weeks = max((timestamps[-1] - timestamps[0]) / (7 * 24 * 3600), 1.0)
    features["commit_frequency"] = total_commits / span_weeks

    intervals = []
    for i in range(1, len(timestamps)):
        intervals.append(timestamps[i] - timestamps[i - 1])
    if intervals:
        mean_interval = sum(intervals) / len(intervals)
        var_interval = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        features["commit_burstiness"] = math.sqrt(var_interval) / max(mean_interval, 1.0)
    else:
        features["commit_burstiness"] = 0.0

    hour_counts = defaultdict(int)
    for ts in timestamps:
        dt = datetime.utcfromtimestamp(ts)
        hour_counts[dt.hour] += 1
    for h in range(24):
        features[f"commit_hour_{h:02d}"] = hour_counts.get(h, 0) / total_commits

    sizes = [a + d for a, d in zip(adds, dels)]
    features["commit_size_mean"] = sum(sizes) / len(sizes)
    features["commit_size_max"] = max(sizes) if sizes else 0.0
    if len(sizes) > 1:
        mean_s = features["commit_size_mean"]
        var_s = sum((s - mean_s) ** 2 for s in sizes) / len(sizes)
        features["commit_size_std"] = math.sqrt(var_s)
    else:
        features["commit_size_std"] = 0.0

    large = sum(1 for s in sizes if s > 100)
    small = sum(1 for s in sizes if s <= 100)
    features["batch_vs_incremental"] = large / max(small, 1.0)

    return features
