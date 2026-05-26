from __future__ import annotations

from testing.core.config.trackstate_cli_create_native_hierarchy_config import (
    TrackStateCliCreateNativeHierarchyConfig,
)
from testing.core.interfaces.trackstate_cli_create_native_hierarchy_probe import (
    TrackStateCliCreateNativeHierarchyProbe,
)
from testing.core.models.trackstate_cli_create_native_hierarchy_result import (
    TrackStateCliCreateNativeHierarchyValidationResult,
)


class TrackStateCliCreateNativeHierarchyValidator:
    def __init__(self, probe: TrackStateCliCreateNativeHierarchyProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliCreateNativeHierarchyConfig,
    ) -> TrackStateCliCreateNativeHierarchyValidationResult:
        return TrackStateCliCreateNativeHierarchyValidationResult(
            observation=self._probe.observe_create_with_native_hierarchy(
                config=config
            )
        )
