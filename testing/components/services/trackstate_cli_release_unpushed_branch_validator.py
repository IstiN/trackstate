from __future__ import annotations

from testing.core.config.trackstate_cli_release_unpushed_branch_config import (
    TrackStateCliReleaseUnpushedBranchConfig,
)
from testing.core.interfaces.trackstate_cli_release_unpushed_branch_probe import (
    TrackStateCliReleaseUnpushedBranchProbe,
)
from testing.core.models.trackstate_cli_release_unpushed_branch_result import (
    TrackStateCliReleaseUnpushedBranchValidationResult,
)


class TrackStateCliReleaseUnpushedBranchValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseUnpushedBranchProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
    ) -> TrackStateCliReleaseUnpushedBranchValidationResult:
        return self._probe.observe(config=config)
