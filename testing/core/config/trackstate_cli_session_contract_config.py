from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliSessionContractConfig:
    requested_command_prefix: tuple[str, ...]
    fallback_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_target_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    required_permission_keys: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "TrackStateCliSessionContractConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            requested_command_prefix=("trackstate", "session", "--target", "local"),
            fallback_command_prefix=(
                dart_bin,
                "run",
                "trackstate",
                "session",
                "--target",
                "local",
            ),
            required_top_level_keys=(
                "schemaVersion",
                "ok",
                "provider",
                "target",
                "output",
                "data",
            ),
            required_target_keys=("type", "value"),
            required_data_keys=(
                "command",
                "provider",
                "branch",
                "authSource",
                "user",
                "permissions",
            ),
            required_permission_keys=(
                "canRead",
                "canWrite",
                "isAdmin",
                "canCreateBranch",
                "canManageAttachments",
                "canCheckCollaborators",
            ),
        )
