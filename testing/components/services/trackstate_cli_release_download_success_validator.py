from __future__ import annotations

from testing.core.config.trackstate_cli_release_download_success_config import (
    TrackStateCliReleaseDownloadSuccessConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_success_probe import (
    TrackStateCliReleaseDownloadSuccessProbe,
)
from testing.core.models.trackstate_cli_release_download_success_result import (
    TrackStateCliReleaseDownloadSuccessFixture,
    TrackStateCliReleaseDownloadSuccessValidationResult,
)


class TrackStateCliReleaseDownloadSuccessValidator:
    def __init__(self, probe: TrackStateCliReleaseDownloadSuccessProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseDownloadSuccessConfig,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
        token: str,
    ) -> TrackStateCliReleaseDownloadSuccessValidationResult:
        return self._probe.observe_release_download_success(
            config=config,
            fixture=fixture,
            token=token,
        )
