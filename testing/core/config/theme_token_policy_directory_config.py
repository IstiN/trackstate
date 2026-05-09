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
    def from_env(cls) -> "ThemeTokenPolicyDirectoryConfig":
        return cls(
            flutter_version=os.environ.get(
                "TS132_FLUTTER_VERSION",
                os.environ.get("TRACKSTATE_FLUTTER_VERSION", "3.35.3"),
            ),
            target_path=os.environ.get("TS132_TARGET_PATH", "lib/"),
            success_message=os.environ.get(
                "TS132_SUCCESS_MESSAGE",
                "No theme token policy violations found.",
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
