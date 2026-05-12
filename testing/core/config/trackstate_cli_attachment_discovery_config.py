from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliAttachmentDiscoveryConfig:
    requested_root_help_command: tuple[str, ...]
    requested_attachment_upload_help_command: tuple[str, ...]
    requested_jira_attachment_upload_help_command: tuple[str, ...]
    fallback_root_help_command: tuple[str, ...]
    fallback_attachment_upload_help_command: tuple[str, ...]
    fallback_jira_attachment_upload_help_command: tuple[str, ...]
    required_root_fragments: tuple[str, ...]
    required_attachment_upload_fragments: tuple[str, ...]
    required_jira_attachment_upload_fragments: tuple[str, ...]

    @classmethod
    def from_env(cls) -> "TrackStateCliAttachmentDiscoveryConfig":
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return cls(
            requested_root_help_command=("trackstate", "--help"),
            requested_attachment_upload_help_command=(
                "trackstate",
                "attachment",
                "upload",
                "--help",
            ),
            requested_jira_attachment_upload_help_command=(
                "trackstate",
                "jira_attach_file_to_ticket",
                "--help",
            ),
            fallback_root_help_command=(dart_bin, "run", "trackstate", "--help"),
            fallback_attachment_upload_help_command=(
                dart_bin,
                "run",
                "trackstate",
                "attachment",
                "upload",
                "--help",
            ),
            fallback_jira_attachment_upload_help_command=(
                dart_bin,
                "run",
                "trackstate",
                "jira_attach_file_to_ticket",
                "--help",
            ),
            required_root_fragments=(
                "attachment Upload or download one attachment.",
                "trackstate attachment upload",
                "trackstate attachment download",
                'Use "trackstate <command> --help" for command-specific options.',
            ),
            required_attachment_upload_fragments=(
                "trackstate attachment upload",
                "Upload one attachment to a single issue.",
                "jira_attach_file_to_ticket --issueKey TRACK-1 --file ./design.png",
                "--issue         Issue key that will receive the attachment.",
                "--file          Source file to upload.",
            ),
            required_jira_attachment_upload_fragments=(
                "trackstate attachment upload",
                "Compatibility alias:",
                "jira_attach_file_to_ticket --issueKey TRACK-1 --file ./design.png",
                "--issue         Issue key that will receive the attachment.",
                "--file          Source file to upload.",
            ),
        )
