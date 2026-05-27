"""Artifact — Build output tracking with content-addressable identity."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ArtifactState(Enum):
    BUILDING = "building"
    READY = "ready"
    STALE = "stale"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class Artifact:
    """Tracks a build output — binary, image, package, or derived artifact."""

    name: str
    path: str
    recipe_name: str
    tags: list[str] = field(default_factory=list)
    state: ArtifactState = ArtifactState.UNKNOWN
    digest: str = ""
    size_bytes: int = 0
    build_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def compute_digest(self, content: bytes | None = None) -> str:
        if content is not None:
            self.digest = hashlib.sha256(content).hexdigest()[:40]
            self.size_bytes = len(content)
            self.state = ArtifactState.READY
        else:
            self.state = ArtifactState.STALE
        return self.digest

    def mark_ready(self, digest: str, size_bytes: int) -> None:
        self.digest = digest
        self.size_bytes = size_bytes
        self.state = ArtifactState.READY

    def mark_failed(self) -> None:
        self.state = ArtifactState.FAILED

    def is_valid(self) -> bool:
        return self.state in (ArtifactState.READY, ArtifactState.BUILDING)

    def age_seconds(self, now: float | None = None) -> float:
        return (now or time.time()) - self.created_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "recipe_name": self.recipe_name,
            "tags": self.tags,
            "state": self.state.value,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "build_time_ms": self.build_time_ms,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
