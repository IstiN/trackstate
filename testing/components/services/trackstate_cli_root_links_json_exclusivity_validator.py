from __future__ import annotations

from testing.core.config.trackstate_cli_root_links_json_exclusivity_config import (
    TrackStateCliRootLinksJsonExclusivityConfig,
)
from testing.core.interfaces.trackstate_cli_root_links_json_exclusivity_probe import (
    TrackStateCliRootLinksJsonExclusivityProbe,
)
from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonExclusivityValidationResult,
)


class TrackStateCliRootLinksJsonExclusivityValidator:
    def __init__(
        self,
        probe: TrackStateCliRootLinksJsonExclusivityProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliRootLinksJsonExclusivityConfig,
    ) -> TrackStateCliRootLinksJsonExclusivityValidationResult:
        return self._probe.observe_root_links_json_exclusivity(config=config)
