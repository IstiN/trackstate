from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from testing.core.config.semantic_label_context_lint_config import (
    SemanticLabelContextLintConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.semantic_label_context_compliance_result import (
    SemanticLabelContextComplianceResult,
)


class SemanticLabelContextComplianceValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: SemanticLabelContextLintConfig,
    ) -> SemanticLabelContextComplianceResult:
        temp_repository_root = Path(tempfile.mkdtemp(prefix="ts923-"))

        try:
            self._copy_repository(temp_repository_root)

            flutter_version = self._probe.flutter_version()
            pub_get = self._probe.pub_get(temp_repository_root)

            target_path = temp_repository_root / config.target_relative_path
            localization_path = temp_repository_root / config.localization_relative_path
            source = target_path.read_text(encoding="utf-8")
            localization_source = localization_path.read_text(encoding="utf-8")
            analyze = self._probe.analyze(
                temp_repository_root,
                config.target_relative_path,
            )

            return SemanticLabelContextComplianceResult(
                flutter_version=flutter_version,
                pub_get=pub_get,
                analyze=analyze,
                temp_repository_root=temp_repository_root,
                target_relative_path=config.target_relative_path,
                localization_relative_path=config.localization_relative_path,
                source=source,
                localization_source=localization_source,
            )
        finally:
            if not config.keep_temp_project and temp_repository_root.exists():
                shutil.rmtree(temp_repository_root)

    def _copy_repository(self, destination: Path) -> None:
        shutil.copytree(
            self._repository_root,
            destination,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".dart_tool",
                "build",
                "outputs",
            ),
        )
