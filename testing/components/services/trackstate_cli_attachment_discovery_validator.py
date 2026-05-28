from __future__ import annotations

from testing.core.config.trackstate_cli_attachment_discovery_config import (
    TrackStateCliAttachmentDiscoveryConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_discovery_probe import (
    TrackStateCliAttachmentDiscoveryProbe,
)
from testing.core.models.trackstate_cli_attachment_discovery_result import (
    TrackStateCliAttachmentDiscoveryValidationResult,
)


class TrackStateCliAttachmentDiscoveryValidator:
    def __init__(self, probe: TrackStateCliAttachmentDiscoveryProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliAttachmentDiscoveryConfig,
    ) -> TrackStateCliAttachmentDiscoveryValidationResult:
        del config
        return TrackStateCliAttachmentDiscoveryValidationResult(
            root_help=self._probe.root_help(),
            attachment_upload_help=self._probe.attachment_upload_help(),
            jira_attachment_upload_help=self._probe.jira_attachment_upload_help(),
        )
