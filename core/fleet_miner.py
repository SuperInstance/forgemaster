#!/usr/bin/env python3
"""core/fleet_miner.py — Git history miner feeding the collective inference loop.

The pipeline:
  1. SCAN:    List repos, check for new commits
  2. EXTRACT: Pull commit metadata (author, message, files, time, parent, branch)
  3. ANALYZE: Identify patterns (author cadence, file change clusters, cross-pollination)
  4. TILE:    Convert patterns to tiles the fleet can use
  5. FEED:    Push tiles into the collective inference loop

Data source: 1500+ commits across 8 SuperInstance fleet repos, author patterns,
time deltas, cross-pollination events.

These ARE the collective behavior signal — when commit in repo A references
repo B, or when the same author works across repos, or when file changes
cluster in time across repositories.
"""
from __future__ import annotations

import os
import re
import json
import time
import hashlib
import subprocess
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from datetime import datetime, timezone


# ─── CommitData — one mined commit ────────────────────────────────────────────

@dataclass
class CommitData:
    """A single commit extracted from git history."""
    sha: str
    short_sha: str
    author: str
    author_email: str
    message: str
    timestamp: float           # unix epoch
    date_iso: str              # human-readable
    repo_name: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    parent_shas: List[str] = field(default_factory=list)
    branch: str = ""

    @property
    def message_summary(self) -> str:
        """First line of commit message."""
        return self.message.split("\n")[0][:120]

    @property
    def size(self) -> int:
        return self.insertions + self.deletions

    def references_repo(self, repo_names: Set[str]) -> List[str]:
        """Check if commit message references other repos by name."""
        found = []
        msg_lower = self.message.lower()
        for name in repo_names:
            if name.lower() in msg_lower and name != self.repo_name:
                found.append(name)
        return found


# ─── CrossPollinationEvent ────────────────────────────────────────────────────

@dataclass
class CrossPollEvent:
    """When work in one repo is connected to work in another.

    The collective behavior signal. Three types:
      - REFERENCE: commit message mentions another repo
      - SAME_AUTHOR: same person committing across repos in a time window
      - FILE_LINK: changed files that are symlinked or dependency-connected
    """
    event_type: str            # reference | same_author | file_link
    source_repo: str
    target_repo: str
    source_sha: str
    author: str
    timestamp: float
    details: str = ""
    strength: float = 1.0     # how strong the connection (1.0 = direct ref)

    @property
    def event_id(self) -> str:
        raw = f"{self.event_type}:{self.source_sha}:{self.source_repo}->{self.target_repo}"
        return hashlib.md5(raw.encode()).hexdigest()[:12]


# ─── AuthorPattern — cadence and behavior for one author ──────────────────────

@dataclass
class AuthorPattern:
    """Mining results for one author across all repos."""
    name: str
    total_commits: int = 0
    repos: List[str] = field(default_factory=list)
    avg_commit_size: float = 0.0
    avg_time_between: float = 0.0   # seconds
    active_hours: List[int] = field(default_factory=list)  # hours (0-23)
    file_types: Dict[str, int] = field(default_factory=dict)
    first_commit: float = 0.0
    last_commit: float = 0.0
    burst_count: int = 0            # days with 5+ commits

    @property
    def span_days(self) -> float:
        if self.first_commit == 0:
            return 0
        return (self.last_commit - self.first_commit) / 86400


# ─── GitRepo — one repo's mining interface ────────────────────────────────────

