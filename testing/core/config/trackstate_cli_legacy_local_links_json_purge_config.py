from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_root_links_json_exclusivity_config import (
    TrackStateCliRootLinksJsonExclusivityConfig,
)


@dataclass(frozen=True)
class TrackStateCliLegacyLocalLinksJsonPurgeConfig(
    TrackStateCliRootLinksJsonExclusivityConfig
):
    legacy_links_json_payload: tuple[dict[str, str], ...]

    @property
    def legacy_links_json_relative_path(self) -> str:
        return f"{self.issue_a_directory_relative_path}/links.json"

    @classmethod
    def from_defaults(cls) -> "TrackStateCliLegacyLocalLinksJsonPurgeConfig":
        return cls(
            test_id="TS-1213",
            project_key="TS",
            project_name="TS-1213 Legacy Local Link Metadata Purge Project",
            seed_issue_key="TS-0",
            expected_author_email="ts1213@example.com",
            issue_a_summary="Issue With Legacy Link Metadata",
            issue_b_summary="Link Target Issue",
            issue_a_create_command_prefix=(
                "trackstate",
                "ticket",
                "create",
                "--target",
                "local",
                "--summary",
                "Issue With Legacy Link Metadata",
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
                "Link Target Issue",
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
            legacy_links_json_payload=(
                {
                    "type": "relates to",
                    "target": "TS-999",
                    "direction": "outward",
                },
            ),
        )
