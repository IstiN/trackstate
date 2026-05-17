from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliInvalidLinkTypeConfig:
    test_id: str
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    issue_a_summary: str
    issue_b_summary: str
    unsupported_link_type_label: str
    issue_a_create_command_prefix: tuple[str, ...]
    issue_b_create_command_prefix: tuple[str, ...]
    invalid_link_command_prefix: tuple[str, ...]
    expected_error_code: str
    expected_error_category: str
    expected_error_exit_code: int

    @property
    def issue_a_key(self) -> str:
        return "TS-1"

    @property
    def issue_b_key(self) -> str:
        return "TS-2"

    @property
    def expected_error_message(self) -> str:
        return f"Unsupported link type {self.unsupported_link_type_label}."

    def issue_a_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_a_create_command_prefix, "--path", repository_path)

    def issue_b_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_b_create_command_prefix, "--path", repository_path)

    def invalid_link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.invalid_link_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliInvalidLinkTypeConfig":
        unsupported_link_type_label = "unsupported_link_type_label"
        return cls(
            test_id="TS-645",
            project_key="TS",
            project_name="TS-645 Invalid Link Type Project",
            seed_issue_key="TS-0",
            expected_author_email="ts645@example.com",
            issue_a_summary="Issue A",
            issue_b_summary="Issue B",
            unsupported_link_type_label=unsupported_link_type_label,
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
            invalid_link_command_prefix=(
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
                unsupported_link_type_label,
            ),
            expected_error_code="INVALID_MUTATION",
            expected_error_category="validation",
            expected_error_exit_code=2,
        )
