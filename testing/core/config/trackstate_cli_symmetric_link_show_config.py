from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_inverse_link_canonical_storage_config import (
    TrackStateCliInverseLinkCanonicalStorageConfig,
)


@dataclass(frozen=True)
class TrackStateCliSymmetricLinkShowConfig(
    TrackStateCliInverseLinkCanonicalStorageConfig
):
    ticket_show_command_prefix: tuple[str, ...]
    read_ticket_command_prefix: tuple[str, ...]
    expected_inward_link_payload: dict[str, str]

    def ticket_show_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.ticket_show_command_prefix, "--path", repository_path)

    def read_ticket_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.read_ticket_command_prefix, "--path", repository_path)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliSymmetricLinkShowConfig":
        return cls(
            test_id="TS-657",
            project_key="TS",
            project_name="TS-657 Symmetric Link Show Project",
            seed_issue_key="TS-0",
            expected_author_email="ts657@example.com",
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
                "relates to",
            ),
            expected_canonical_link_payload={
                "type": "relates to",
                "target": "TS-2",
                "direction": "outward",
            },
            ticket_show_command_prefix=(
                "trackstate",
                "ticket",
                "show",
                "--target",
                "local",
                "--key",
                "TS-2",
            ),
            read_ticket_command_prefix=(
                "trackstate",
                "read",
                "ticket",
                "--target",
                "local",
                "--key",
                "TS-2",
            ),
            expected_inward_link_payload={
                "type": "relates to",
                "target": "TS-1",
                "direction": "inward",
            },
        )
