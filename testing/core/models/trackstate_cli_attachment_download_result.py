from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliAttachmentDownloadObservation:
    command_observation: TrackStateCliCommandObservation
    attachment_id: str
    attachment_name: str
    attachment_media_type: str
    attachment_relative_path: str
    attachment_created_at: str
    attachment_blob_sha: str
    attachment_bytes: bytes
    attachment_base64: str
    output_file_argument: str
    saved_file_absolute_path: str
    saved_file_exists: bool
    saved_file_bytes: bytes | None
    git_status_lines: tuple[str, ...]

    @property
    def requested_command(self) -> tuple[str, ...]:
        return self.command_observation.requested_command

    @property
    def executed_command(self) -> tuple[str, ...]:
        return self.command_observation.executed_command

    @property
    def fallback_reason(self) -> str | None:
        return self.command_observation.fallback_reason

    @property
    def repository_path(self) -> str:
        return self.command_observation.repository_path

    @property
    def compiled_binary_path(self) -> str | None:
        return self.command_observation.compiled_binary_path

    @property
    def requested_command_text(self) -> str:
        return self.command_observation.requested_command_text

    @property
    def executed_command_text(self) -> str:
        return self.command_observation.executed_command_text

    @property
    def result(self):
        return self.command_observation.result


@dataclass(frozen=True)
class TrackStateCliAttachmentDownloadValidationResult:
    observation: TrackStateCliAttachmentDownloadObservation
