from __future__ import annotations

import base64
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliAttachmentDownloadConfig:
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    attachment_name: str
    attachment_relative_path: str
    attachment_media_type: str
    attachment_base64: str
    attachment_created_at: str
    output_file_argument: str
    requested_command_prefix: tuple[str, ...]
    required_top_level_keys: tuple[str, ...]
    required_target_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    required_attachment_keys: tuple[str, ...]
    expected_command_name: str

    @classmethod
    def from_env(cls) -> "TrackStateCliAttachmentDownloadConfig":
        return cls(
            project_key="TS",
            project_name="TS-382 Local Attachment Download Project",
            issue_key="TS-1",
            issue_summary="CLI attachment download fixture",
            attachment_name="ATT-123.png",
            attachment_relative_path="TS/TS-1/attachments/ATT-123.png",
            attachment_media_type="image/png",
            attachment_base64=(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+lm9sAAAAASUVORK5CYII="
            ),
            attachment_created_at="2026-05-12T08:00:00Z",
            output_file_argument="./downloads/downloaded_file.png",
            requested_command_prefix=(
                "trackstate",
                "attachment",
                "download",
            ),
            required_top_level_keys=(
                "schemaVersion",
                "ok",
                "provider",
                "target",
                "output",
                "data",
            ),
            required_target_keys=("type", "value"),
            required_data_keys=(
                "command",
                "authSource",
                "issue",
                "savedFile",
                "attachment",
            ),
            required_attachment_keys=(
                "id",
                "name",
                "mediaType",
                "sizeBytes",
                "createdAt",
                "revisionOrOid",
            ),
            expected_command_name="attachment-download",
        )

    @property
    def attachment_bytes(self) -> bytes:
        return base64.b64decode(self.attachment_base64)

    @property
    def requested_command(self) -> tuple[str, ...]:
        return (
            *self.requested_command_prefix,
            "--attachment-id",
            self.attachment_relative_path,
            "--out",
            self.output_file_argument,
            "--target",
            "local",
        )

    @property
    def fallback_command_prefix(self) -> tuple[str, ...]:
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        return (dart_bin, "run", "trackstate")
