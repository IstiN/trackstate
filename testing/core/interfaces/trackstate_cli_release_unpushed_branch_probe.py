from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_unpushed_branch_config import (
    TrackStateCliReleaseUnpushedBranchConfig,
)
from testing.core.models.trackstate_cli_release_unpushed_branch_result import (
    TrackStateCliReleaseUnpushedBranchValidationResult,
)


class TrackStateCliReleaseUnpushedBranchProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
    ) -> TrackStateCliReleaseUnpushedBranchValidationResult: ...
