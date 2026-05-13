from __future__ import annotations

from testing.core.config.trackstate_cli_canonical_link_formatter_config import (
    TrackStateCliCanonicalLinkFormatterConfig,
)
from testing.core.interfaces.trackstate_cli_canonical_link_formatter_probe import (
    TrackStateCliCanonicalLinkFormatterProbe,
)
from testing.core.models.trackstate_cli_canonical_link_formatter_result import (
    TrackStateCliCanonicalLinkFormatterValidationResult,
)


class TrackStateCliCanonicalLinkFormatterValidator:
    def __init__(
        self,
        probe: TrackStateCliCanonicalLinkFormatterProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliCanonicalLinkFormatterConfig,
    ) -> TrackStateCliCanonicalLinkFormatterValidationResult:
        return TrackStateCliCanonicalLinkFormatterValidationResult(
            observation=self._probe.observe(config=config)
        )
