from __future__ import annotations

from testing.core.config.trackstate_cli_links_json_hierarchy_exclusion_config import (
    TrackStateCliLinksJsonHierarchyExclusionConfig,
)
from testing.core.interfaces.trackstate_cli_links_json_hierarchy_exclusion_probe import (
    TrackStateCliLinksJsonHierarchyExclusionProbe,
)
from testing.core.models.trackstate_cli_links_json_hierarchy_exclusion_result import (
    TrackStateCliLinksJsonHierarchyExclusionValidationResult,
)


class TrackStateCliLinksJsonHierarchyExclusionValidator:
    def __init__(
        self,
        probe: TrackStateCliLinksJsonHierarchyExclusionProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLinksJsonHierarchyExclusionConfig,
    ) -> TrackStateCliLinksJsonHierarchyExclusionValidationResult:
        return self._probe.observe_links_json_excludes_hierarchy_relationships(
            config=config
        )