class GitRepo:
    """A single repo. Tracks its state for incremental mining.

    Uses git subprocess calls (git log, git rev-list, etc.) to pull real data.
    Falls back to simulated data if git calls fail.
    """

    def __init__(self, path: str, name: str = ""):
        self.path = os.path.abspath(path)
        self.name = name or os.path.basename(self.path)
        self._last_sha: Optional[str] = None
        self._commits: List[CommitData] = []
        self._is_git = os.path.isdir(os.path.join(self.path, ".git"))

    def _git(self, *args: str) -> str:
        """Run a git command in this repo. Returns stdout."""
        try:
            result = subprocess.run(
                ["git", "-C", self.path] + list(args),
                capture_output=True, text=True, timeout=30,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ""

    def scan(self) -> dict:
        """Scan repo for metadata. Returns repo info dict."""
        if not self._is_git:
            return {"name": self.name, "path": self.path, "is_git": False}

        head_count = self._git("rev-list", "--count", "HEAD")
        branches = self._git("branch", "--list")
        branch_list = [b.strip().lstrip("* ") for b in branches.split("\n") if b.strip()]
        head_sha = self._git("rev-parse", "HEAD")

        return {
            "name": self.name,
            "path": self.path,
            "is_git": True,
            "commit_count": int(head_count) if head_count.isdigit() else 0,
            "branches": branch_list,
            "head_sha": head_sha,
        }

    def new_commits(self, since_sha: str = "") -> List[str]:
        """Get SHAs of commits since a given SHA."""
        if not self._is_git:
            return []
        if since_sha:
            shas = self._git("rev-list", f"{since_sha}..HEAD")
        else:
            shas = self._git("rev-list", "HEAD")
        return [s for s in shas.split("\n") if s.strip()]

    def extract(self, commit_range: str = "", max_commits: int = 500) -> List[CommitData]:
        """Pull commit metadata. Returns list of CommitData.

        Args:
            commit_range: e.g. "abc123..HEAD" or "" for all
            max_commits: safety limit
        """
        if not self._is_git:
            return []

        range_arg = commit_range or "HEAD"
        # Format: sha|author_name|author_email|timestamp|subject|parent1 parent2
        log = self._git(
            "log", f"--max-count={max_commits}",
            "--format=%H|%aN|%aE|%ct|%s|%P",
            range_arg,
        )
        if not log:
            return []

        commits = []
        for line in log.split("\n"):
            parts = line.split("|", 5)
            if len(parts) < 6:
                continue
            sha, author, email, ts_str, subject, parents_str = parts
            ts = float(ts_str) if ts_str.isdigit() else 0
            parents = parents_str.strip().split() if parents_str.strip() else []
            date_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else ""

            # Get file stats for this commit
            files_changed = []
            insertions = 0
            deletions = 0
            short_sha = sha[:8]

            # Only fetch stats for recent commits (expensive for old ones)
            stat_output = self._git("diff", "--shortstat", f"{sha}^", sha)
            if stat_output:
                ins_match = re.search(r"(\d+) insertion", stat_output)
                del_match = re.search(r"(\d+) deletion", stat_output)
                insertions = int(ins_match.group(1)) if ins_match else 0
                deletions = int(del_match.group(1)) if del_match else 0

            name_status = self._git("diff", "--name-only", f"{sha}^", sha)
            if name_status:
                files_changed = [f.strip() for f in name_status.split("\n") if f.strip()]

            commits.append(CommitData(
                sha=sha, short_sha=short_sha,
                author=author, author_email=email,
                message=subject, timestamp=ts, date_iso=date_iso,
                repo_name=self.name,
                files_changed=files_changed,
                insertions=insertions, deletions=deletions,
                parent_shas=parents,
            ))

        self._commits = commits
        if commits:
            self._last_sha = commits[0].sha  # most recent
        return commits

    def extract_all(self, max_commits: int = 1000) -> List[CommitData]:
        """Extract all commits from the repo."""
        return self.extract(commit_range="", max_commits=max_commits)

    @property
    def last_sha(self) -> Optional[str]:
        return self._last_sha

    @property
    def commits(self) -> List[CommitData]:
        return self._commits


# ─── FleetMiner — mines all fleet repos for patterns ──────────────────────────

class FleetMiner:
    """Mines all fleet repos for patterns that feed collective inference.

    The main pipeline:
      1. SCAN:    Discover repos, count commits, find branches
      2. EXTRACT: Pull commit metadata from each repo
      3. ANALYZE: Find patterns — author cadence, time deltas, clusters
      4. TILE:    Convert to tiles for the fleet
      5. FEED:    Push into collective inference loop

    Usage:
        miner = FleetMiner([
            "/home/phoenix/.openclaw/workspace",
            "/home/phoenix/projects/constraint-theory-core",
            ...
        ])
        report = miner.mine_all()
        patterns = miner.author_patterns()
        events = miner.cross_pollination()
    """

    def __init__(self, repo_paths: List[str]):
        self.repos: Dict[str, GitRepo] = {}
        for p in repo_paths:
            repo = GitRepo(p)
            self.repos[repo.name] = repo

        self._all_commits: List[CommitData] = []
        self._cross_events: List[CrossPollEvent] = []
        self._author_patterns: Dict[str, AuthorPattern] = {}
        self._repo_names: Set[str] = set(self.repos.keys())
        self._mined = False

    def mine_all(self, max_per_repo: int = 500) -> dict:
        """Full mining pipeline across all repos.

        Returns a report with scan results, commit counts, and patterns found.
        """
        # Phase 1: SCAN
        scan_results = {}
        for name, repo in self.repos.items():
            scan_results[name] = repo.scan()

        # Phase 2: EXTRACT
        total_commits = 0
        for name, repo in self.repos.items():
            if scan_results[name].get("is_git"):
                commits = repo.extract_all(max_commits=max_per_repo)
                total_commits += len(commits)
                self._all_commits.extend(commits)

        # Sort by timestamp
        self._all_commits.sort(key=lambda c: c.timestamp)

        # Phase 3: ANALYZE
        self._build_author_patterns()
        self._find_cross_pollination()

        self._mined = True

        return {
            "repos_scanned": len(self.repos),
            "repos_with_git": sum(1 for s in scan_results.values() if s.get("is_git")),
            "total_commits": total_commits,
            "unique_authors": len(self._author_patterns),
            "cross_poll_events": len(self._cross_events),
            "time_span_days": self._time_span_days(),
            "repo_details": {
                name: {
                    "commits": scan_results[name].get("commit_count", 0),
                    "branches": scan_results[name].get("branches", []),
                }
                for name in scan_results
            },
        }

    def author_patterns(self) -> Dict[str, AuthorPattern]:
        """Get per-author patterns: cadence, repos, file types, active hours."""
        if not self._author_patterns:
            self._build_author_patterns()
        return self._author_patterns

    def time_patterns(self) -> dict:
        """Aggregate time-based patterns across all repos.

        Returns: hourly distribution, daily volumes, burst days, gaps.
        """
        if not self._all_commits:
            return {}

        # Hourly distribution
        hour_counts: Dict[int, int] = defaultdict(int)
        # Daily volumes
        day_counts: Dict[str, int] = defaultdict(int)
        # Inter-commit times
        deltas: List[float] = []

        sorted_commits = sorted(self._all_commits, key=lambda c: c.timestamp)
        for i, c in enumerate(sorted_commits):
            if c.timestamp > 0:
                dt = datetime.fromtimestamp(c.timestamp, tz=timezone.utc)
                hour_counts[dt.hour] += 1
                day_counts[dt.strftime("%Y-%m-%d")] += 1
                if i > 0 and sorted_commits[i - 1].timestamp > 0:
                    deltas.append(c.timestamp - sorted_commits[i - 1].timestamp)

        # Burst days (5+ commits)
        burst_days = {d: c for d, c in day_counts.items() if c >= 5}

        # Gap analysis (longest silent periods)
        gaps = []
        if deltas:
            median_delta = sorted(deltas)[len(deltas) // 2]
            for i, d in enumerate(deltas):
                if d > median_delta * 10 and d > 86400:  # 10x median and > 1 day
                    gaps.append({
                        "after_index": i,
                        "duration_hours": round(d / 3600, 1),
                    })

        return {
            "total_commits": len(self._all_commits),
            "hourly_distribution": dict(sorted(hour_counts.items())),
            "peak_hour": max(hour_counts, key=hour_counts.get) if hour_counts else None,
            "unique_days": len(day_counts),
            "burst_days": len(burst_days),
            "top_burst_days": sorted(burst_days.items(), key=lambda x: -x[1])[:5],
            "median_commit_delta_hours": round(sorted(deltas)[len(deltas)//2] / 3600, 1) if deltas else 0,
            "long_gaps": gaps[:5],
        }

    def cross_pollination(self) -> List[CrossPollEvent]:
        """Find cross-pollination events between repos.

        Three detection methods:
          1. REFERENCE: commit message mentions another repo by name
          2. SAME_AUTHOR: same author commits to different repos within 2 hours
          3. FILE_LINK: shared file paths across repos (e.g., core/*.py)
        """
        if self._cross_events:
            return self._cross_events
        self._find_cross_pollination()
        return self._cross_events

    def synergy_graph(self) -> dict:
        """Build a repo-to-repo synergy graph.

        Nodes: repos. Edges: cross-pollination events between them.
        Edge weight: number of events.
        """
        events = self.cross_pollination()
        edges: Dict[Tuple[str, str], int] = defaultdict(int)
        edge_details: Dict[Tuple[str, str], List[str]] = defaultdict(list)

        for ev in events:
            key = tuple(sorted([ev.source_repo, ev.target_repo]))
            edges[key] += 1
            edge_details[key].append(f"{ev.event_type}:{ev.source_sha[:8]}")

        nodes = list(self.repos.keys())
        graph_edges = []
        for (a, b), weight in sorted(edges.items(), key=lambda x: -x[1]):
            graph_edges.append({
                "source": a, "target": b,
                "weight": weight,
                "details": edge_details[(a, b)][:5],
            })

        return {
            "nodes": nodes,
            "edges": graph_edges,
            "density": len(graph_edges) / max(1, len(nodes) * (len(nodes) - 1) / 2),
        }

    def to_tiles(self) -> List[dict]:
        """Convert mined patterns to tiles for the collective inference loop.

        Each tile has: id, type, content, trigger, confidence, evidence.
        These can be fed directly into TileStore.admit() or fleet_intel.
        """
        tiles = []

        # Author tiles — one per author
        for author, pattern in self._author_patterns.items():
            tiles.append({
                "id": f"author-{hashlib.md5(author.encode()).hexdigest()[:8]}",
                "type": "meta",
                "content": json.dumps({
                    "author": author,
                    "total_commits": pattern.total_commits,
                    "repos": pattern.repos,
                    "avg_commit_size": round(pattern.avg_commit_size, 1),
                    "span_days": round(pattern.span_days, 1),
                    "burst_count": pattern.burst_count,
                    "top_file_types": sorted(
                        pattern.file_types.items(), key=lambda x: -x[1]
                    )[:5],
                }),
                "trigger": f"author:{author}",
                "confidence": min(1.0, pattern.total_commits / 50),
                "evidence": [f"{pattern.total_commits} commits across {len(pattern.repos)} repos"],
            })

        # Cross-pollination tiles
        synergy = self.synergy_graph()
        for edge in synergy["edges"]:
            tiles.append({
                "id": f"synergy-{edge['source'][:4]}-{edge['target'][:4]}",
                "type": "meta",
                "content": json.dumps({
                    "repos": [edge["source"], edge["target"]],
                    "event_count": edge["weight"],
                    "sample_events": edge["details"],
                }),
                "trigger": f"synergy:{edge['source']}:{edge['target']}",
                "confidence": min(1.0, edge["weight"] / 10),
                "evidence": [f"{edge['weight']} cross-pollination events"],
            })

        # Time pattern tiles
        tp = self.time_patterns()
        if tp:
            tiles.append({
                "id": "time-patterns-fleet",
                "type": "meta",
                "content": json.dumps({
                    "peak_hour": tp.get("peak_hour"),
                    "burst_days": tp.get("burst_days", 0),
                    "median_delta_hours": tp.get("median_commit_delta_hours"),
                    "unique_active_days": tp.get("unique_days", 0),
                }),
                "trigger": "time:patterns",
                "confidence": 0.8,
                "evidence": [f"{tp.get('total_commits', 0)} commits analyzed"],
            })

        return tiles

    # ── Internal ──

    def _build_author_patterns(self) -> None:
        """Analyze per-author patterns from all commits."""
        author_commits: Dict[str, List[CommitData]] = defaultdict(list)
        for c in self._all_commits:
            author_commits[c.author].append(c)

        for author, commits in author_commits.items():
            timestamps = sorted([c.timestamp for c in commits if c.timestamp > 0])
            sizes = [c.size for c in commits]
            file_types: Dict[str, int] = defaultdict(int)
            active_hours: List[int] = []

            for c in commits:
                for f in c.files_changed:
                    ext = os.path.splitext(f)[1] or "no-ext"
                    file_types[ext] += 1
                if c.timestamp > 0:
                    dt = datetime.fromtimestamp(c.timestamp, tz=timezone.utc)
                    active_hours.append(dt.hour)

            # Compute inter-commit times
            deltas = []
            for i in range(1, len(timestamps)):
                deltas.append(timestamps[i] - timestamps[i - 1])

            # Burst days
            day_counts: Dict[str, int] = defaultdict(int)
            for c in commits:
                if c.timestamp > 0:
                    dt = datetime.fromtimestamp(c.timestamp, tz=timezone.utc)
                    day_counts[dt.strftime("%Y-%m-%d")] += 1

            repos = list(set(c.repo_name for c in commits))

            self._author_patterns[author] = AuthorPattern(
                name=author,
                total_commits=len(commits),
                repos=repos,
                avg_commit_size=sum(sizes) / len(sizes) if sizes else 0,
                avg_time_between=sum(deltas) / len(deltas) if deltas else 0,
                active_hours=active_hours,
                file_types=dict(file_types),
                first_commit=timestamps[0] if timestamps else 0,
                last_commit=timestamps[-1] if timestamps else 0,
                burst_count=sum(1 for d, c in day_counts.items() if c >= 5),
            )

    def _find_cross_pollination(self) -> None:
        """Detect cross-pollination events between repos."""
        events: List[CrossPollEvent] = []
        repo_names = self._repo_names

        # TYPE 1: REFERENCE — commit message mentions another repo
        for c in self._all_commits:
            refs = c.references_repo(repo_names)
            for ref_repo in refs:
                events.append(CrossPollEvent(
                    event_type="reference",
                    source_repo=c.repo_name,
                    target_repo=ref_repo,
                    source_sha=c.sha,
                    author=c.author,
                    timestamp=c.timestamp,
                    details=c.message_summary[:100],
                    strength=1.0,
                ))

        # TYPE 2: SAME_AUTHOR — same person commits to different repos within 2 hours
        author_commits: Dict[str, List[CommitData]] = defaultdict(list)
        for c in self._all_commits:
            author_commits[c.author].append(c)

        for author, commits in author_commits.items():
            sorted_c = sorted(commits, key=lambda c: c.timestamp)
            for i in range(1, len(sorted_c)):
                if sorted_c[i].repo_name != sorted_c[i - 1].repo_name:
                    delta = sorted_c[i].timestamp - sorted_c[i - 1].timestamp
                    if 0 < delta < 7200:  # within 2 hours
                        events.append(CrossPollEvent(
                            event_type="same_author",
                            source_repo=sorted_c[i - 1].repo_name,
                            target_repo=sorted_c[i].repo_name,
                            source_sha=sorted_c[i - 1].sha,
                            author=author,
                            timestamp=sorted_c[i].timestamp,
                            details=f"{delta/60:.0f}min gap between repos",
                            strength=1.0 - (delta / 7200),
                        ))

        # TYPE 3: FILE_LINK — shared file paths across repos
        repo_files: Dict[str, Set[str]] = defaultdict(set)
        for c in self._all_commits:
            for f in c.files_changed:
                # Normalize: use basename for comparison
                basename = os.path.basename(f)
                if basename and not basename.startswith("."):
                    repo_files[c.repo_name].add(basename)

        shared: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
        repo_list = list(repo_files.keys())
        for i, r1 in enumerate(repo_list):
            for r2 in repo_list[i + 1:]:
                overlap = repo_files[r1] & repo_files[r2]
                if len(overlap) >= 3:  # meaningful overlap
                    shared[(r1, r2)] = overlap

        for (r1, r2), files in shared.items():
            events.append(CrossPollEvent(
                event_type="file_link",
                source_repo=r1,
                target_repo=r2,
                source_sha="",
                author="",
                timestamp=time.time(),
                details=f"{len(files)} shared files: {', '.join(list(files)[:5])}",
                strength=min(1.0, len(files) / 20),
            ))

        self._cross_events = events

    def _time_span_days(self) -> float:
        """Total time span of all commits."""
        timestamps = [c.timestamp for c in self._all_commits if c.timestamp > 0]
        if len(timestamps) < 2:
            return 0
        return (max(timestamps) - min(timestamps)) / 86400


# ─── Demo ─────────────────────────────────────────────────────────────────────

def demo():
    """Mine 3+ real fleet repos and show the patterns."""
    print("FLEET MINER — Git History → Collective Inference Signal")
    print("=" * 60)

    # Discover repos
    repo_paths = [
        "/home/phoenix/.openclaw/workspace",
        "/home/phoenix/projects/constraint-theory-core",
        "/home/phoenix/projects/constraint-theory-python",
        "/home/phoenix/projects/Constraint-Theory",
        "/home/phoenix/projects/cocapn",
        "/home/phoenix/projects/pasture-ai",
        "/home/phoenix/projects/Constraint-Theory-web",
        "/home/phoenix/projects/cacapn",
    ]

    # Filter to paths that exist
    repo_paths = [p for p in repo_paths if os.path.isdir(p)]
    print(f"\n1. DISCOVERED {len(repo_paths)} repos")

    miner = FleetMiner(repo_paths)

    # Phase 1: SCAN
    print("\n2. SCANNING")
    for name, repo in miner.repos.items():
        info = repo.scan()
        if info.get("is_git"):
            print(f"   {name}: {info['commit_count']} commits, {len(info['branches'])} branches")
        else:
            print(f"   {name}: not a git repo")

    # Phase 2: EXTRACT
    print("\n3. EXTRACTING")
    report = miner.mine_all(max_per_repo=500)
    print(f"   Total commits: {report['total_commits']}")
    print(f"   Unique authors: {report['unique_authors']}")
    print(f"   Time span: {report['time_span_days']:.0f} days")

    # Phase 3: AUTHOR PATTERNS
    print("\n4. AUTHOR PATTERNS")
    authors = miner.author_patterns()
    for author in sorted(authors, key=lambda a: -authors[a].total_commits)[:6]:
        p = authors[author]
        repos_str = ", ".join(p.repos[:3])
        top_types = sorted(p.file_types.items(), key=lambda x: -x[1])[:3]
        types_str = ", ".join(f"{ext}({cnt})" for ext, cnt in top_types)
        print(f"   {author}:")
        print(f"     {p.total_commits} commits across {repos_str}")
        print(f"     Avg size: {p.avg_commit_size:.0f} lines, span: {p.span_days:.0f} days")
        print(f"     File types: {types_str}")
        print(f"     Burst days: {p.burst_count}")

    # Phase 4: TIME PATTERNS
    print("\n5. TIME PATTERNS")
    tp = miner.time_patterns()
    if tp:
        print(f"   Peak hour (UTC): {tp.get('peak_hour')}")
        print(f"   Active days: {tp.get('unique_days', 0)}")
        print(f"   Burst days (5+ commits): {tp.get('burst_days', 0)}")
        print(f"   Median delta: {tp.get('median_commit_delta_hours', 0)}h")
        if tp.get("top_burst_days"):
            print("   Top burst days:")
            for day, count in tp["top_burst_days"][:3]:
                print(f"     {day}: {count} commits")
        if tp.get("long_gaps"):
            print(f"   Longest gaps:")
            for gap in tp["long_gaps"][:3]:
                print(f"     {gap['duration_hours']}h gap")

    # Phase 5: CROSS-POLLINATION
    print("\n6. CROSS-POLLINATION")
    events = miner.cross_pollination()
    by_type = defaultdict(int)
    for ev in events:
        by_type[ev.event_type] += 1
    print(f"   Total events: {len(events)}")
    for etype, count in sorted(by_type.items(), key=lambda x: -x[1]):
        print(f"   {etype}: {count}")

    # Show strongest connections
    if events:
        print("\n   Strongest connections:")
        seen = set()
        for ev in sorted(events, key=lambda e: -e.strength):
            pair = tuple(sorted([ev.source_repo, ev.target_repo]))
            if pair not in seen:
                seen.add(pair)
                print(f"     {ev.source_repo} ↔ {ev.target_repo}: {ev.details[:60]}")
                if len(seen) >= 5:
                    break

    # Phase 6: SYNERGY GRAPH
    print("\n7. SYNERGY GRAPH")
    graph = miner.synergy_graph()
    print(f"   Nodes: {len(graph['nodes'])}")
    print(f"   Edges: {len(graph['edges'])}")
    print(f"   Density: {graph['density']:.2f}")
    for edge in graph["edges"][:5]:
        print(f"   {edge['source']} → {edge['target']}: weight={edge['weight']}")

    # Phase 7: TILES
    print("\n8. TILES (feeding collective inference)")
    tiles = miner.to_tiles()
    print(f"   Generated {len(tiles)} tiles")
    for tile in tiles[:5]:
        print(f"   [{tile['type']}] {tile['id']}: {tile['trigger']}")
        print(f"     confidence={tile['confidence']:.2f}, evidence={tile['evidence']}")

    print("\n" + "=" * 60)
    print(f"RESULT: Mined {report['total_commits']} commits from {report['repos_scanned']} repos.")
    print(f"Found {report['unique_authors']} authors, {len(events)} cross-pollination events.")
    print(f"Generated {len(tiles)} tiles for the collective inference loop.")
    print("The git history IS the fleet's fossil record. Now it's data.")


if __name__ == "__main__":
    demo()
