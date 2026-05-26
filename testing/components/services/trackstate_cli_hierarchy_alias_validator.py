from __future__ import annotations

from testing.core.config.trackstate_cli_hierarchy_alias_config import (
    TrackStateCliHierarchyAliasConfig,
)
from testing.core.interfaces.trackstate_cli_hierarchy_alias_probe import (
    TrackStateCliHierarchyAliasProbe,
)
from testing.core.models.trackstate_cli_hierarchy_alias_result import (
    TrackStateCliHierarchyAliasValidationResult,
)


class TrackStateCliHierarchyAliasValidator:
    def __init__(self, probe: TrackStateCliHierarchyAliasProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliHierarchyAliasConfig,
    ) -> TrackStateCliHierarchyAliasValidationResult:
        return TrackStateCliHierarchyAliasValidationResult(
            observation=self._probe.observe_hierarchy_alias_mapping(config=config)
        )
