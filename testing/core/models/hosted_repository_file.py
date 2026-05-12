from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HostedRepositoryFile:
    path: str
    sha: str
    content: str
