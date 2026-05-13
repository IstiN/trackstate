from __future__ import annotations

from testing.core.config.trackstate_cli_localized_components_config import (
    TrackStateCliLocalizedComponentsConfig,
)
from testing.core.interfaces.trackstate_cli_localized_components_probe import (
    TrackStateCliLocalizedComponentsProbe,
)
from testing.core.models.trackstate_cli_localized_components_result import (
    TrackStateCliLocalizedComponentsValidationResult,
)


class TrackStateCliLocalizedComponentsValidator:
    def __init__(self, probe: TrackStateCliLocalizedComponentsProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLocalizedComponentsConfig,
    ) -> TrackStateCliLocalizedComponentsValidationResult:
        return self._probe.observe_localized_component_metadata(config=config)
