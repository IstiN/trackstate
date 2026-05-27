from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliInverseLinkCanonicalStorageConfig:
    test_id: str
    project_key: str
    project_name: str
    seed_issue_key: str
    expected_author_email: str
    issue_a_summary: str
    issue_b_summary: str
    issue_a_create_command_prefix: tuple[str, ...]
    issue_b_create_command_prefix: tuple[str, ...]
    inverse_link_command_prefix: tuple[str, ...]
    expected_canonical_link_payload: dict[str, str]

    @property
    def issue_a_key(self) -> str:
        return "TS-1"

    @property
    def issue_b_key(self) -> str:
        return "TS-2"

    @property
    def source_links_json_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_a_key}/links.json"

    @property
    def target_links_json_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_b_key}/links.json"

    def issue_a_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_a_create_command_prefix, "--path", repository_path)

    def issue_b_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_b_create_command_prefix, "--path", repository_path)

    def inverse_link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.inverse_link_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliInverseLinkCanonicalStorageConfig":
        return cls(
            test_id="TS-624",
            project_key="TS",
            project_name="TS-624 Inverse Link Canonical Storage Project",
            seed_issue_key="TS-0",
            expected_author_email="ts624@example.com",
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
            inverse_link_command_prefix=(
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
                "is blocked by",
            ),
            expected_canonical_link_payload={
                "type": "blocks",
                "target": "TS-1",
                "direction": "outward",
            },
        )
