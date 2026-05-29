from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_inverse_link_canonical_storage_config import (
    TrackStateCliInverseLinkCanonicalStorageConfig,
)


@dataclass(frozen=True)
class TrackStateCliReadTicketMixedLinkDirectionsConfig(
    TrackStateCliInverseLinkCanonicalStorageConfig
):
    issue_c_summary: str
    issue_c_create_command_prefix: tuple[str, ...]
    outward_link_command_prefix: tuple[str, ...]
    read_ticket_command_prefix: tuple[str, ...]
    expected_inward_link_payload: dict[str, str]
    expected_outward_link_payload: dict[str, str]

    @property
    def issue_c_key(self) -> str:
        return "TS-3"

    @property
    def expected_links_payload(self) -> tuple[dict[str, str], dict[str, str]]:
        return (
            self.expected_inward_link_payload,
            self.expected_outward_link_payload,
        )

    def issue_c_create_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.issue_c_create_command_prefix, "--path", repository_path)

    def outward_link_command(self, repository_path: str) -> tuple[str, ...]:
        return (*self.outward_link_command_prefix, "--path", repository_path)

    def read_ticket_command(self, repository_path: str) -> tuple[str, ...]:
        del repository_path
        return self.read_ticket_command_prefix

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadTicketMixedLinkDirectionsConfig":
        return cls(
            test_id="TS-675",
            project_key="TS",
            project_name="TS-675 Read Ticket Mixed Link Directions Project",
            seed_issue_key="TS-0",
            expected_author_email="ts675@example.com",
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
            issue_c_summary="Issue C",
            issue_c_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue C",
                "--issue-type",
                "Story",
            ),
            outward_link_command_prefix=(
                "trackstate",
                "ticket",
                "link",
                "--target",
                "local",
                "--key",
                "TS-2",
                "--target-key",
                "TS-3",
                "--type",
                "blocks",
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
            expected_outward_link_payload={
                "type": "blocks",
                "target": "TS-3",
                "direction": "outward",
            },
        )
