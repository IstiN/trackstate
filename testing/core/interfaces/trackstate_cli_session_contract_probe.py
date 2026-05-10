from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.core.models.trackstate_cli_session_contract_result import (
    TrackStateCliSessionContractObservation,
)


class TrackStateCliSessionContractProbe(Protocol):
    def observe_default_json_session(
        self,
        *,
        config: TrackStateCliSessionContractConfig,
    ) -> TrackStateCliSessionContractObservation: ...
