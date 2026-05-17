from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliHttpRequestObservation:
    method: str
    url: str
    host: str
    path: str
    query: str | None
    rewritten_url: str | None = None
