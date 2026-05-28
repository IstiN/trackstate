from __future__ import annotations

from typing import Protocol

from testing.core.models.repository_source_match import RepositorySourceMatch


class RepositorySourceProbe(Protocol):
    def find_literal_matches(
        self,
        *,
        roots: tuple[str, ...],
        literal: str,
        file_glob: str = "*.dart",
    ) -> tuple[RepositorySourceMatch, ...]: ...

    def read_text(self, relative_path: str) -> str: ...

    def read_lines(
        self,
        relative_path: str,
        *,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> tuple[str, ...]: ...

