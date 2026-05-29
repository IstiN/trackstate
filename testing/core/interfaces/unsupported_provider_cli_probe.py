from __future__ import annotations

from typing import Protocol

from testing.core.config.unsupported_provider_cli_config import (
    UnsupportedProviderCliConfig,
)
from testing.core.models.unsupported_provider_cli_result import (
    UnsupportedProviderCliObservation,
)


class UnsupportedProviderCliProbe(Protocol):
    def unsupported_provider(
        self,
        *,
        config: UnsupportedProviderCliConfig,
    ) -> UnsupportedProviderCliObservation: ...
