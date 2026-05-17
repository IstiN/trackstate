from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepositorySourceMatch:
    relative_path: str
    line_number: int
    line_text: str

