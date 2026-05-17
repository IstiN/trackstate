from __future__ import annotations

from pathlib import Path

from testing.core.config.flutter_dependency_boundary_config import (
    FlutterDependencyBoundaryConfig,
)
from testing.core.interfaces.repository_source_probe import RepositorySourceProbe
from testing.core.models.flutter_dependency_boundary_validation_result import (
    FlutterDependencyBoundaryValidationResult,
)


class FlutterDependencyBoundaryValidator:
    def __init__(
        self,
        repository_root: Path,
        probe: RepositorySourceProbe,
    ) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: FlutterDependencyBoundaryConfig,
    ) -> FlutterDependencyBoundaryValidationResult:
        disallowed_import_matches = self._probe.find_literal_matches(
            roots=config.search_roots,
            literal=config.disallowed_flutter_import_literal,
        )
        provider_forbidden_import_matches = tuple(
            match
            for fragment in config.forbidden_provider_import_fragments
            for match in self._probe.find_literal_matches(
                roots=(config.provider_relative_path,),
                literal=fragment,
            )
        )
        provider_meta_import_matches = self._probe.find_literal_matches(
            roots=(config.provider_relative_path,),
            literal=config.meta_import_literal,
        )
        provider_required_keyword_matches = self._probe.find_literal_matches(
            roots=(config.provider_relative_path,),
            literal=config.replacement_keyword_literal,
        )
        provider_import_lines = tuple(
            line.strip()
            for line in self._probe.read_lines(
                config.provider_relative_path,
                start_line=1,
                end_line=config.provider_excerpt_end_line,
            )
            if line.strip().startswith("import ")
        )
        provider_excerpt_lines = self._probe.read_lines(
            config.provider_relative_path,
            start_line=1,
            end_line=config.provider_excerpt_end_line,
        )
        provider_has_expected_compat_import = any(
            config.expected_provider_import_fragment in line
            for line in provider_import_lines
        )

        replacement_strategy: str | None = None
        if provider_meta_import_matches:
            replacement_strategy = "package:meta"
        elif provider_required_keyword_matches:
            replacement_strategy = "dart-required-keyword"

        return FlutterDependencyBoundaryValidationResult(
            repository_root=self._repository_root,
            search_roots=config.search_roots,
            provider_relative_path=config.provider_relative_path,
            disallowed_import_matches=disallowed_import_matches,
            provider_forbidden_import_matches=provider_forbidden_import_matches,
            provider_meta_import_matches=provider_meta_import_matches,
            provider_required_keyword_matches=provider_required_keyword_matches,
            provider_import_lines=provider_import_lines,
            provider_excerpt_lines=provider_excerpt_lines,
            provider_has_expected_compat_import=provider_has_expected_compat_import,
            replacement_strategy=replacement_strategy,
        )

