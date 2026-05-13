from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.repository_source_probe import RepositorySourceProbe
from testing.core.models.repository_source_match import RepositorySourceMatch


class PythonRepositorySourceTreeFramework(RepositorySourceProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = repository_root

    def find_literal_matches(
        self,
        *,
        roots: tuple[str, ...],
        literal: str,
        file_glob: str = "*.dart",
    ) -> tuple[RepositorySourceMatch, ...]:
        matches: list[RepositorySourceMatch] = []
        for root in roots:
            for path in self._iter_files(root=root, file_glob=file_glob):
                for line_number, line_text in enumerate(
                    path.read_text(encoding="utf-8").splitlines(),
                    start=1,
                ):
                    if literal in line_text:
                        matches.append(
                            RepositorySourceMatch(
                                relative_path=path.relative_to(self._repository_root).as_posix(),
                                line_number=line_number,
                                line_text=line_text,
                            )
                        )
        return tuple(matches)

    def read_text(self, relative_path: str) -> str:
        return self._resolve(relative_path).read_text(encoding="utf-8")

    def read_lines(
        self,
        relative_path: str,
        *,
        start_line: int = 1,
        end_line: int | None = None,
    ) -> tuple[str, ...]:
        lines = self.read_text(relative_path).splitlines()
        start_index = max(start_line - 1, 0)
        stop_index = len(lines) if end_line is None else min(end_line, len(lines))
        return tuple(lines[start_index:stop_index])

    def _iter_files(self, *, root: str, file_glob: str) -> tuple[Path, ...]:
        candidate = self._resolve(root)
        if candidate.is_file():
            return (candidate,)
        if not candidate.is_dir():
            raise FileNotFoundError(
                f"Repository source root does not exist: {candidate}"
            )
        return tuple(
            sorted(path for path in candidate.rglob(file_glob) if path.is_file())
        )

    def _resolve(self, relative_path: str) -> Path:
        return (self._repository_root / relative_path).resolve()

