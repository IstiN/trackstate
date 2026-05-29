from __future__ import annotations

from typing import Protocol

from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation


class TrackStateCliAttachmentDiscoveryProbe(Protocol):
    def root_help(self) -> TrackStateCliHelpObservation: ...

    def attachment_upload_help(self) -> TrackStateCliHelpObservation: ...

    def jira_attachment_upload_help(self) -> TrackStateCliHelpObservation: ...
