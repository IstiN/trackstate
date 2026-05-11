from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliHelpConfig:
    requested_root_help_command: tuple[str, ...]
    requested_session_help_command: tuple[str, ...]
    fallback_root_help_command: tuple[str, ...]
    fallback_session_help_command: tuple[str, ...]
    required_root_examples: tuple[str, ...]
    required_root_option_fragments: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "TrackStateCliHelpConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            requested_root_help_command=("trackstate", "--help"),
            requested_session_help_command=("trackstate", "session", "--help"),
            fallback_root_help_command=(dart_bin, "run", "trackstate", "--help"),
            fallback_session_help_command=(
                dart_bin,
                "run",
                "trackstate",
                "session",
                "--help",
            ),
            required_root_examples=(
                "trackstate session --target local",
                "trackstate session --target hosted --provider github --repository owner/name",
            ),
            required_root_option_fragments=(
                "--target",
                "Target type: local or hosted.",
                "--provider",
                "Provider name. Supported values: local-git, github.",
                "--repository",
                "Hosted repository in owner/name form.",
            ),
        )
