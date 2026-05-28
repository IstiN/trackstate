from __future__ import annotations

from testing.core.config.trackstate_cli_legacy_local_links_json_purge_config import (
    TrackStateCliLegacyLocalLinksJsonPurgeConfig,
)
from testing.core.interfaces.trackstate_cli_legacy_local_links_json_purge_probe import (
    TrackStateCliLegacyLocalLinksJsonPurgeProbe,
)
from testing.core.models.trackstate_cli_legacy_local_links_json_purge_result import (
    TrackStateCliLegacyLocalLinksJsonPurgeValidationResult,
)


class TrackStateCliLegacyLocalLinksJsonPurgeValidator:
    def __init__(
        self,
        probe: TrackStateCliLegacyLocalLinksJsonPurgeProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLegacyLocalLinksJsonPurgeConfig,
    ) -> TrackStateCliLegacyLocalLinksJsonPurgeValidationResult:
        return self._probe.observe_legacy_local_links_json_purge(config=config)
