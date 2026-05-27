from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation


@dataclass(frozen=True)
class TrackStateCliAttachmentDiscoveryValidationResult:
    root_help: TrackStateCliHelpObservation
    attachment_upload_help: TrackStateCliHelpObservation
    jira_attachment_upload_help: TrackStateCliHelpObservation
