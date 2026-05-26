from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliHierarchyAliasConfig:
    project_key: str
    project_name: str
    epic_key: str
    target_story_key: str
    source_story_key: str
    subtask_key: str
    created_summary: str
    required_top_level_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    requested_create_command: tuple[str, ...]
    requested_update_command: tuple[str, ...]

    @property
    def expected_updated_subtask_path(self) -> str:
        return (
            f"{self.project_key}/{self.epic_key}/"
            f"{self.target_story_key}/{self.subtask_key}/main.md"
        )

    @property
    def expected_original_subtask_path(self) -> str:
        return (
            f"{self.project_key}/{self.epic_key}/"
            f"{self.source_story_key}/{self.subtask_key}/main.md"
        )

    @classmethod
    def from_env(cls) -> "TrackStateCliHierarchyAliasConfig":
        return cls(
            project_key="HIER",
            project_name="TS-459 Hierarchy Alias Project",
            epic_key="EPIC-1",
            target_story_key="STORY-1",
            source_story_key="STORY-2",
            subtask_key="SUB-1",
            created_summary="Task",
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
            requested_create_command=(
                "trackstate",
                "jira_create_ticket_with_parent",
                "--target",
                "local",
                "--summary",
                "Task",
                "--parent",
                "EPIC-1",
            ),
            requested_update_command=(
                "trackstate",
                "jira_update_ticket_parent",
                "--target",
                "local",
                "--issueKey",
                "SUB-1",
                "--parent",
                "STORY-1",
            ),
        )
