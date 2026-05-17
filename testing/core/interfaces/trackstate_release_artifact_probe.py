from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_release_artifact_config import (
    TrackStateReleaseArtifactConfig,
)
from testing.core.models.trackstate_release_artifact_result import (
    TrackStateReleaseArtifactObservation,
)


class TrackStateReleaseArtifactProbe(Protocol):
    def observe_release_artifacts(
        self,
        *,
        config: TrackStateReleaseArtifactConfig,
    ) -> TrackStateReleaseArtifactObservation: ...
