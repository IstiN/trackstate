from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliCreateNativeHierarchyConfig:
    project_key: str
    project_name: str
    epic_key: str
    summary: str
    requested_command_prefix: tuple[str, ...]
    fallback_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_target_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    required_issue_keys: tuple[str, ...]
    expected_command_name: str
    expected_issue_key: str
    expected_issue_type: str
    expected_status: str
    expected_priority: str
    expected_description: str
    expected_author_email: str

    @property
    def expected_storage_path(self) -> str:
        return (
            f"{self.project_key}/{self.epic_key}/{self.expected_issue_key}/main.md"
        )

    @classmethod
    def from_env(cls) -> "TrackStateCliCreateNativeHierarchyConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            project_key="TS",
            project_name="TS-457 Local Create Test Project",
            epic_key="EPIC-101",
            summary="New Story",
            requested_command_prefix=(
                "trackstate",
                "create",
                "--summary",
                "New Story",
                "--issueType",
                "Story",
                "--epic",
                "EPIC-101",
                "--target",
                "local",
            ),
            fallback_command_prefix=(
                dart_bin,
                "run",
                "trackstate",
                "create",
                "--summary",
                "New Story",
                "--issueType",
                "Story",
                "--epic",
                "EPIC-101",
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
                "operation",
                "authSource",
                "revision",
                "issue",
            ),
            required_issue_keys=(
                "key",
                "project",
                "summary",
                "description",
                "issueType",
                "status",
                "priority",
                "assignee",
                "reporter",
                "labels",
                "epic",
                "storagePath",
                "archived",
            ),
            expected_command_name="ticket-create",
            expected_issue_key="TS-1",
            expected_issue_type="story",
            expected_status="todo",
            expected_priority="medium",
            expected_description="Describe the issue.",
            expected_author_email="ts457@example.com",
        )
