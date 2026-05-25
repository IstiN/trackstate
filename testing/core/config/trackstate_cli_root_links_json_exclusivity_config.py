from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliRootLinksJsonExclusivityConfig:
    test_id: str
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    issue_a_summary: str
    issue_b_summary: str
    issue_a_create_command_prefix: tuple[str, ...]
    issue_b_create_command_prefix: tuple[str, ...]
    link_command_prefix: tuple[str, ...]
    expected_link_payload: dict[str, str]

    @property
    def issue_a_key(self) -> str:
        return "TS-1"

    @property
    def issue_b_key(self) -> str:
        return "TS-2"

    @property
    def root_links_json_relative_path(self) -> str:
        return "links.json"

    @property
    def issue_a_directory_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_a_key}"

    @property
    def issue_b_directory_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_b_key}"

    @property
    def issue_a_main_relative_path(self) -> str:
        return f"{self.issue_a_directory_relative_path}/main.md"

    @property
    def issue_b_main_relative_path(self) -> str:
        return f"{self.issue_b_directory_relative_path}/main.md"

    def issue_a_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_a_create_command_prefix, "--path", repository_path)

    def issue_b_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_b_create_command_prefix, "--path", repository_path)

    def link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.link_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliRootLinksJsonExclusivityConfig":
        return cls(
            test_id="TS-1136",
            project_key="TS",
            project_name="TS-1136 Root Link Artifact Location Project",
            seed_issue_key="TS-0",
            expected_author_email="ts1136@example.com",
            issue_a_summary="Issue A",
            issue_b_summary="Issue B",
            issue_a_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue A",
                "--issue-type",
                "Story",
            ),
            issue_b_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue B",
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
                "TS-1",
                "--target-key",
                "TS-2",
                "--type",
                "blocks",
            ),
            expected_link_payload={
                "type": "blocks",
                "target": "TS-2",
                "direction": "outward",
            },
        )
