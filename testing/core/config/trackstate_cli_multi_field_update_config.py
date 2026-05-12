from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliMultiFieldUpdateConfig:
    project_key: str
    project_name: str
    issue_key: str
    initial_summary: str
    initial_priority_id: str
    initial_assignee: str
    initial_labels: tuple[str, ...]
    updated_summary: str
    updated_priority_name: str
    updated_priority_id: str
    updated_assignee: str
    updated_labels: tuple[str, ...]
    requested_command_prefix: tuple[str, ...]
    fallback_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    expected_commit_subject: str

    @classmethod
    def from_env(cls) -> "TrackStateCliMultiFieldUpdateConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        issue_key = "TS-1"
        return cls(
            project_key="TS",
            project_name="TS-460 Local Multi-field Update Project",
            issue_key=issue_key,
            initial_summary="Old Title",
            initial_priority_id="low",
            initial_assignee="old-user",
            initial_labels=("legacy",),
            updated_summary="New Title",
            updated_priority_name="High",
            updated_priority_id="high",
            updated_assignee="user1",
            updated_labels=("bug", "ai"),
            requested_command_prefix=(
                "trackstate",
                "jira_update_ticket",
                "--target",
                "local",
            ),
            fallback_command_prefix=(
                dart_bin,
                "run",
                "trackstate",
                "jira_update_ticket",
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
                "issue",
            ),
            expected_commit_subject=f"Update {issue_key} fields",
        )
