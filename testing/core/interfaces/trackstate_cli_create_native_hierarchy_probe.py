from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_create_native_hierarchy_config import (
    TrackStateCliCreateNativeHierarchyConfig,
)
from testing.core.models.trackstate_cli_create_native_hierarchy_result import (
    TrackStateCliCreateNativeHierarchyObservation,
)


class TrackStateCliCreateNativeHierarchyProbe(Protocol):
    def observe_create_with_native_hierarchy(
        self,
        *,
        config: TrackStateCliCreateNativeHierarchyConfig,
    ) -> TrackStateCliCreateNativeHierarchyObservation: ...
