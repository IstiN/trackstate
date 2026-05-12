from __future__ import annotations

from testing.core.config.trackstate_cli_lifecycle_config import (
    TrackStateCliLifecycleConfig,
)
from testing.core.interfaces.trackstate_cli_lifecycle_probe import (
    TrackStateCliLifecycleProbe,
)
from testing.core.models.trackstate_cli_lifecycle_result import (
    TrackStateCliLifecycleValidationResult,
)


class TrackStateCliLifecycleValidator:
    def __init__(self, probe: TrackStateCliLifecycleProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLifecycleConfig,
    ) -> TrackStateCliLifecycleValidationResult:
        return self._probe.observe_lifecycle_behavior(config=config)
