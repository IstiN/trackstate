from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_localized_components_config import (
    TrackStateCliLocalizedComponentsConfig,
)
from testing.core.models.trackstate_cli_localized_components_result import (
    TrackStateCliLocalizedComponentsValidationResult,
)


class TrackStateCliLocalizedComponentsProbe(Protocol):
    def observe_localized_component_metadata(
        self,
        *,
        config: TrackStateCliLocalizedComponentsConfig,
    ) -> TrackStateCliLocalizedComponentsValidationResult: ...
