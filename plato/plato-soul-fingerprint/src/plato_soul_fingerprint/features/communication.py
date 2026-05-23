"""Communication features from commit messages."""

import subprocess
import os
import re


IMPERATIVE_VERBS = {
    "add", "fix", "remove", "update", "change", "refactor", "move", "rename",
    "merge", "split", "implement", "create", "delete", "handle", "support",
    "allow", "disable", "enable", "make", "set", "get", "use", "replace",
    "improve", "optimize", "simplify", "clean", "document", "test", "build",
    "install", "configure", "upgrade", "downgrade", "revert", "apply",
}


def _git_log_messages(repo_path: str):
    env = os.environ.copy()
    env["GIT_DIR"] = os.path.join(repo_path, ".git")
    env["GIT_WORK_TREE"] = repo_path
    result = subprocess.run(
        ["git", "log", "--format=%s"],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo_path,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def extract_communication_features(repo_path: str) -> dict:
    features = {}
    msgs = _git_log_messages(repo_path)
    total = len(msgs)

    if total == 0:
        features["msg_length_mean"] = 0.0
        features["msg_length_std"] = 0.0
        features["msg_length_max"] = 0.0
        features["conventional_commit_score"] = 0.0
        features["imperative_verb_frequency"] = 0.0
        features["emoji_frequency"] = 0.0
        features["reference_frequency"] = 0.0
        return features

    lengths = [len(m) for m in msgs]
    mean_len = sum(lengths) / total
    var_len = sum((l - mean_len) ** 2 for l in lengths) / total
    features["msg_length_mean"] = mean_len
    features["msg_length_std"] = var_len ** 0.5
    features["msg_length_max"] = max(lengths)

    conventional = 0
    imperative = 0
    emoji = 0
    reference = 0

    conventional_pattern = re.compile(
        r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:\s"
    )

    for msg in msgs:
        if conventional_pattern.match(msg):
            conventional += 1
        first_word = msg.split()[0].lower().rstrip(":")
        if first_word in IMPERATIVE_VERBS:
            imperative += 1
        if any(ord(c) > 0x1F300 for c in msg):
            emoji += 1
        if re.search(r"#\d+|issue|pull request|pr\s*#?\d+", msg, re.I):
            reference += 1

    features["conventional_commit_score"] = conventional / total
    features["imperative_verb_frequency"] = imperative / total
    features["emoji_frequency"] = emoji / total
    features["reference_frequency"] = reference / total

    return features
