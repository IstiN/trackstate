from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceSyncSemanticLabelContractConfig:
    flutter_version: str
    test_relative_path: Path
    source_relative_path: Path
    expected_test_name: str
    expected_result: str
    required_test_snippets: tuple[str, ...]
    required_source_snippets: tuple[str, ...]
    mutation_snippet: str
    flutter_test_reporter: str

    @classmethod
    def from_env(
        cls,
        *,
        env_prefixes: tuple[str, ...] = ("TS937", "TRACKSTATE"),
    ) -> "WorkspaceSyncSemanticLabelContractConfig":
        expected_test_name = _read_env(
            "EXPECTED_TEST_NAME",
            env_prefixes=env_prefixes,
            default=(
                "flutter analyze rejects a raw string passed to the workspace sync "
                "semantic label API"
            ),
        )
        mutation_snippet = _read_env(
            "MUTATION_SNIPPET",
            env_prefixes=env_prefixes,
            default="semanticLabel: 'Attention needed',",
        )
        return cls(
            flutter_version=_read_env(
                "FLUTTER_VERSION",
                env_prefixes=env_prefixes,
                default="3.35.3",
            ),
            test_relative_path=Path(
                _read_env(
                    "TEST_PATH",
                    env_prefixes=env_prefixes,
                    default="test/workspace_sync_semantic_label_contract_test.dart",
                ),
            ),
            source_relative_path=Path(
                _read_env(
                    "SOURCE_PATH",
                    env_prefixes=env_prefixes,
                    default="lib/ui/features/tracker/views/trackstate_app.dart",
                ),
            ),
            expected_test_name=expected_test_name,
            expected_result=_read_env(
                "EXPECTED_RESULT",
                env_prefixes=env_prefixes,
                default=(
                    "The unit test passes, confirming that the widget's API is "
                    "programmatically constrained to the authorized localization "
                    "contract, preventing regressions to primitive String literals."
                ),
            ),
            required_test_snippets=(
                "test(",
                expected_test_name,
                "semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),",
                mutation_snippet,
                "lib/ui/features/tracker/views/trackstate_app.dart",
                "'analyze'",
            ),
            required_source_snippets=(
                "final _SyncPillSemanticLabel? semanticLabel;",
                "_SyncPillSemanticLabel _workspaceSyncSemanticLabel(",
                "semanticLabel: _workspaceSyncSemanticLabel(l10n, viewModel),",
            ),
            mutation_snippet=mutation_snippet,
            flutter_test_reporter=_read_env(
                "FLUTTER_TEST_REPORTER",
                env_prefixes=env_prefixes,
                default="expanded",
            ),
        )


def _read_env(
    suffix: str,
    *,
    env_prefixes: tuple[str, ...],
    default: str,
) -> str:
    for prefix in env_prefixes:
        value = os.environ.get(f"{prefix}_{suffix}")
        if value is not None:
            return value
    return default
