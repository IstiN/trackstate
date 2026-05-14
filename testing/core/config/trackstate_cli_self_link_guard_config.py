from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliSelfLinkGuardConfig:
    test_id: str
    compiled_source_ref: str
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    issue_a_summary: str
    issue_a_create_command_prefix: tuple[str, ...]
    self_link_command_prefix: tuple[str, ...]
    expected_error_code: str
    expected_error_category: str
    expected_error_exit_code: int
    expected_error_message_fragments: tuple[str, ...]

    @property
    def issue_a_key(self) -> str:
        return "TS-1"

    @property
    def links_json_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_a_key}/links.json"

    def issue_a_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_a_create_command_prefix, "--path", repository_path)

    def self_link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.self_link_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliSelfLinkGuardConfig":
        return cls(
            test_id="TS-659",
            compiled_source_ref="origin/main",
            project_key="TS",
            project_name="TS-659 Self Link Guard Project",
            seed_issue_key="TS-0",
            expected_author_email="ts659@example.com",
            issue_a_summary="Issue A",
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
            self_link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-1",
                "--target-key",
                "TS-1",
                "--type",
                "relates to",
            ),
            expected_error_code="INVALID_MUTATION",
            expected_error_category="validation",
            expected_error_exit_code=2,
            expected_error_message_fragments=("TS-1", "itself"),
        )
