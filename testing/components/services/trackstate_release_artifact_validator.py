from __future__ import annotations

from testing.core.config.trackstate_release_artifact_config import (
    TrackStateReleaseArtifactConfig,
)
from testing.core.interfaces.trackstate_release_artifact_probe import (
    TrackStateReleaseArtifactProbe,
)
from testing.core.models.trackstate_release_artifact_result import (
    TrackStateReleaseArtifactObservation,
)


class TrackStateReleaseArtifactValidator:
    def __init__(self, probe: TrackStateReleaseArtifactProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateReleaseArtifactConfig,
    ) -> TrackStateReleaseArtifactObservation:
        return self._probe.observe_release_artifacts(config=config)
