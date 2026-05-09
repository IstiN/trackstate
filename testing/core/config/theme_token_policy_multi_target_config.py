from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokenPolicyMultiTargetConfig:
    flutter_version: str
    file_target_path: str
    directory_target_path: str
    success_message: str
    diagnostic_markers: tuple[str, ...]

    @property
    def command_targets(self) -> tuple[str, str]:
        return (self.file_target_path, self.directory_target_path)

    @classmethod
    def from_env(
        cls,
        *,
        env_prefixes: tuple[str, ...] = ("TS158", "TS132", "TRACKSTATE"),
        default_flutter_version: str = "3.35.3",
        default_file_target_path: str = "lib/main.dart",
        default_directory_target_path: str = "tool/",
        default_success_message: str = "No theme token policy violations found.",
    ) -> "ThemeTokenPolicyMultiTargetConfig":
        return cls(
            flutter_version=_read_env(
                "FLUTTER_VERSION",
                env_prefixes=env_prefixes,
                default=default_flutter_version,
            ),
            file_target_path=_read_env(
                "FILE_TARGET_PATH",
                env_prefixes=env_prefixes,
                default=default_file_target_path,
            ),
            directory_target_path=_read_env(
                "DIRECTORY_TARGET_PATH",
                env_prefixes=env_prefixes,
                default=default_directory_target_path,
            ),
            success_message=_read_env(
                "SUCCESS_MESSAGE",
                env_prefixes=env_prefixes,
                default=default_success_message,
            ),
            diagnostic_markers=(
                "warning •",
                "error •",
                "info •",
                " warning - ",
                " error - ",
                " info - ",
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
