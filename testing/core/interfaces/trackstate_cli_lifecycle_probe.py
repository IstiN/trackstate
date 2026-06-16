from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_lifecycle_config import (
    TrackStateCliLifecycleConfig,
)
from testing.core.models.trackstate_cli_lifecycle_result import (
    TrackStateCliLifecycleValidationResult,
)


class TrackStateCliLifecycleProbe(Protocol):
    def observe_lifecycle_behavior(
        self,
        *,
        config: TrackStateCliLifecycleConfig,
    ) -> TrackStateCliLifecycleValidationResult: ...
