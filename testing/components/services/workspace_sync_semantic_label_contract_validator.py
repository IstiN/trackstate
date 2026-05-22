from __future__ import annotations

from pathlib import Path

from testing.core.config.workspace_sync_semantic_label_contract_config import (
    WorkspaceSyncSemanticLabelContractConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.workspace_sync_semantic_label_contract_result import (
    WorkspaceSyncSemanticLabelContractResult,
)


class WorkspaceSyncSemanticLabelContractValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: WorkspaceSyncSemanticLabelContractConfig,
    ) -> WorkspaceSyncSemanticLabelContractResult:
        flutter_version = self._probe.flutter_version()
        pub_get = self._probe.pub_get(self._repository_root)

        test_source = self._read_required_file(config.test_relative_path)
        source = self._read_required_file(config.source_relative_path)
        flutter_test = self._probe.test(
            self._repository_root,
            config.test_relative_path,
            reporter=config.flutter_test_reporter,
        )

        return WorkspaceSyncSemanticLabelContractResult(
            flutter_version=flutter_version,
            pub_get=pub_get,
            flutter_test=flutter_test,
            test_relative_path=config.test_relative_path,
            source_relative_path=config.source_relative_path,
            test_source=test_source,
            source=source,
        )

    def _read_required_file(self, relative_path: Path) -> str:
        path = self._repository_root / relative_path
        if not path.is_file():
            raise AssertionError(f"Required file is missing: {relative_path.as_posix()}")
        return path.read_text(encoding="utf-8")
