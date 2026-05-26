from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_hierarchy_alias_config import (
    TrackStateCliHierarchyAliasConfig,
)
from testing.core.models.trackstate_cli_hierarchy_alias_result import (
    TrackStateCliHierarchyAliasObservation,
)


class TrackStateCliHierarchyAliasProbe(Protocol):
    def observe_hierarchy_alias_mapping(
        self,
        *,
        config: TrackStateCliHierarchyAliasConfig,
    ) -> TrackStateCliHierarchyAliasObservation: ...
