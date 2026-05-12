from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliCommentCreationConfig:
    project_key: str
    project_name: str
    issue_key: str
    comment_body: str
    requested_command_prefix: tuple[str, ...]
    fallback_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    expected_comment_ids: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "TrackStateCliCommentCreationConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            project_key="TS",
            project_name="TS-462 Local Comment Test Project",
            issue_key="TS-1",
            comment_body="Test Comment",
            requested_command_prefix=(
                "trackstate",
                "ticket",
                "comment",
                "--target",
                "local",
            ),
            fallback_command_prefix=(
                dart_bin,
                "run",
                "trackstate",
                "ticket",
                "comment",
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
            required_data_keys=(
                "command",
                "operation",
                "authSource",
                "revision",
                "comment",
                "issue",
            ),
            expected_comment_ids=("0001", "0002"),
        )
