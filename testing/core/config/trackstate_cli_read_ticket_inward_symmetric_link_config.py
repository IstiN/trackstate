from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_symmetric_link_show_config import (
    TrackStateCliSymmetricLinkShowConfig,
)


@dataclass(frozen=True)
class TrackStateCliReadTicketInwardSymmetricLinkConfig(
    TrackStateCliSymmetricLinkShowConfig
):
    def read_ticket_command(self, repository_path: str) -> tuple[str, ...]:
        del repository_path
        return self.read_ticket_command_prefix

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadTicketInwardSymmetricLinkConfig":
        return cls(
            test_id="TS-670",
            project_key="TS",
            project_name="TS-670 Read Ticket Symmetric Link Project",
            seed_issue_key="TS-0",
            expected_author_email="ts670@example.com",
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
                "--key",
                "TS-2",
            ),
            expected_inward_link_payload={
                "type": "relates to",
                "target": "TS-1",
                "direction": "inward",
            },
        )
