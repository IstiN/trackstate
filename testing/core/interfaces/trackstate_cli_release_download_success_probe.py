from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_download_success_config import (
    TrackStateCliReleaseDownloadSuccessConfig,
)
from testing.core.models.trackstate_cli_release_download_success_result import (
    TrackStateCliReleaseDownloadSuccessFixture,
    TrackStateCliReleaseDownloadSuccessValidationResult,
)


class TrackStateCliReleaseDownloadSuccessProbe(Protocol):
    def observe_release_download_success(
        self,
        *,
        config: TrackStateCliReleaseDownloadSuccessConfig,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
        token: str,
    ) -> TrackStateCliReleaseDownloadSuccessValidationResult: ...
