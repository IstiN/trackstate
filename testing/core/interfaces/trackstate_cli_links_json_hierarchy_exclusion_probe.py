from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_links_json_hierarchy_exclusion_config import (
    TrackStateCliLinksJsonHierarchyExclusionConfig,
)
from testing.core.models.trackstate_cli_links_json_hierarchy_exclusion_result import (
    TrackStateCliLinksJsonHierarchyExclusionValidationResult,
)


class TrackStateCliLinksJsonHierarchyExclusionProbe(Protocol):
    def observe_links_json_excludes_hierarchy_relationships(
        self,
        *,
        config: TrackStateCliLinksJsonHierarchyExclusionConfig,
    ) -> TrackStateCliLinksJsonHierarchyExclusionValidationResult: ...
