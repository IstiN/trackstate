from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ThemeTokenNestedDirectoryViolationConfig:
    flutter_version: str
    target_path: str
    probe_relative_path: Path
    success_message: str
    violation_literal: str
    required_diagnostic_fragments: tuple[str, ...]
    keep_temp_project: bool

    @classmethod
    def from_env(
        cls,
        *,
        env_prefixes: tuple[str, ...] = ("TS157", "TS132", "TS115", "TRACKSTATE"),
        default_flutter_version: str = "3.35.3",
        default_target_path: str = "lib/",
        default_probe_relative_path: str = "lib/nest_test/violation.dart",
        default_success_message: str = "No theme token policy violations found.",
        default_violation_literal: str = "Color(0xFF112233)",
    ) -> "ThemeTokenNestedDirectoryViolationConfig":
        return cls(
            flutter_version=_read_env(
                "FLUTTER_VERSION",
                env_prefixes=env_prefixes,
                default=default_flutter_version,
            ),
            target_path=_read_env(
                "TARGET_PATH",
                env_prefixes=env_prefixes,
                default=default_target_path,
            ),
            probe_relative_path=Path(
                _read_env(
                    "PROBE_PATH",
                    env_prefixes=env_prefixes,
                    default=default_probe_relative_path,
                ),
            ),
            success_message=_read_env(
                "SUCCESS_MESSAGE",
                env_prefixes=env_prefixes,
                default=default_success_message,
            ),
            violation_literal=_read_env(
                "VIOLATION_LITERAL",
                env_prefixes=env_prefixes,
                default=default_violation_literal,
            ),
            required_diagnostic_fragments=(
                "theme",
                "token",
                "hardcoded",
                "color",
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
