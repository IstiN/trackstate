from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.models.repository_source_match import RepositorySourceMatch


@dataclass(frozen=True)
class FlutterDependencyBoundaryValidationResult:
    repository_root: Path
    search_roots: tuple[str, ...]
    provider_relative_path: str
    disallowed_import_matches: tuple[RepositorySourceMatch, ...]
    provider_forbidden_import_matches: tuple[RepositorySourceMatch, ...]
    provider_meta_import_matches: tuple[RepositorySourceMatch, ...]
    provider_required_keyword_matches: tuple[RepositorySourceMatch, ...]
    provider_import_lines: tuple[str, ...]
    provider_excerpt_lines: tuple[str, ...]
    provider_has_expected_compat_import: bool
    replacement_strategy: str | None

