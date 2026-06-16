from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_legacy_local_links_json_purge_config import (
    TrackStateCliLegacyLocalLinksJsonPurgeConfig,
)
from testing.core.models.trackstate_cli_legacy_local_links_json_purge_result import (
    TrackStateCliLegacyLocalLinksJsonPurgeValidationResult,
)


class TrackStateCliLegacyLocalLinksJsonPurgeProbe(Protocol):
    def observe_legacy_local_links_json_purge(
        self,
        *,
        config: TrackStateCliLegacyLocalLinksJsonPurgeConfig,
    ) -> TrackStateCliLegacyLocalLinksJsonPurgeValidationResult: ...
