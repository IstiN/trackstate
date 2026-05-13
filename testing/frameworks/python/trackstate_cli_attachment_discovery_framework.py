from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_attachment_discovery_probe import (
    TrackStateCliAttachmentDiscoveryProbe,
)
from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation
from testing.frameworks.python.trackstate_cli_help_framework import (
    PythonTrackStateCliHelpFramework,
)


class PythonTrackStateCliAttachmentDiscoveryFramework(
    PythonTrackStateCliHelpFramework,
    TrackStateCliAttachmentDiscoveryProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def attachment_upload_help(self) -> TrackStateCliHelpObservation:
        return self._run_preferred_command(
            requested_command=("trackstate", "attachment", "upload", "--help"),
            fallback_command=(
                "dart",
                "run",
                "trackstate",
                "attachment",
                "upload",
                "--help",
            ),
        )

    def jira_attachment_upload_help(self) -> TrackStateCliHelpObservation:
        return self._run_preferred_command(
            requested_command=("trackstate", "jira_attach_file_to_ticket", "--help"),
            fallback_command=(
                "dart",
                "run",
                "trackstate",
                "jira_attach_file_to_ticket",
                "--help",
            ),
        )
