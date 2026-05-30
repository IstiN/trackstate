from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SemanticLabelContextLintConfig:
    flutter_version: str
    source_git_ref: str
    target_relative_path: Path
    localization_relative_path: Path
    semantic_label_localization_key: str
    required_source_snippet: str
    replacement_source_snippet: str
    required_semantic_label: str
    generic_semantic_label: str
    required_issue_terms: tuple[str, ...]
    required_context_terms: tuple[str, ...]
    keep_temp_project: bool

    @classmethod
    def from_env(
        cls,
        *,
        env_prefixes: tuple[str, ...] = ("TS907", "TRACKSTATE"),
    ) -> "SemanticLabelContextLintConfig":
        return cls(
            flutter_version=_read_env(
                "FLUTTER_VERSION",
                env_prefixes=env_prefixes,
                default="3.35.3",
            ),
            source_git_ref=_read_env(
                "SOURCE_GIT_REF",
                env_prefixes=env_prefixes,
                default="origin/main",
            ),
            target_relative_path=Path(
                _read_env(
                    "TARGET_PATH",
                    env_prefixes=env_prefixes,
                    default="lib/ui/features/tracker/views/trackstate_app.dart",
                ),
            ),
            localization_relative_path=Path(
                _read_env(
                    "LOCALIZATION_PATH",
                    env_prefixes=env_prefixes,
                    default="lib/l10n/app_en.arb",
                ),
            ),
            semantic_label_localization_key=_read_env(
                "SEMANTIC_LABEL_LOCALIZATION_KEY",
                env_prefixes=env_prefixes,
                default="workspaceSyncAttentionNeededSemanticLabel",
            ),
            required_source_snippet=_read_env(
                "REQUIRED_SOURCE_SNIPPET",
                env_prefixes=env_prefixes,
                default="_l10n.workspaceSyncAttentionNeededSemanticLabel,",
            ),
            replacement_source_snippet=_read_env(
                "REPLACEMENT_SOURCE_SNIPPET",
                env_prefixes=env_prefixes,
                default="_l10n.workspaceSyncAttentionNeededVisibleLabel,",
            ),
            required_semantic_label=_read_env(
                "REQUIRED_SEMANTIC_LABEL",
                env_prefixes=env_prefixes,
                default="Sync error, attention needed",
            ),
            generic_semantic_label=_read_env(
                "GENERIC_SEMANTIC_LABEL",
                env_prefixes=env_prefixes,
                default="Attention needed",
            ),
            required_issue_terms=(
                "sync",
                "error",
                "attention",
            ),
            required_context_terms=(
                "accessibility",
                "aria",
                "semantic",
                "semantics",
                "label",
                "context",
                "prefix",
            ),
            keep_temp_project=_read_env(
                "KEEP_TEMP_PROJECT",
                env_prefixes=env_prefixes,
                default="0",
            )
            == "1",
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
