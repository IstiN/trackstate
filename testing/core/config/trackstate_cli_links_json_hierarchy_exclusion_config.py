from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliLinksJsonHierarchyExclusionConfig:
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    parent_summary: str
    child_summary: str
    unrelated_source_summary: str
    unrelated_target_summary: str
    parent_create_command_prefix: tuple[str, ...]
    child_create_command_prefix: tuple[str, ...]
    unrelated_source_create_command_prefix: tuple[str, ...]
    unrelated_target_create_command_prefix: tuple[str, ...]
    link_command_prefix: tuple[str, ...]
    expected_link_payload: dict[str, str]

    @property
    def parent_issue_key(self) -> str:
        return "TS-1"

    @property
    def child_issue_key(self) -> str:
        return "TS-2"

    @property
    def unrelated_source_issue_key(self) -> str:
        return "TS-3"

    @property
    def unrelated_target_issue_key(self) -> str:
        return "TS-4"

    @property
    def child_main_relative_path(self) -> str:
        return (
            f"{self.project_key}/{self.parent_issue_key}/{self.child_issue_key}/main.md"
        )

    @property
    def links_json_relative_path(self) -> str:
        return f"{self.project_key}/{self.unrelated_source_issue_key}/links.json"

    @property
    def issue_index_relative_path(self) -> str:
        return f"{self.project_key}/.trackstate/index/issues.json"

    def parent_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.parent_create_command_prefix, "--path", repository_path)

    def child_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.child_create_command_prefix, "--path", repository_path)

    def unrelated_source_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.unrelated_source_create_command_prefix, "--path", repository_path)

    def unrelated_target_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.unrelated_target_create_command_prefix, "--path", repository_path)

    def link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.link_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliLinksJsonHierarchyExclusionConfig":
        return cls(
            project_key="TS",
            project_name="TS-602 Link Persistence Test Project",
            seed_issue_key="TS-0",
            expected_author_email="ts602@example.com",
            parent_summary="Parent Story",
            child_summary="Child Sub-task",
            unrelated_source_summary="Unrelated Source",
            unrelated_target_summary="Unrelated Target",
            parent_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Parent Story",
                "--issue-type",
                "Story",
            ),
            child_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Child Sub-task",
                "--issue-type",
                "Sub-task",
                "--parent",
                "TS-1",
            ),
            unrelated_source_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Unrelated Source",
                "--issue-type",
                "Story",
            ),
            unrelated_target_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Unrelated Target",
                "--issue-type",
                "Story",
            ),
            link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-3",
                "--target-key",
                "TS-4",
                "--type",
                "blocks",
            ),
            expected_link_payload={
                "type": "blocks",
                "target": "TS-4",
                "direction": "outward",
            },
        )
