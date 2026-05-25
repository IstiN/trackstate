from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_root_links_json_exclusivity_config import (
    TrackStateCliRootLinksJsonExclusivityConfig,
)
from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonExclusivityValidationResult,
)


class TrackStateCliRootLinksJsonExclusivityProbe(Protocol):
    def observe_root_links_json_exclusivity(
        self,
        *,
        config: TrackStateCliRootLinksJsonExclusivityConfig,
    ) -> TrackStateCliRootLinksJsonExclusivityValidationResult: ...
