from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliFieldResolutionConfig:
    project_key: str
    project_name: str
    issue_key: str
    initial_summary: str
    initial_priority_id: str
    initial_assignee: str
    custom_field_definitions: tuple[tuple[str, str, str], ...]
    initial_custom_fields: tuple[tuple[str, int], ...]
    exact_field_identifier: str
    exact_field_value: int
    display_name_identifier: str
    display_name_value: int
    ambiguous_field_identifier: str
    ambiguous_field_value: int
    ambiguous_field_ids: tuple[str, ...]
    conflict_display_name: str
    requested_command_prefix: tuple[str, ...]
    fallback_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_success_data_keys: tuple[str, ...]
    required_error_keys: tuple[str, ...]
    expected_command_name: str
    expected_commit_subject: str

    @classmethod
    def from_env(cls) -> "TrackStateCliFieldResolutionConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        issue_key = "TS-1"
        return cls(
            project_key="TS",
            project_name="TS-458 Local Field Resolution Project",
            issue_key=issue_key,
            initial_summary="TS-458 fixture",
            initial_priority_id="medium",
            initial_assignee="ts458-user",
            custom_field_definitions=(
                ("customfield_10016", "Canonical Points", "number"),
                ("storyPoints", "Story Points", "number"),
                ("velocityPoints", "Velocity Points", "number"),
                ("effortPoints", "Effort Points", "number"),
            ),
            initial_custom_fields=(
                ("customfield_10016", 1),
                ("storyPoints", 2),
                ("velocityPoints", 13),
                ("effortPoints", 21),
            ),
            exact_field_identifier="customfield_10016",
            exact_field_value=8,
            display_name_identifier="Story Points",
            display_name_value=5,
            ambiguous_field_identifier="Points",
            ambiguous_field_value=3,
            ambiguous_field_ids=("velocityPoints", "effortPoints"),
            conflict_display_name="Points",
            requested_command_prefix=(
                "trackstate",
                "ticket",
                "update-field",
                "--target",
                "local",
            ),
            fallback_command_prefix=(
                dart_bin,
                "run",
                "trackstate",
                "ticket",
                "update-field",
                "--target",
                "local",
            ),
            required_top_level_keys=(
                "schemaVersion",
                "ok",
                "provider",
                "target",
                "output",
            ),
            required_success_data_keys=(
                "command",
                "operation",
                "authSource",
                "revision",
                "field",
                "issue",
            ),
            required_error_keys=(
                "code",
                "category",
                "message",
                "exitCode",
                "details",
            ),
            expected_command_name="ticket-update-field",
            expected_commit_subject=f"Update {issue_key} fields",
        )
