from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeTokenPolicyDirectoryConfig:
    flutter_version: str
    target_path: str
    success_message: str
    diagnostic_markers: tuple[str, ...]

    @classmethod
    def from_env(
        cls,
        *,
        env_prefixes: tuple[str, ...] = ("TS132", "TRACKSTATE"),
        default_flutter_version: str = "3.35.3",
        default_target_path: str = "lib/",
        default_success_message: str = "No theme token policy violations found.",
    ) -> "ThemeTokenPolicyDirectoryConfig":
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
